"""FastAPI 服务入口：桌面端（Tauri sidecar）与未来 Web 端共用。

MVP 范围：
- POST /api/charts/calculate  无状态排盘（JSON 进 JSON 出）
- 命盘 CRUD / 快照 / 导入导出
- AI 分析：skill CRUD、LLM 配置、流式对话代理（biz_requirement.md §4.4）
"""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ziwei_engine.calendar.converter import BirthInput
from ziwei_engine.chart.natal import NatalChart, calculate
from ziwei_engine.io.serialize import ENGINE_VERSION, chart_to_dict, horoscope_to_dict, patterns_to_dict, soul_body_to_dict, star_analysis_to_dict
from ziwei_engine.rules.patterns import analyze_patterns
from ziwei_engine.rules.star_interp import analyze_soul_body, analyze_stars
from ziwei_engine.rules.horoscope import locate_horoscope

app = FastAPI(title="Ziwei API", version=ENGINE_VERSION)

# Tauri webview / 本地前端跨域；expose 供前端读取导出文件名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


class CalculateRequest(BaseModel):
    """排盘请求。"""

    solar_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", examples=["1990-05-15"])
    hour_index: int = Field(ge=0, le=12, description="0=早子时…11=亥时, 12=晚子时")
    gender: str = Field(pattern=r"^(男|女)$")
    target_date: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="运限定位目标日（大限/流年/小限），缺省为今天",
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine_version": ENGINE_VERSION}


def _horoscope(chart: NatalChart, target_date: str | None) -> dict:
    """按目标日定位运限；target_date 为 None 时取今天。"""
    sk = chart.skeleton
    try:
        info = locate_horoscope(
            chart.birth,
            chart.calendar,
            sk.soul_palace_branch,
            sk.class_number,
            date.fromisoformat(target_date) if target_date else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return horoscope_to_dict(info)


def _analysis(chart: NatalChart) -> dict:
    """格局 + 星曜 + 命身主分析（biz_requirement.md §4.3.1/§4.3.2）。"""
    return {
        "patterns": patterns_to_dict(analyze_patterns(chart)),
        "stars": star_analysis_to_dict(analyze_stars(chart)),
        "soul_body": soul_body_to_dict(analyze_soul_body(chart)),
    }


@app.post("/api/charts/calculate")
def calculate_chart(req: CalculateRequest) -> dict:
    y, m, d = (int(x) for x in req.solar_date.split("-"))
    chart = calculate(BirthInput(y, m, d, req.hour_index, req.gender))
    result = chart_to_dict(chart)
    result["horoscope"] = _horoscope(chart, req.target_date)
    result["analysis"] = _analysis(chart)
    return result


# ---------- 命盘持久化 CRUD ----------

import os
from pathlib import Path

from ziwei_engine.io.persist import (
    backfill_hour_index,
    delete_chart,
    ensure_chart_hour_index,
    load_snapshot,
    make_session_factory,
    migrate_legacy_names,
    save_chart,
    update_chart,
)
from ziwei_engine.models import Chart, Person

_DB_PATH = Path(os.environ.get("ZIWEI_DB", Path(__file__).resolve().parent.parent / "data" / "ziwei.sqlite"))
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_session_factory = make_session_factory(_DB_PATH)
# 旧库迁移（幂等，每次启动执行）：补列 → 宫名迁移 → 时辰回填
ensure_chart_hour_index(_session_factory)
migrate_legacy_names(_session_factory)
backfill_hour_index(_session_factory)


class SaveChartRequest(CalculateRequest):
    person_name: str = "未命名"


@app.post("/api/charts", status_code=201)
def create_chart(req: SaveChartRequest) -> dict:
    """排盘并落库（含快照）。"""
    y, m, d = (int(x) for x in req.solar_date.split("-"))
    chart = calculate(BirthInput(y, m, d, req.hour_index, req.gender))
    with _session_factory() as session:
        row = save_chart(session, chart, person_name=req.person_name)
        return {"chart_id": row.id, "person": req.person_name}


@app.get("/api/charts")
def list_charts() -> list[dict]:
    from sqlalchemy import select

    with _session_factory() as session:
        rows = session.scalars(select(Chart).order_by(Chart.id.desc())).all()
        return [
            {
                "chart_id": r.id,
                "person": session.get(Person, r.person_id).name,
                "solar_datetime": r.solar_datetime.isoformat() if r.solar_datetime else None,
                "hour_index": r.hour_index,
                "gender": r.gender,
                "engine_version": r.engine_version,
            }
            for r in rows
        ]


@app.get("/api/charts/export-all")
def export_all_charts() -> Response:
    """导出全部命盘为单个 JSON 文件（快照数组 + 元信息，供备份/迁移）。"""
    from datetime import date

    from sqlalchemy import select

    with _session_factory() as session:
        rows = session.execute(select(Chart).order_by(Chart.id)).scalars().all()
        charts = [
            {
                "chart_id": row.id,
                "person": session.get(Person, row.person_id).name,
                "snapshot": load_snapshot(session, row.id),
            }
            for row in rows
        ]
    payload = {
        "version": ENGINE_VERSION,
        "exported_at": date.today().isoformat(),
        "count": len(charts),
        "charts": charts,
    }
    filename = f"ziwei_all_{date.today().isoformat()}.json"
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@app.get("/api/charts/{chart_id}")
def get_chart(chart_id: int) -> dict:
    """读取命盘快照（完整 JSON，可直接渲染或导出）。"""
    with _session_factory() as session:
        try:
            snap = load_snapshot(session, chart_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="chart not found") from None
    # 快照本身不含运限/格局：按出生参数重排现算，保证与当前引擎版本一致
    inp = snap["input"]
    y, m, d = (int(x) for x in inp["solar_date"].split("-"))
    chart = calculate(BirthInput(y, m, d, inp["hour_index"], inp["gender"]))
    snap["horoscope"] = _horoscope(chart, None)
    snap["analysis"] = _analysis(chart)
    return snap


class UpdateChartRequest(BaseModel):
    """编辑命盘：出生参数 + 姓名（整体重排覆盖，保留历史快照）。"""

    solar_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    hour_index: int = Field(ge=0, le=12, description="0=早子时…11=亥时, 12=晚子时")
    gender: str = Field(pattern=r"^(男|女)$")
    person_name: str = Field(default="未命名", min_length=1, max_length=64)


@app.put("/api/charts/{chart_id}")
def edit_chart(chart_id: int, req: UpdateChartRequest) -> dict:
    y, m, d = (int(x) for x in req.solar_date.split("-"))
    chart = calculate(BirthInput(y, m, d, req.hour_index, req.gender))
    with _session_factory() as session:
        row = update_chart(session, chart_id, chart, person_name=req.person_name)
        if row is None:
            raise HTTPException(status_code=404, detail="chart not found") from None
        return {"chart_id": row.id, "person": req.person_name}


@app.delete("/api/charts/{chart_id}", status_code=204)
def remove_chart(chart_id: int) -> Response:
    with _session_factory() as session:
        if not delete_chart(session, chart_id):
            raise HTTPException(status_code=404, detail="chart not found") from None
    return Response(status_code=204)


# ---------- JSON 文件导出 / 导入（biz_requirement.md §4.2） ----------

import json
from urllib.parse import quote


@app.get("/api/charts/{chart_id}/export")
def export_chart(chart_id: int) -> Response:
    """导出命盘 JSON 快照为下载文件。"""
    with _session_factory() as session:
        try:
            snap = load_snapshot(session, chart_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="chart not found") from None
        row = session.get(Chart, chart_id)
        person = session.get(Person, row.person_id).name if row else "chart"
    filename = f"ziwei_{person}_{snap['input']['solar_date']}.json"
    return Response(
        content=json.dumps(snap, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


class ImportChartRequest(BaseModel):
    """导入命盘 JSON 文件内容。"""

    snapshot: dict
    person_name: str = "导入命盘"


@app.post("/api/charts/import", status_code=201)
def import_chart(req: ImportChartRequest) -> dict:
    """导入快照：以其中出生参数重排后落库，保证与当前引擎版本一致。"""
    try:
        birth_input = req.snapshot["input"]
        y, m, d = (int(x) for x in str(birth_input["solar_date"]).split("-"))
        hour_index = int(birth_input["hour_index"])
        gender = str(birth_input["gender"])
        if gender not in ("男", "女"):
            raise ValueError("gender 必须为 男/女")
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"无效的命盘文件: {e}") from e
    chart = calculate(BirthInput(y, m, d, hour_index, gender))
    with _session_factory() as session:
        row = save_chart(session, chart, person_name=req.person_name or "导入命盘")
        return {"chart_id": row.id, "person": req.person_name}


# ---------- AI 分析：skill 管理 / LLM 配置 / 流式对话（biz_requirement.md §4.4） ----------

from fastapi.responses import StreamingResponse

from ziwei_engine.models import AIConfig, PromptTemplate
from ziwei_engine.io.persist import ensure_prompt_template_builtin, seed_skills

from llm import build_messages, stream_chat

# 旧库补列 + 内置 skill 播种（幂等，随启动执行）
ensure_prompt_template_builtin(_session_factory)
with _session_factory() as _s:
    seed_skills(_s)


def _skill_dict(row: PromptTemplate) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "content": row.template_content,
        "is_builtin": row.is_builtin,
    }


@app.get("/api/ai/skills")
def list_skills() -> list[dict]:
    from sqlalchemy import select

    with _session_factory() as session:
        rows = session.scalars(
            select(PromptTemplate).order_by(PromptTemplate.is_builtin.desc(), PromptTemplate.id)
        ).all()
        return [_skill_dict(r) for r in rows]


class SkillRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1)
    category: str | None = None


@app.post("/api/ai/skills", status_code=201)
def create_skill(req: SkillRequest) -> dict:
    from sqlalchemy import select

    with _session_factory() as session:
        if session.scalar(select(PromptTemplate).where(PromptTemplate.name == req.name)):
            raise HTTPException(status_code=409, detail=f"skill「{req.name}」已存在")
        row = PromptTemplate(
            name=req.name,
            category=req.category or "自定义",
            template_content=req.content,
            is_builtin=False,
        )
        session.add(row)
        session.commit()
        return _skill_dict(row)


@app.put("/api/ai/skills/{skill_id}")
def update_skill(skill_id: int, req: SkillRequest) -> dict:
    with _session_factory() as session:
        row = session.get(PromptTemplate, skill_id)
        if row is None:
            raise HTTPException(status_code=404, detail="skill 不存在")
        if row.is_builtin:
            # 内置 skill 只读：内容随引擎版本播种刷新，要调整请新建自定义 skill
            raise HTTPException(status_code=409, detail="内置 skill 为只读，可复制内容新建自定义 skill")
        row.name = req.name
        row.template_content = req.content
        row.category = req.category or "自定义"
        session.commit()
        return _skill_dict(row)


@app.delete("/api/ai/skills/{skill_id}", status_code=204)
def delete_skill(skill_id: int) -> Response:
    with _session_factory() as session:
        row = session.get(PromptTemplate, skill_id)
        if row is None:
            raise HTTPException(status_code=404, detail="skill 不存在")
        if row.is_builtin:
            raise HTTPException(status_code=409, detail="内置 skill 不可删除")
        session.delete(row)
        session.commit()
        return Response(status_code=204)


def _get_config(session) -> AIConfig:
    cfg = session.get(AIConfig, 1)
    if cfg is None:
        cfg = AIConfig(id=1)
        session.add(cfg)
        session.commit()
    return cfg


@app.get("/api/ai/config")
def get_ai_config() -> dict:
    with _session_factory() as session:
        cfg = _get_config(session)
        return {
            "base_url": cfg.base_url,
            "model": cfg.model,
            # Key 脱敏：只回传掩码与是否存在，不回传明文
            "api_key_masked": (cfg.api_key[:4] + "****" + cfg.api_key[-4:]) if cfg.api_key and len(cfg.api_key) > 8 else ("****" if cfg.api_key else ""),
            "has_api_key": bool(cfg.api_key),
        }


class AIConfigRequest(BaseModel):
    base_url: str = Field(min_length=1, max_length=255)
    model: str = Field(min_length=1, max_length=64)
    # 空字符串 = 保持原 key 不变；null = 清除
    api_key: str | None = ""


@app.put("/api/ai/config")
def put_ai_config(req: AIConfigRequest) -> dict:
    with _session_factory() as session:
        cfg = _get_config(session)
        cfg.base_url = req.base_url.rstrip("/")
        cfg.model = req.model
        if req.api_key is None:
            cfg.api_key = None
        elif req.api_key:
            cfg.api_key = req.api_key
        session.commit()
        return {"ok": True}


class ChatMessage(BaseModel):
    role: str
    content: str


class AIChatRequest(BaseModel):
    skill_id: int
    chart: dict
    messages: list[ChatMessage] = []


@app.post("/api/ai/chat")
async def ai_chat(req: AIChatRequest) -> StreamingResponse:
    """流式对话：skill 提示词 + 命盘 JSON + 历史消息 → SSE 增量文本。"""
    with _session_factory() as session:
        skill = session.get(PromptTemplate, req.skill_id)
        if skill is None:
            raise HTTPException(status_code=404, detail="skill 不存在")
        cfg = _get_config(session)
        if not cfg.api_key:
            raise HTTPException(status_code=400, detail="尚未配置 LLM API Key，请在设置中填写")
        skill_prompt = skill.template_content
        base_url, api_key, model = cfg.base_url, cfg.api_key, cfg.model

    history = [m.model_dump() for m in req.messages]
    messages = build_messages(skill_prompt, req.chart, history)

    async def event_stream():
        try:
            async for kind, text in stream_chat(base_url, api_key, model, messages):
                payload = {"delta": text} if kind == "content" else {"reasoning": text}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

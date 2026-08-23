"""FastAPI 服务入口：桌面端（Tauri sidecar）与未来 Web 端共用。

MVP 范围：
- POST /api/charts/calculate  无状态排盘（JSON 进 JSON 出）
- 命盘 CRUD / 快照接口在 DB 模型就绪后接入
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ziwei_engine.calendar.converter import BirthInput
from ziwei_engine.chart.natal import calculate
from ziwei_engine.io.serialize import ENGINE_VERSION, chart_to_dict

app = FastAPI(title="Ziwei API", version=ENGINE_VERSION)

# Tauri webview / 本地前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CalculateRequest(BaseModel):
    """排盘请求。"""

    solar_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", examples=["1990-05-15"])
    hour_index: int = Field(ge=0, le=12, description="0=早子时…11=亥时, 12=晚子时")
    gender: str = Field(pattern=r"^(男|女)$")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine_version": ENGINE_VERSION}


@app.post("/api/charts/calculate")
def calculate_chart(req: CalculateRequest) -> dict:
    y, m, d = (int(x) for x in req.solar_date.split("-"))
    chart = calculate(BirthInput(y, m, d, req.hour_index, req.gender))
    return chart_to_dict(chart)


# ---------- 命盘持久化 CRUD ----------

import os
from pathlib import Path

from ziwei_engine.io.persist import load_snapshot, make_session_factory, save_chart
from ziwei_engine.models import Chart, Person

_DB_PATH = Path(os.environ.get("ZIWEI_DB", Path(__file__).resolve().parent.parent / "data" / "ziwei.sqlite"))
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_session_factory = make_session_factory(_DB_PATH)


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
                "gender": r.gender,
                "engine_version": r.engine_version,
            }
            for r in rows
        ]


@app.get("/api/charts/{chart_id}")
def get_chart(chart_id: int) -> dict:
    """读取命盘快照（完整 JSON，可直接渲染或导出）。"""
    with _session_factory() as session:
        try:
            return load_snapshot(session, chart_id)
        except KeyError:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="chart not found")

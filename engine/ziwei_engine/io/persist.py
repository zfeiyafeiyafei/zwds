"""命盘持久化：NatalChart → 四域数据库 + JSON 快照文件。

- 结构化落库：chart / chart_palace / chart_star / chart_shensha / chart_period
- 快照：chart_snapshot 表 + 本地 JSON 文件（biz_requirement.md §4.2）
- 知识库基础行（十二宫定义、星曜状态、默认流派规则包）首次自动播种
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from ..chart.natal import NatalChart
from ..constants import EARTHLY_BRANCHES, HEAVENLY_STEMS, PALACE_NAME_ALIASES, PALACE_NAMES
from ..models import (
    AnalysisRule,
    Base,
    Chart,
    ChartPalace,
    ChartPeriod,
    ChartShensha,
    ChartSnapshot,
    ChartStar,
    PalaceDefinition,
    PatternDefinition,
    Person,
    RulePackage,
    School,
    Star,
    StarStatusDefinition,
    User,
)
from ..rules.patterns import RULES, PatternRule
from ..rules.period import all_decadals, decadal_direction
from .serialize import ENGINE_VERSION, chart_to_dict

STAR_STATUS_NAMES = ["庙", "旺", "得", "利", "平", "不", "陷"]
DEFAULT_SCHOOL = ("三合派", "sanhe")
DEFAULT_RULE_PACKAGE = ("三合派传统规则", ENGINE_VERSION)

# 神煞类型 ↔ Palace 属性名
SHENSHA_FIELDS = {
    "changsheng12": "changsheng12",
    "boshi12": "boshi12",
    "suiqian12": "suiqian12",
    "jiangqian12": "jiangqian12",
}


def make_session_factory(db_path: str | Path) -> sessionmaker:
    """创建会话工厂并建表。"""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def seed_base(session: Session) -> RulePackage:
    """播种知识库基础行与默认规则包，返回默认 RulePackage。"""
    if not session.scalar(select(PalaceDefinition).limit(1)):
        for seq, name in enumerate(PALACE_NAMES):
            session.add(PalaceDefinition(name=name, sequence=seq))
    if not session.scalar(select(StarStatusDefinition).limit(1)):
        for name in STAR_STATUS_NAMES:
            session.add(StarStatusDefinition(name=name))
    package = session.scalar(
        select(RulePackage).join(School).where(School.code == DEFAULT_SCHOOL[1])
    )
    if package is None:
        school = School(name=DEFAULT_SCHOOL[0], code=DEFAULT_SCHOOL[1], version=ENGINE_VERSION)
        session.flush()
        package = RulePackage(
            school=school, name=DEFAULT_RULE_PACKAGE[0], version=ENGINE_VERSION
        )
        session.add(package)
        session.flush()
    _seed_patterns(session, package)
    session.commit()
    return package


def _pattern_condition_json(rule: PatternRule) -> dict:
    """格局规则 → analysis_rule.condition_json（仅存非空字段）。"""
    cond: dict = {"name": rule.name}
    if rule.required:
        cond["required"] = sorted(rule.required)
    if rule.any_of:
        cond["any_of"] = [sorted(g) for g in rule.any_of]
    if rule.need_lu:
        cond["need_lu"] = True
    if rule.need_double_lu:
        cond["need_double_lu"] = True
    if rule.mutagens:
        cond["mutagens"] = sorted(rule.mutagens)
    if rule.bright_all:
        cond["bright_all"] = rule.bright_all
    if rule.soul_stars:
        cond["soul_stars"] = sorted(rule.soul_stars)
    if rule.soul_branches:
        cond["soul_branches"] = [EARTHLY_BRANCHES[b] for b in sorted(rule.soul_branches)]
    if rule.soul_only:
        cond["soul_only"] = True
    if rule.soul_mutagens:
        cond["soul_mutagens"] = sorted(rule.soul_mutagens)
    if rule.at_branch:
        cond["at_branch"] = {
            star: [EARTHLY_BRANCHES[b] for b in sorted(branches)]
            for star, branches in rule.at_branch
        }
    if rule.clamp_pair[0]:
        cond["clamp_pair"] = list(rule.clamp_pair)
    if rule.soul_body_pair[0]:
        cond["soul_body_pair"] = list(rule.soul_body_pair)
    if rule.empty_soul:
        cond["empty_soul"] = True
    if rule.special:
        cond["special"] = rule.special
    return cond


def _seed_patterns(session: Session, package: RulePackage) -> None:
    """以 rules.patterns.RULES 为唯一来源，播种格局知识库与分析规则（按名幂等更新）。"""
    defs = {d.name: d for d in session.scalars(select(PatternDefinition)).all()}
    analysis = {
        (r.result_json or {}).get("name"): r
        for r in session.scalars(
            select(AnalysisRule).where(
                AnalysisRule.rule_package_id == package.id,
                AnalysisRule.rule_type == "格局",
            )
        ).all()
    }
    for priority, rule in enumerate(RULES):
        description = f"{rule.condition}。{rule.explain}"
        row = defs.get(rule.name)
        if row is None:
            session.add(
                PatternDefinition(
                    name=rule.name, category=rule.category, description=description
                )
            )
        else:
            row.category = rule.category
            row.description = description
        condition_json = _pattern_condition_json(rule)
        result_json = {
            "name": rule.name,
            "category": rule.category,
            "domain": rule.domain,
            "explain": rule.explain,
        }
        arule = analysis.get(rule.name)
        if arule is None:
            session.add(
                AnalysisRule(
                    rule_package_id=package.id,
                    rule_type="格局",
                    condition_json=condition_json,
                    result_json=result_json,
                    priority=priority,
                )
            )
        else:
            arule.condition_json = condition_json
            arule.result_json = result_json
            arule.priority = priority


def _default_user(session: Session) -> User:
    """本地桌面 MVP：单一本地账号。"""
    user = session.scalar(select(User).where(User.username == "local"))
    if user is None:
        user = User(username="local", email="local@localhost", password_hash="")
        session.add(user)
        session.flush()
    return user


def _star_row(session: Session, name: str, category: str) -> Star:
    star = session.scalar(select(Star).where(Star.name == name))
    if star is None:
        star = Star(name=name, code=name, category=category)
        session.add(star)
        session.flush()
    return star


def save_chart(
    session: Session,
    chart: NatalChart,
    *,
    person_name: str = "未命名",
    rule_package: RulePackage | None = None,
) -> Chart:
    """完整命盘落库（含快照）。返回 Chart 行。"""
    cal = chart.calendar
    sk = chart.skeleton
    package = rule_package or seed_base(session)
    user = _default_user(session)

    person = Person(user_id=user.id, name=person_name, gender=chart.birth.gender)
    session.add(person)
    session.flush()

    row = Chart(
        person_id=person.id,
        rule_package_id=package.id,
        engine_version=ENGINE_VERSION,
        solar_datetime=datetime(
            chart.birth.solar_year, chart.birth.solar_month, chart.birth.solar_day
        ),
        hour_index=chart.birth.hour_index,
        lunar_datetime=f"{cal.lunar_year}-{cal.lunar_month}-{cal.lunar_day}"
        + ("(闰)" if cal.is_leap else ""),
        gender=chart.birth.gender,
        life_master=sk.soul,
        body_master=sk.body,
        body_palace=sk.palaces[sk.body_palace_branch].name,
        origin_palace="",
    )
    session.add(row)
    session.flush()

    _fill_chart_rows(session, row, chart)

    session.add(ChartSnapshot(
        chart_id=row.id,
        json_content=chart_to_dict(chart),
        engine_version=ENGINE_VERSION,
    ))
    session.commit()
    return row


def _fill_chart_rows(session: Session, row: Chart, chart: NatalChart) -> None:
    """写入（整体替换）命盘的结构化实例行：十二宫、星曜、神煞、大限。"""
    cal = chart.calendar
    sk = chart.skeleton

    palace_defs = {p.name: p for p in session.scalars(select(PalaceDefinition))}
    status_defs = {s.name: s for s in session.scalars(select(StarStatusDefinition))}

    direction = decadal_direction(cal.year_gan, chart.birth.gender)
    decadals = all_decadals(sk.soul_palace_branch, sk.class_number, direction)

    for branch in range(12):
        p = sk.palaces[branch]
        palace_row = ChartPalace(
            chart_id=row.id,
            palace_definition_id=palace_defs[p.name].id,
            heavenly_stem=HEAVENLY_STEMS[p.heavenly_stem],
            earth_branch=EARTHLY_BRANCHES[p.earthly_branch],
            position=branch,
        )
        session.add(palace_row)
        session.flush()

        for s in p.major_stars + p.minor_stars + p.adjective_stars:
            session.add(ChartStar(
                chart_id=row.id,
                chart_palace_id=palace_row.id,
                star_id=_star_row(session, s.name, s.star_type).id,
                category=s.star_type,
                status_id=status_defs[s.brightness].id if s.brightness in status_defs else None,
                birth_hua=s.mutagen or None,
            ))

        for shensha_type, attr in SHENSHA_FIELDS.items():
            value = getattr(p, attr, "")
            if value:
                session.add(ChartShensha(
                    chart_id=row.id,
                    chart_palace_id=palace_row.id,
                    type=shensha_type,
                    name=value,
                ))

        dec = next(d for d in decadals if d.palace_branch == branch)
        session.add(ChartPeriod(
            chart_id=row.id,
            period_type="大限",
            age_start=dec.age_start,
            age_end=dec.age_end,
            chart_palace_id=palace_row.id,
        ))


def update_chart(
    session: Session,
    chart_id: int,
    chart: NatalChart,
    *,
    person_name: str,
) -> Chart | None:
    """编辑命盘：替换结构化实例行并追加新快照（旧快照保留作历史版本）。

    出生参数与姓名均可改；出生参数变化即整体重排。命盘不存在返回 None。
    """
    row = session.get(Chart, chart_id)
    if row is None:
        return None
    cal = chart.calendar
    sk = chart.skeleton

    # 先删子表再重灌；快照不删，保留编辑前版本
    for model in (ChartStar, ChartShensha, ChartPeriod, ChartPalace):
        session.execute(delete(model).where(model.chart_id == chart_id))

    row.engine_version = ENGINE_VERSION
    row.solar_datetime = datetime(
        chart.birth.solar_year, chart.birth.solar_month, chart.birth.solar_day
    )
    row.hour_index = chart.birth.hour_index
    row.lunar_datetime = f"{cal.lunar_year}-{cal.lunar_month}-{cal.lunar_day}" + (
        "(闰)" if cal.is_leap else ""
    )
    row.gender = chart.birth.gender
    row.life_master = sk.soul
    row.body_master = sk.body
    row.body_palace = sk.palaces[sk.body_palace_branch].name

    person = session.get(Person, row.person_id)
    if person is not None:
        person.name = person_name
        person.gender = chart.birth.gender

    _fill_chart_rows(session, row, chart)

    session.add(ChartSnapshot(
        chart_id=chart_id,
        json_content=chart_to_dict(chart),
        engine_version=ENGINE_VERSION,
    ))
    session.commit()
    return row


def delete_chart(session: Session, chart_id: int) -> bool:
    """删除命盘及其子表、快照；无其余命盘的 Person 一并删除。"""
    row = session.get(Chart, chart_id)
    if row is None:
        return False
    person_id = row.person_id
    siblings = session.scalar(
        select(func.count(Chart.id)).where(
            Chart.person_id == person_id, Chart.id != chart_id
        )
    )
    # 自下而上删除，避免外键悬挂（SQLite 默认不校验，但保持可移植）
    for model in (ChartStar, ChartShensha, ChartPeriod):
        session.execute(delete(model).where(model.chart_id == chart_id))
    session.execute(delete(ChartPalace).where(ChartPalace.chart_id == chart_id))
    session.execute(delete(ChartSnapshot).where(ChartSnapshot.chart_id == chart_id))
    session.delete(row)
    if not siblings:
        person = session.get(Person, person_id)
        if person is not None:
            session.delete(person)
    session.commit()
    return True


def _rename_deep(value: object) -> object:
    """递归把字符串值中的宫位旧称替换为现名（仅整串相等时）。"""
    if isinstance(value, dict):
        return {k: _rename_deep(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rename_deep(v) for v in value]
    if isinstance(value, str):
        return PALACE_NAME_ALIASES.get(value, value)
    return value


def migrate_legacy_names(session_factory: sessionmaker) -> None:
    """旧版本数据迁移：宫位旧称 → 现名（仆役→交友）。

    覆盖三处：palace_definition 字典行、chart.body_palace、历史快照 JSON。
    若字典中新旧名同时存在（name 唯一约束），先把 chart_palace 引用并到现名行，
    再删除旧名行。幂等：全部为新名时不产生任何写入。
    """
    from sqlalchemy import update

    with session_factory() as session:
        dirty = False

        for old, new in PALACE_NAME_ALIASES.items():
            legacy_def = session.scalar(select(PalaceDefinition).where(PalaceDefinition.name == old))
            if legacy_def is None:
                continue
            current_def = session.scalar(select(PalaceDefinition).where(PalaceDefinition.name == new))
            if current_def is None:
                legacy_def.name = new
            else:
                session.execute(
                    update(ChartPalace)
                    .where(ChartPalace.palace_definition_id == legacy_def.id)
                    .values(palace_definition_id=current_def.id)
                )
                session.delete(legacy_def)
            dirty = True

        for row in session.scalars(
            select(Chart).where(Chart.body_palace.in_(PALACE_NAME_ALIASES))
        ).all():
            row.body_palace = PALACE_NAME_ALIASES[row.body_palace]
            dirty = True

        for snap in session.scalars(select(ChartSnapshot)).all():
            renamed = _rename_deep(snap.json_content)
            if renamed != snap.json_content:
                snap.json_content = renamed  # type: ignore[assignment]
                dirty = True

        if dirty:
            session.commit()


def ensure_chart_hour_index(session_factory: sessionmaker) -> None:
    """旧库补列：chart.hour_index（SQLite 的 create_all 不会 ALTER 旧表）。"""
    engine = session_factory.kw["bind"]
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(chart)"))}
        if "hour_index" not in cols:
            conn.execute(text("ALTER TABLE chart ADD COLUMN hour_index INTEGER"))
            conn.commit()


def backfill_hour_index(session_factory: sessionmaker) -> None:
    """旧数据回填：从各命盘最新快照的 input.hour_index 补 chart.hour_index。"""
    with session_factory() as session:
        rows = session.scalars(select(Chart).where(Chart.hour_index.is_(None))).all()
        dirty = False
        for row in rows:
            snap = session.scalar(
                select(ChartSnapshot)
                .where(ChartSnapshot.chart_id == row.id)
                .order_by(ChartSnapshot.id.desc())
                .limit(1)
            )
            if snap is None:
                continue
            hour = (snap.json_content.get("input") or {}).get("hour_index")
            if hour is None:
                continue
            row.hour_index = int(hour)
            dirty = True
        if dirty:
            session.commit()


def load_snapshot(session: Session, chart_id: int) -> dict:
    """读取最新快照 JSON。"""
    snap = session.scalar(
        select(ChartSnapshot)
        .where(ChartSnapshot.chart_id == chart_id)
        .order_by(ChartSnapshot.id.desc())
    )
    if snap is None:
        raise KeyError(f"chart {chart_id} 无快照")
    return snap.json_content


def save_json_file(path: str | Path, chart: NatalChart) -> Path:
    """命盘导出 JSON 文件。"""
    path = Path(path)
    path.write_text(
        json.dumps(chart_to_dict(chart), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def load_json_file(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

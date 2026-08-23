"""命盘持久化：NatalChart → 四域数据库 + JSON 快照文件。

- 结构化落库：chart / chart_palace / chart_star / chart_shensha / chart_period
- 快照：chart_snapshot 表 + 本地 JSON 文件（biz_requirement.md §4.2）
- 知识库基础行（十二宫定义、星曜状态、默认流派规则包）首次自动播种
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ..chart.natal import NatalChart
from ..constants import EARTHLY_BRANCHES, HEAVENLY_STEMS, PALACE_NAMES
from ..models import (
    Base,
    Chart,
    ChartPalace,
    ChartPeriod,
    ChartShensha,
    ChartSnapshot,
    ChartStar,
    PalaceDefinition,
    Person,
    RulePackage,
    School,
    Star,
    StarStatusDefinition,
    User,
)
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
    session.commit()
    return package


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

    session.add(ChartSnapshot(
        chart_id=row.id,
        json_content=chart_to_dict(chart),
        engine_version=ENGINE_VERSION,
    ))
    session.commit()
    return row


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

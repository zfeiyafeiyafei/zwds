"""持久化与快照测试：落库结构完整性 + JSON 文件往返 + 编辑/删除/迁移。"""

import json

import pytest
from sqlalchemy import func, select

from ziwei_engine.calendar.converter import BirthInput
from ziwei_engine.chart.natal import calculate
from ziwei_engine.io.persist import (
    delete_chart,
    load_json_file,
    load_snapshot,
    make_session_factory,
    migrate_legacy_names,
    save_chart,
    save_json_file,
    update_chart,
)
from ziwei_engine.models import (
    AnalysisRule,
    Chart,
    ChartPalace,
    ChartPeriod,
    ChartSnapshot,
    ChartStar,
    PalaceDefinition,
    PatternDefinition,
    Person,
)
from ziwei_engine.rules.patterns import RULES


@pytest.fixture()
def session(tmp_path):
    sf = make_session_factory(tmp_path / "test.sqlite")
    with sf() as s:
        yield s


def test_save_chart_structure(session) -> None:
    chart = calculate(BirthInput(1990, 5, 15, 6, "男"))
    row = save_chart(session, chart, person_name="测试")

    palaces = session.scalar(
        select(func.count(ChartPalace.id)).where(ChartPalace.chart_id == row.id)
    )
    stars = session.scalar(
        select(func.count(ChartStar.id)).where(ChartStar.chart_id == row.id)
    )
    decadals = session.scalar(
        select(func.count(ChartPeriod.id)).where(ChartPeriod.chart_id == row.id)
    )
    assert palaces == 12
    assert stars == 14 + len([1 for p in chart.palaces for _ in p.minor_stars + p.adjective_stars])
    assert decadals == 12


def test_snapshot_round_trip(session, tmp_path) -> None:
    chart = calculate(BirthInput(1984, 2, 2, 12, "女"))
    row = save_chart(session, chart)
    snap = load_snapshot(session, row.id)
    assert snap["meta"]["five_elements_class"] == chart.skeleton.five_elements_class

    path = save_json_file(tmp_path / "chart.json", chart)
    back = load_json_file(path)
    assert back == json.loads(path.read_text())
    assert back["input"] == {"solar_date": "1984-02-02", "hour_index": 12, "gender": "女"}


def _child_counts(session, chart_id: int) -> tuple[int, int, int]:
    palaces = session.scalar(
        select(func.count(ChartPalace.id)).where(ChartPalace.chart_id == chart_id)
    )
    stars = session.scalar(
        select(func.count(ChartStar.id)).where(ChartStar.chart_id == chart_id)
    )
    periods = session.scalar(
        select(func.count(ChartPeriod.id)).where(ChartPeriod.chart_id == chart_id)
    )
    return palaces, stars, periods


def test_update_chart_replaces_children_and_keeps_history(session) -> None:
    row = save_chart(session, calculate(BirthInput(1990, 5, 15, 6, "男")), person_name="甲")

    new_chart = calculate(BirthInput(1985, 11, 20, 9, "女"))
    updated = update_chart(session, row.id, new_chart, person_name="乙")
    assert updated is not None

    # 结构化实例行按新命盘整体替换
    new_stars = len([1 for p in new_chart.palaces for _ in p.major_stars + p.minor_stars + p.adjective_stars])
    assert _child_counts(session, row.id) == (12, new_stars, 12)

    # 主表与人物字段更新
    row = session.get(Chart, row.id)
    assert row.gender == "女"
    assert (row.solar_datetime.year, row.solar_datetime.month) == (1985, 11)

    # 快照追加不覆盖：两版可各自读取，最新版为新参数
    snaps = session.scalars(
        select(ChartSnapshot).where(ChartSnapshot.chart_id == row.id).order_by(ChartSnapshot.id)
    ).all()
    assert len(snaps) == 2
    assert snaps[1].json_content["input"]["solar_date"] == "1985-11-20"
    assert load_snapshot(session, row.id)["input"]["solar_date"] == "1985-11-20"


def test_update_missing_chart_returns_none(session) -> None:
    assert update_chart(session, 999, calculate(BirthInput(1990, 5, 15, 6, "男")), person_name="x") is None


def test_delete_chart_removes_family(session) -> None:
    keep = save_chart(session, calculate(BirthInput(1990, 5, 15, 6, "男")), person_name="保留")
    gone = save_chart(session, calculate(BirthInput(1984, 2, 2, 12, "女")), person_name="删除")

    assert delete_chart(session, gone.id) is True
    assert delete_chart(session, gone.id) is False
    assert _child_counts(session, gone.id) == (0, 0, 0)
    assert session.get(Chart, gone.id) is None
    # 无其余命盘的 Person 一并删除；另一命盘不受影响
    persons = session.scalars(select(Person)).all()
    assert [p.name for p in persons] == ["保留"]
    assert _child_counts(session, keep.id)[0] == 12


def test_migrate_legacy_names(tmp_path) -> None:
    """旧称定义/主表字段/快照 JSON 全部迁到现名，且重复执行无副作用。"""
    sf = make_session_factory(tmp_path / "migrate.sqlite")
    with sf() as s:
        row = save_chart(s, calculate(BirthInput(1990, 5, 15, 6, "男")), person_name="迁移")
        # 模拟旧库：字典行还是旧名，身宫与历史快照带旧称
        friend_def = s.scalar(select(PalaceDefinition).where(PalaceDefinition.name == "交友"))
        friend_def.name = "仆役"
        s.get(Chart, row.id).body_palace = "仆役"
        s.add(ChartSnapshot(chart_id=row.id, json_content={"palaces": [{"name": "仆役"}, {"name": "命宫"}]}))
        s.commit()

    migrate_legacy_names(sf)
    migrate_legacy_names(sf)  # 幂等

    with sf() as s:
        assert s.scalar(select(PalaceDefinition).where(PalaceDefinition.name == "交友")) is not None
        assert s.scalar(select(PalaceDefinition).where(PalaceDefinition.name == "仆役")) is None
        assert s.get(Chart, row.id).body_palace == "交友"
        legacy = s.scalar(
            select(ChartSnapshot)
            .where(ChartSnapshot.chart_id == row.id)
            .order_by(ChartSnapshot.id.desc())
        )
        assert legacy.json_content == {"palaces": [{"name": "交友"}, {"name": "命宫"}]}
        # 结构化宫位行经外键继续指向改名后的定义
        palace_rows = s.scalars(select(ChartPalace).where(ChartPalace.chart_id == row.id)).all()
        def_ids = {p.palace_definition_id for p in palace_rows}
        renamed = s.scalar(select(PalaceDefinition).where(PalaceDefinition.name == "交友"))
        assert renamed.id in def_ids


def test_migrate_merges_when_both_names_exist(tmp_path) -> None:
    """异常状态：新旧名同时存在时，引用并到现名行并删除旧行，不违反唯一约束。"""
    sf = make_session_factory(tmp_path / "merge.sqlite")
    with sf() as s:
        row = save_chart(s, calculate(BirthInput(1990, 5, 15, 6, "男")), person_name="合并")
        dup = PalaceDefinition(name="仆役", sequence=7)
        s.add(dup)
        s.flush()
        palace_row = s.scalar(
            select(ChartPalace).where(ChartPalace.chart_id == row.id).limit(1)
        )
        palace_row.palace_definition_id = dup.id
        s.commit()

    migrate_legacy_names(sf)

    with sf() as s:
        assert s.scalar(select(PalaceDefinition).where(PalaceDefinition.name == "仆役")) is None
        current = s.scalar(select(PalaceDefinition).where(PalaceDefinition.name == "交友"))
        palace_row = s.get(ChartPalace, palace_row.id)
        assert palace_row.palace_definition_id == current.id
        # 该命盘 12 个宫位行的定义引用均完好
        cnt = s.scalar(
            select(func.count(ChartPalace.id)).where(ChartPalace.chart_id == row.id)
        )
        assert cnt == 12


def test_seed_patterns(session) -> None:
    """格局库播种：RULES 全量入 pattern_definition 与 analysis_rule，重复播种幂等。"""
    save_chart(session, calculate(BirthInput(1990, 5, 15, 6, "男")), person_name="甲")
    save_chart(session, calculate(BirthInput(1985, 11, 20, 9, "男")), person_name="乙")

    defs = session.scalars(select(PatternDefinition)).all()
    assert len(defs) == len(RULES)
    by_name = {d.name: d for d in defs}
    assert set(by_name) == {r.name for r in RULES}
    assert by_name["杀破狼"].category == "吉格"
    assert by_name["日月反背"].category == "凶格"
    assert "七杀、破军、贪狼会齐命宫三方" in by_name["杀破狼"].description

    arules = session.scalars(
        select(AnalysisRule).where(AnalysisRule.rule_type == "格局")
    ).all()
    assert len(arules) == len(RULES)
    by_result = {r.result_json["name"]: r for r in arules}
    assert by_result["明珠出海"].condition_json["at_branch"] == {
        "太阳": ["卯"],
        "太阴": ["亥"],
    }
    assert by_result["羊陀夹忌"].condition_json["soul_mutagens"] == ["忌"]
    assert by_result["命无正曜"].condition_json["empty_soul"] is True
    assert {r.priority for r in arules} == set(range(len(RULES)))

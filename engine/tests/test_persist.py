"""持久化与快照测试：落库结构完整性 + JSON 文件往返。"""

import json

import pytest
from sqlalchemy import func, select

from ziwei_engine.calendar.converter import BirthInput
from ziwei_engine.chart.natal import calculate
from ziwei_engine.io.persist import (
    load_json_file,
    load_snapshot,
    make_session_factory,
    save_chart,
    save_json_file,
)
from ziwei_engine.models import ChartPalace, ChartPeriod, ChartStar


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

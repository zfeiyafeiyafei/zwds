"""引擎 vs iztro 交叉验证。

每个 fixture 是 iztro astro.bySolar 的完整输出。
约定：iztro palaces[i].index 0 = 寅宫，即 branch = (index + 2) % 12；
本引擎 Palace 列表以地支索引存储。
"""

import json
import re
from pathlib import Path

import pytest

from ziwei_engine.calendar.converter import BirthInput
from ziwei_engine.chart.natal import calculate
from ziwei_engine.constants import EARTHLY_BRANCHES as Z
from ziwei_engine.constants import HEAVENLY_STEMS as G
from ziwei_engine.constants import PALACE_NAME_ALIASES

FIXTURES = Path(__file__).parent / "fixtures"


def _alias(name: str) -> str:
    """夹具来自 iztro 原始输出，宫名旧称映射为本产品命名（仆役→交友）。"""
    return PALACE_NAME_ALIASES.get(name, name)


def _load(path: Path) -> tuple[BirthInput, dict]:
    m = re.match(r"ref_(\d{4})(\d{2})(\d{2})_(\d+)_([mf])\.json", path.name)
    assert m, path.name
    y, mo, d, h = int(m[1]), int(m[2]), int(m[3]), int(m[4])
    gender = "男" if m[5] == "m" else "女"
    return BirthInput(y, mo, d, h, gender), json.loads(path.read_text())


def _iz_branch(palace: dict) -> int:
    return (palace["index"] + 2) % 12


def _params() -> list[Path]:
    return sorted(FIXTURES.glob("ref_*.json"))


@pytest.mark.parametrize("fixture", _params(), ids=lambda p: p.stem)
def test_calendar(fixture: Path) -> None:
    birth, ref = _load(fixture)
    from ziwei_engine.calendar.converter import convert

    cal = convert(birth)
    iz = ref["rawDates"]
    iz_gz = [tuple(iz["chineseDate"][k]) for k in ("yearly", "monthly", "daily", "hourly")]
    my_gz = [
        (G[cal.year_gan], Z[cal.year_zhi]),
        (G[cal.month_gan], Z[cal.month_zhi]),
        (G[cal.day_gan], Z[cal.day_zhi]),
        (G[cal.hour_gan], Z[cal.hour_zhi]),
    ]
    assert my_gz == iz_gz
    iz_l = iz["lunarDate"]
    assert (cal.lunar_year, cal.lunar_month, cal.lunar_day, cal.is_leap) == (
        iz_l["lunarYear"], iz_l["lunarMonth"], iz_l["lunarDay"], iz_l["isLeap"],
    )


@pytest.mark.parametrize("fixture", _params(), ids=lambda p: p.stem)
def test_skeleton(fixture: Path) -> None:
    birth, ref = _load(fixture)
    sk = calculate(birth).skeleton
    assert Z[sk.soul_palace_branch] == ref["earthlyBranchOfSoulPalace"]
    assert Z[sk.body_palace_branch] == ref["earthlyBranchOfBodyPalace"]
    assert sk.five_elements_class == ref["fiveElementsClass"]
    assert sk.soul == ref["soul"]
    assert sk.body == ref["body"]
    for p in ref["palaces"]:
        my = sk.palaces[_iz_branch(p)]
        assert my.name == _alias(p["name"])
        assert G[my.heavenly_stem] == p["heavenlyStem"]
        assert my.is_body_palace == p["isBodyPalace"]


@pytest.mark.parametrize("fixture", _params(), ids=lambda p: p.stem)
def test_major_stars_and_sihua(fixture: Path) -> None:
    birth, ref = _load(fixture)
    chart = calculate(birth)
    for p in ref["palaces"]:
        branch = _iz_branch(p)
        iz = {s["name"]: (s.get("mutagen") or "").replace("化", "") for s in p["majorStars"]}
        my = {s.name: s.mutagen for s in chart.palaces[branch].major_stars}
        assert my == iz, f"branch {Z[branch]}"

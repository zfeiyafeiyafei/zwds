"""辅星/杂曜/神煞/宫内周期 vs iztro 逐宫对齐验证。

对照约定同 test_cross_validation：iztro palaces[i].index 0 = 寅宫，
branch = (index + 2) % 12；星曜集合比较顺序无关；mutagen 单字。
"""

import json
import re
from pathlib import Path

import pytest

from ziwei_engine.calendar.converter import BirthInput
from ziwei_engine.chart.natal import calculate
from ziwei_engine.constants import EARTHLY_BRANCHES as Z

FIXTURES = Path(__file__).parent / "fixtures"


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
def test_minor_stars(fixture: Path) -> None:
    """每宫 minorStars：name + mutagen + brightness 完全一致。"""
    birth, ref = _load(fixture)
    chart = calculate(birth)
    for p in ref["palaces"]:
        branch = _iz_branch(p)
        iz = {
            s["name"]: ((s.get("mutagen") or "").replace("化", ""), s.get("brightness") or "")
            for s in p["minorStars"]
        }
        my = {s.name: (s.mutagen, s.brightness) for s in chart.palaces[branch].minor_stars}
        assert my == iz, f"branch {Z[branch]}: mine={my} iztro={iz}"


@pytest.mark.parametrize("fixture", _params(), ids=lambda p: p.stem)
def test_major_star_brightness(fixture: Path) -> None:
    """主星亮度（iztro_rules.md §9 七级）。"""
    birth, ref = _load(fixture)
    chart = calculate(birth)
    for p in ref["palaces"]:
        branch = _iz_branch(p)
        iz = {s["name"]: s.get("brightness") or "" for s in p["majorStars"]}
        my = {s.name: s.brightness for s in chart.palaces[branch].major_stars}
        assert my == iz, f"branch {Z[branch]}: mine={my} iztro={iz}"


@pytest.mark.parametrize("fixture", _params(), ids=lambda p: p.stem)
def test_adjective_stars(fixture: Path) -> None:
    """每宫 adjectiveStars：星名集合一致（杂曜无亮度/四化）。"""
    birth, ref = _load(fixture)
    chart = calculate(birth)
    for p in ref["palaces"]:
        branch = _iz_branch(p)
        iz = sorted(s["name"] for s in p["adjectiveStars"])
        my = sorted(s.name for s in chart.palaces[branch].adjective_stars)
        assert my == iz, f"branch {Z[branch]}: mine={my} iztro={iz}"


@pytest.mark.parametrize("fixture", _params(), ids=lambda p: p.stem)
def test_decorative_stars(fixture: Path) -> None:
    """长生/博士/岁前/将前十二神（iztro_rules.md §11）。"""
    birth, ref = _load(fixture)
    chart = calculate(birth)
    for p in ref["palaces"]:
        my = chart.palaces[_iz_branch(p)]
        got = (my.changsheng12, my.boshi12, my.suiqian12, my.jiangqian12)
        want = (p["changsheng12"], p["boshi12"], p["suiqian12"], p["jiangqian12"])
        assert got == want, f"palace {p['index']}: mine={got} iztro={want}"


@pytest.mark.parametrize("fixture", _params(), ids=lambda p: p.stem)
def test_palace_periods(fixture: Path) -> None:
    """小限虚岁序列、大限区间、来因宫（iztro_rules.md §12/§13/§4）。"""
    birth, ref = _load(fixture)
    chart = calculate(birth)
    for p in ref["palaces"]:
        my = chart.palaces[_iz_branch(p)]
        assert my.ages == p["ages"], f"palace {p['index']} ages"
        assert list(my.decadal_range) == p["decadal"]["range"], f"palace {p['index']} decadal"
        assert my.is_original_palace == p["isOriginalPalace"], f"palace {p['index']} original"

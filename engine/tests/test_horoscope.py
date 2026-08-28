"""locate_horoscope 编排测试：fixture 交叉验证 + 历法边界 + 未上运。"""

import json
import re
from datetime import date
from pathlib import Path

import pytest

from ziwei_engine.calendar.converter import BirthInput, convert
from ziwei_engine.chart.layout import build_skeleton
from ziwei_engine.constants import EARTHLY_BRANCHES as Z
from ziwei_engine.constants import PALACE_NAME_ALIASES
from ziwei_engine.rules.horoscope import locate_horoscope

FIXTURES = Path(__file__).parent / "fixtures"


def _load(path: Path) -> tuple[BirthInput, int, dict]:
    m = re.match(r"refh_(\d{4})(\d{2})(\d{2})_(\d+)_([mf])_(\d{4})\.json", path.name)
    assert m, path.name
    birth = BirthInput(int(m[1]), int(m[2]), int(m[3]), int(m[4]), "男" if m[5] == "m" else "女")
    return birth, int(m[6]), json.loads(path.read_text())


def _alias(name: str) -> str:
    """iztro 宫名旧称映射（仆役→交友）。"""
    return PALACE_NAME_ALIASES.get(name, name)


def _ref_names_per_branch(ref_block: dict) -> dict[str, str]:
    """夹具 palaceNames 数组（从寅宫起）→ {地支: 宫名}。"""
    return {Z[(i + 2) % 12]: _alias(n) for i, n in enumerate(ref_block["palaceNames"])}


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("refh_*.json")), ids=lambda p: p.stem)
def test_locate_matches_iztro(fixture: Path) -> None:
    """与 iztro horoscope 输出对齐（目标日 = 目标年 6 月 1 日）。"""
    birth, target_year, ref = _load(fixture)
    cal = convert(birth)
    sk = build_skeleton(cal)
    h = locate_horoscope(birth, cal, sk.soul_palace_branch, sk.class_number, date(target_year, 6, 1))

    assert h.nominal_age == ref["age"]["nominalAge"]
    assert Z[h.decadal.palace_branch] == ref["decadal"]["earthlyBranch"]
    assert h.decadal.age_start == sk.class_number + h.decadal.index * 10
    assert Z[h.xiaoxian_branch] == ref["age"]["earthlyBranch"]
    assert Z[h.yearly_zhi] == ref["yearly"]["earthlyBranch"]
    # 流年四化 = 流年干四化，按 禄权科忌 序
    expected = dict(zip(ref["yearly"]["mutagen"], "禄权科忌"))
    assert h.yearly_mutagens == expected


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("refh_*.json")), ids=lambda p: p.stem)
def test_derived_palace_names_matches_iztro(fixture: Path) -> None:
    """运限十二宫名与 iztro palaceNames 一致（命宫起地支递减，同本命构架）。"""
    birth, target_year, ref = _load(fixture)
    cal = convert(birth)
    sk = build_skeleton(cal)
    h = locate_horoscope(birth, cal, sk.soul_palace_branch, sk.class_number, date(target_year, 6, 1))

    assert h.decadal_palace_names == _ref_names_per_branch(ref["decadal"])
    assert h.yearly_palace_names == _ref_names_per_branch(ref["yearly"])
    assert h.xiaoxian_palace_names == _ref_names_per_branch(ref["age"])


def test_lunar_new_year_boundary() -> None:
    """正月初一分界：春节前后虚岁差一岁。"""
    birth = BirthInput(1990, 5, 15, 6, "男")
    cal = convert(birth)
    sk = build_skeleton(cal)
    before = locate_horoscope(birth, cal, sk.soul_palace_branch, sk.class_number, date(2026, 2, 15))
    after = locate_horoscope(birth, cal, sk.soul_palace_branch, sk.class_number, date(2026, 2, 17))
    assert before.lunar_year == 2025 and before.nominal_age == 36
    assert after.lunar_year == 2026 and after.nominal_age == 37


def test_decadal_none_before_start_age() -> None:
    """出生当年虚岁 1 < 局数：无大限，小限仍定位。"""
    birth = BirthInput(2020, 6, 1, 6, "男")
    cal = convert(birth)
    sk = build_skeleton(cal)
    h = locate_horoscope(birth, cal, sk.soul_palace_branch, sk.class_number, date(2020, 8, 1))
    assert h.nominal_age == 1
    assert h.decadal is None
    assert 0 <= h.xiaoxian_branch <= 11


def test_target_before_birth_raises() -> None:
    birth = BirthInput(1990, 5, 15, 6, "男")
    cal = convert(birth)
    sk = build_skeleton(cal)
    with pytest.raises(ValueError):
        locate_horoscope(birth, cal, sk.soul_palace_branch, sk.class_number, date(1980, 1, 1))

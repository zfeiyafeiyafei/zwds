"""大限/流年/小限 vs iztro horoscope 交叉验证。

fixture 命名：refh_YYYYMMDD_<hour>_<m|f>_<targetYear>.json
验证：虚岁、大限宫位、小限宫位、流年宫位、流年四化。
"""

import json
import re
from pathlib import Path

import pytest
from lunar_python import Solar

from ziwei_engine.calendar.converter import BirthInput, convert
from ziwei_engine.chart.layout import build_skeleton
from ziwei_engine.constants import EARTHLY_BRANCHES as Z
from ziwei_engine.constants import HEAVENLY_STEMS as G
from ziwei_engine.rules import period
from ziwei_engine.rules.sihua import birth_mutagens

FIXTURES = Path(__file__).parent / "fixtures"


def _load(path: Path) -> tuple[BirthInput, int, dict]:
    m = re.match(r"refh_(\d{4})(\d{2})(\d{2})_(\d+)_([mf])_(\d{4})\.json", path.name)
    assert m, path.name
    birth = BirthInput(
        int(m[1]), int(m[2]), int(m[3]), int(m[4]), "男" if m[5] == "m" else "女"
    )
    return birth, int(m[6]), json.loads(path.read_text())


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("refh_*.json")), ids=lambda p: p.stem)
def test_periods(fixture: Path) -> None:
    birth, target_year, ref = _load(fixture)
    cal = convert(birth)
    sk = build_skeleton(cal)

    # 以目标年中点（6月1日）的农历年计算虚岁，与生成 fixture 时的目标日一致
    target_lunar = Solar.fromYmd(target_year, 6, 1).getLunar()
    nominal_age = target_lunar.getYear() - cal.lunar_year + 1
    assert ref["age"]["nominalAge"] == nominal_age

    direction = period.decadal_direction(cal.year_gan, birth.gender)
    dec = period.decadal_at(sk.soul_palace_branch, sk.class_number, direction, nominal_age)
    assert Z[dec.palace_branch] == ref["decadal"]["earthlyBranch"]
    assert G[sk.palaces[dec.palace_branch].heavenly_stem] == ref["decadal"]["heavenlyStem"]

    xx = period.xiaoxian_branch(cal.year_zhi, birth.gender, nominal_age)
    assert Z[xx] == ref["age"]["earthlyBranch"]
    assert G[sk.palaces[xx].heavenly_stem] == ref["age"]["heavenlyStem"]

    # 流年：流年命宫 = 流年地支所在宫；流年四化 = 流年干四化
    yearly_gz = target_lunar.getYearInGanZhi()
    year_gan, year_zhi = G.index(yearly_gz[0]), Z.index(yearly_gz[1])
    assert Z[year_zhi] == ref["yearly"]["earthlyBranch"]
    assert G[year_gan] == ref["yearly"]["heavenlyStem"]
    iz_yearly_mutagen = ref["yearly"]["mutagen"]  # [禄,权,科,忌] 星名
    my = birth_mutagens(year_gan)
    assert [s for s, _ in sorted(my.items(), key=lambda kv: "禄权科忌".index(kv[1]))] == iz_yearly_mutagen

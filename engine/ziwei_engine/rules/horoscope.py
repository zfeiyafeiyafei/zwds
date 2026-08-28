"""运限定位：按目标日期定位大限 / 流年 / 小限（biz_requirement.md §4.1.2-4.1.4）。

规则（对齐 iztro，horoscopeDivide='normal'）：
- 目标农历年按正月初一分界；虚岁 = 目标农历年 - 生农历年 + 1
- 大限：命宫起 [局数+10k, 局数+10k+9]，阳男阴女顺行；未达起限虚岁则无大限
- 流年命宫 = 流年地支所在宫；流年四化 = 流年干四化（SIHUA 表）
- 小限：生年支三合局起宫，一岁一宫，男顺女逆
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from lunar_python import Solar

from ..calendar.converter import BirthInput, CalendarInfo
from ..constants import EARTHLY_BRANCHES
from .period import Decadal, decadal_at, decadal_direction, xiaoxian_branch
from .sihua import HUA_NAMES, SIHUA

# 运限十二宫名：以运限命宫起逆时针（地支递减）排列，与本命十二宫同构
DERIVED_PALACE_NAMES = [
    "命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄",
    "迁移", "交友", "官禄", "田宅", "福德", "父母",
]


def derived_palace_names(base_branch: int) -> dict[str, str]:
    """运限十二宫映射：{地支: 宫名}（运限命宫落 base_branch）。

    规则与本命盘一致：命宫起按地支递减方向依次排兄弟…父母，
    对齐 iztro horoscope 输出的 palaceNames 数组（refh_*.json 夹具可交叉验证）。
    """
    return {
        EARTHLY_BRANCHES[(base_branch - k) % 12]: DERIVED_PALACE_NAMES[k]
        for k in range(12)
    }


@dataclass(frozen=True)
class HoroscopeInfo:
    """某目标日期的运限定位结果。"""

    target_date: str  # YYYY-MM-DD
    lunar_year: int  # 目标农历年（正月初一分界）
    nominal_age: int  # 虚岁
    decadal: Decadal | None  # None = 未上运（虚岁 < 局数）
    decadal_palace_names: dict[str, str]  # 大限十二宫 {地支: 宫名}
    yearly_gan: int  # 流年干索引
    yearly_zhi: int  # 流年支索引（= 流年命宫地支）
    yearly_mutagens: dict[str, str]  # {星名: 禄/权/科/忌}
    yearly_palace_names: dict[str, str]  # 流年十二宫
    xiaoxian_branch: int  # 小限落地支索引
    xiaoxian_palace_names: dict[str, str]  # 小限十二宫


def locate_horoscope(
    birth: BirthInput,
    cal: CalendarInfo,
    soul_branch: int,
    class_number: int,
    target: date | None = None,
) -> HoroscopeInfo:
    """以目标公历日期（默认今天）定位当前大限 / 流年 / 小限。"""
    t = target or date.today()
    lunar = Solar.fromYmd(t.year, t.month, t.day).getLunar()
    lunar_year = lunar.getYear()  # 正月初一分界（iztro horoscopeDivide normal）
    if lunar_year < cal.lunar_year:
        raise ValueError(f"目标日期 {t.isoformat()} 早于出生年")

    nominal_age = lunar_year - cal.lunar_year + 1
    yearly_gan = lunar.getYearGanIndex()
    yearly_zhi = lunar.getYearZhiIndex()

    decadal: Decadal | None = None
    if nominal_age >= class_number:
        direction = decadal_direction(cal.year_gan, birth.gender)
        decadal = decadal_at(soul_branch, class_number, direction, nominal_age)

    return HoroscopeInfo(
        target_date=t.isoformat(),
        lunar_year=lunar_year,
        nominal_age=nominal_age,
        decadal=decadal,
        decadal_palace_names=(
            derived_palace_names(decadal.palace_branch) if decadal is not None else {}
        ),
        yearly_gan=yearly_gan,
        yearly_zhi=yearly_zhi,
        yearly_mutagens=dict(zip(SIHUA[yearly_gan], HUA_NAMES)),
        yearly_palace_names=derived_palace_names(yearly_zhi),
        xiaoxian_branch=xiaoxian_branch(cal.year_zhi, birth.gender, nominal_age),
        xiaoxian_palace_names=derived_palace_names(
            xiaoxian_branch(cal.year_zhi, birth.gender, nominal_age)
        ),
    )

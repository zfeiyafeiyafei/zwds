"""历法转换：公历输入 → 农历日期 + 干支四柱 + 时辰地支。

封装 lunar_python，输出排盘所需的全部历法信息。
边界规则（立春/正月初一、晚子时跨日）以 docs/iztro_rules.md 为准对齐 iztro 行为。
"""

from __future__ import annotations

from dataclasses import dataclass

from lunar_python import Solar

from ..constants import hour_index_to_branch, hour_index_to_clock


@dataclass(frozen=True)
class BirthInput:
    """排盘输入。"""

    solar_year: int
    solar_month: int
    solar_day: int
    hour_index: int  # 0=早子时 ... 11=亥时, 12=晚子时
    gender: str  # "男" | "女"


@dataclass(frozen=True)
class CalendarInfo:
    """历法计算结果：排盘所需的全部历法数据。"""

    lunar_year: int
    lunar_month: int  # 1-12，闰月由 is_leap 标记
    lunar_day: int
    is_leap: bool
    natal_day: int  # 安星用农历日；晚子时按次日
    hour_branch: int  # 时支索引 0=子
    year_gan: int
    year_zhi: int
    month_gan: int
    month_zhi: int
    day_gan: int
    day_zhi: int
    hour_gan: int
    hour_zhi: int
    zodiac: str


def _gz_pair(gz: str) -> tuple[int, int]:
    from ..constants import EARTHLY_BRANCHES, HEAVENLY_STEMS

    return HEAVENLY_STEMS.index(gz[0]), EARTHLY_BRANCHES.index(gz[1])


def _month_ganzhi(year_gan: int, lunar_month: int) -> tuple[int, int]:
    """五虎遁：年上起月。正月建寅，闰月干支同本月。

    正月干 = (年干 % 5) * 2 + 2 （甲己→丙, 乙庚→戊, 丙辛→庚, 丁壬→壬, 戊癸→甲）
    """
    first_gan = (year_gan % 5) * 2 + 2
    gan = (first_gan + lunar_month - 1) % 10
    zhi = (lunar_month + 1) % 12  # 正月=寅(2)
    return gan, zhi


def convert(birth: BirthInput) -> CalendarInfo:
    """公历出生信息 → 历法信息。

    边界约定（对齐 iztro，经 fixtures 验证）：
    - 年柱以正月初一换年（非立春）
    - 月柱以农历月换月（非节气），由五虎遁得出
    - 晚子时（hour_index=12）全部四柱按次日计算
    """
    hour, minute = hour_index_to_clock(birth.hour_index)
    solar = Solar.fromYmdHms(
        birth.solar_year, birth.solar_month, birth.solar_day, hour, minute, 0
    )
    lunar = solar.getLunar()

    if birth.hour_index == 12:
        # 晚子时(23:00-24:00)：日柱/时柱 lunar_python 在 23:00 后自动按次日；
        # 年柱/月柱显式按次日农历计算（除夕晚子时跨年的边界情形）
        next_lunar = solar.next(1).getLunar()
        year_gan, year_zhi = _gz_pair(next_lunar.getYearInGanZhi())
        next_month = next_lunar.getMonth()
        month_gan, month_zhi = _month_ganzhi(year_gan, abs(next_month))
        day_gan, day_zhi = _gz_pair(lunar.getDayInGanZhiExact())
        natal_day = next_lunar.getDay()
    else:
        year_gan, year_zhi = _gz_pair(lunar.getYearInGanZhi())
        month_gan, month_zhi = _month_ganzhi(year_gan, abs(lunar.getMonth()))
        day_gan, day_zhi = _gz_pair(lunar.getDayInGanZhi())
        natal_day = lunar.getDay()
    hour_gan, hour_zhi = _gz_pair(lunar.getTimeInGanZhi())

    month = lunar.getMonth()
    is_leap = month < 0

    return CalendarInfo(
        lunar_year=lunar.getYear(),
        lunar_month=abs(month),
        lunar_day=lunar.getDay(),
        is_leap=is_leap,
        natal_day=natal_day,
        hour_branch=hour_index_to_branch(birth.hour_index),
        year_gan=year_gan,
        year_zhi=year_zhi,
        month_gan=month_gan,
        month_zhi=month_zhi,
        day_gan=day_gan,
        day_zhi=day_zhi,
        hour_gan=hour_gan,
        hour_zhi=hour_zhi,
        zodiac=lunar.getYearShengXiao(),
    )

"""命盘骨架：命宫/身宫定位、十二宫排布、宫干、五行局、命主身主。

规则（三合派传统，对齐 iztro）：
- 寅宫起正月，顺数至生月，再从该宫起子时逆数至生时 → 命宫
  ming_branch = (2 + lunar_month - 1 - hour_branch) % 12
- 同起法顺数至生时 → 身宫
  body_branch = (2 + lunar_month - 1 + hour_branch) % 12
- 十二宫从命宫起沿地支递减（逆时针）排：命兄夫子财疾迁仆官田福父
- 宫干：五虎遁，寅宫起正月干
- 五行局：命宫干支纳音
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..calendar.converter import CalendarInfo
from ..constants import PALACE_NAMES
from .nayin import five_elements_class

# 命主：由命宫地支定（子属贪狼 …）
SOUL_STAR_BY_BRANCH: list[str] = [
    "贪狼", "巨门", "禄存", "文曲", "廉贞", "武曲",
    "破军", "武曲", "廉贞", "文曲", "禄存", "巨门",
]

# 身主：由生年地支定（子年火星 …）
BODY_STAR_BY_BRANCH: list[str] = [
    "火星", "天相", "天梁", "天同", "文昌", "天机",
    "火星", "天相", "天梁", "天同", "文昌", "天机",
]


@dataclass
class Palace:
    """一个宫位实例。"""

    index: int  # 0-11，固定 = 地支索引
    earthly_branch: int
    heavenly_stem: int
    name: str  # 命宫/兄弟/…
    is_body_palace: bool = False
    major_stars: list = field(default_factory=list)
    minor_stars: list = field(default_factory=list)
    adjective_stars: list = field(default_factory=list)
    # 以下对齐 iztro Palace（iztro_rules.md §1.4），由 chart.natal.calculate 填充
    is_original_palace: bool = False  # 来因宫：宫支非子丑 且 宫干 == 生年干
    changsheng12: str = ""  # 长生十二神
    boshi12: str = ""  # 博士十二神
    suiqian12: str = ""  # 岁前十二神
    jiangqian12: str = ""  # 将前十二神
    ages: list = field(default_factory=list)  # 本宫小限虚岁（10 个）
    decadal_range: tuple = (0, 0)  # 本宫大限虚岁区间 [起, 止]


@dataclass
class ChartSkeleton:
    """排盘骨架：十二宫 + 元信息，星曜尚未安入。"""

    palaces: list[Palace]  # index 与地支索引一致
    soul_palace_branch: int  # 命宫地支
    body_palace_branch: int  # 身宫地支
    five_elements_class: str  # 五行局名
    class_number: int  # 局数 2-6
    soul: str  # 命主
    body: str  # 身主


def soul_palace_branch(lunar_month: int, hour_branch: int) -> int:
    return (2 + lunar_month - 1 - hour_branch) % 12


def body_palace_branch(lunar_month: int, hour_branch: int) -> int:
    return (2 + lunar_month - 1 + hour_branch) % 12


def build_skeleton(cal: CalendarInfo) -> ChartSkeleton:
    from ..constants import FIVE_ELEMENTS_CLASS

    soul_branch = soul_palace_branch(cal.lunar_month, cal.hour_branch)
    body_branch = body_palace_branch(cal.lunar_month, cal.hour_branch)

    # 宫干：寅宫起 = 五虎遁正月干；偏移以 12 取模（子=+10, 丑=+11）再对 10 取模
    first_gan = (cal.year_gan % 5) * 2 + 2
    palace_stems = [(first_gan + (branch - 2) % 12) % 10 for branch in range(12)]

    # 十二宫名：从命宫起地支递减
    palaces: list[Palace] = []
    for branch in range(12):
        offset = (soul_branch - branch) % 12  # 命宫 offset=0
        palaces.append(
            Palace(
                index=branch,
                earthly_branch=branch,
                heavenly_stem=palace_stems[branch],
                name=PALACE_NAMES[offset],
                is_body_palace=(branch == body_branch),
            )
        )

    ming_gan = palace_stems[soul_branch]
    fec = five_elements_class(ming_gan, soul_branch)

    return ChartSkeleton(
        palaces=palaces,
        soul_palace_branch=soul_branch,
        body_palace_branch=body_branch,
        five_elements_class=fec,
        class_number=FIVE_ELEMENTS_CLASS[fec],
        soul=SOUL_STAR_BY_BRANCH[soul_branch],
        body=BODY_STAR_BY_BRANCH[cal.year_zhi],
    )

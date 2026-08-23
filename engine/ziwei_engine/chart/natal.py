"""本命盘编排：历法 → 骨架 → 安星（主星/辅星/杂曜/神煞）→ 四化 → 周期标注。"""

from __future__ import annotations

from dataclasses import dataclass

from ..calendar.converter import BirthInput, CalendarInfo, convert
from ..rules.period import XIAOXIAN_START, decadal_direction
from ..rules.sihua import birth_mutagens
from ..stars import adjective as adj
from ..stars.brightness import get_brightness
from ..stars.major import place_major_stars
from ..stars.minor import LUCUN_BY_GAN, fix_day_index, fix_month_index, place_minor_stars
from .layout import ChartSkeleton, Palace, build_skeleton


@dataclass
class Star:
    """落宫星曜。"""

    name: str
    star_type: str  # major | minor | adjective
    mutagen: str = ""  # 禄/权/科/忌（生年四化）
    brightness: str = ""  # 庙/旺/得/利/平/不/陷


@dataclass
class NatalChart:
    """完整本命盘。"""

    birth: BirthInput
    calendar: CalendarInfo
    skeleton: ChartSkeleton

    @property
    def palaces(self) -> list[Palace]:
        return self.skeleton.palaces


def _place_stars(
    sk: ChartSkeleton,
    positions: dict[str, int],
    star_type: str,
    mutagens: dict[str, str],
    bucket: str,
) -> None:
    """把 {星名: 地支索引} 安入各宫的 minor_stars/adjective_stars。"""
    for name, branch in positions.items():
        star = Star(
            name=name,
            star_type=star_type,
            mutagen=mutagens.get(name, ""),
            brightness=get_brightness(name, branch),
        )
        getattr(sk.palaces[branch], bucket).append(star)


def _mark_periods(sk: ChartSkeleton, cal: CalendarInfo, gender: str) -> None:
    """宫内周期标注：来因宫、四组神煞、大限区间、小限虚岁（iztro_rules.md §4/§11/§12/§13）。"""
    lucun_branch = LUCUN_BY_GAN[cal.year_gan]
    cs = adj.changsheng12(sk.class_number, cal.year_zhi, gender)
    bs = adj.boshi12(lucun_branch, cal.year_zhi, gender)
    sq = adj.suiqian12(cal.year_zhi)
    jq = adj.jiangqian12(cal.year_zhi)

    direction = decadal_direction(cal.year_gan, gender)
    xiaoxian_start = XIAOXIAN_START[cal.year_zhi]
    xiaoxian_dir = 1 if gender == "男" else -1  # 小限男顺女逆（§13.1）

    for palace in sk.palaces:
        branch = palace.earthly_branch
        # 来因宫（§4）：宫支非子丑 且 宫干 == 生年干
        palace.is_original_palace = branch not in (0, 1) and palace.heavenly_stem == cal.year_gan
        palace.changsheng12 = cs[branch]
        palace.boshi12 = bs[branch]
        palace.suiqian12 = sq[branch]
        palace.jiangqian12 = jq[branch]
        # 大限（§12）：第 i 大限 range = [局数 + 10i, 局数 + 10i + 9]
        i = ((branch - sk.soul_palace_branch) * direction) % 12
        palace.decadal_range = (sk.class_number + 10 * i, sk.class_number + 10 * i + 9)
        # 小限（§13.1）：起宫 + 男顺女逆，每宫 10 个虚岁
        offset = ((branch - xiaoxian_start) * xiaoxian_dir) % 12
        palace.ages = [offset + 1 + 12 * j for j in range(10)]


def calculate(birth: BirthInput) -> NatalChart:
    """生成本命盘（主星/辅星/杂曜 + 生年四化 + 神煞 + 大限小限）。"""
    cal = convert(birth)
    sk = build_skeleton(cal)

    mutagens = birth_mutagens(cal.year_gan)
    for name, branch in place_major_stars(cal.natal_day, sk.class_number).items():
        sk.palaces[branch].major_stars.append(
            Star(
                name=name,
                star_type="major",
                mutagen=mutagens.get(name, ""),
                brightness=get_brightness(name, branch),
            )
        )

    # 辅星 14 颗（iztro_rules.md §8.1）；月/日索引含闰月与晚子时修正（§14）
    month_index = fix_month_index(cal.lunar_month, cal.is_leap, cal.lunar_day, birth.hour_index)
    day_index = fix_day_index(cal.lunar_day, birth.hour_index)
    t_idx = cal.hour_branch
    minor_pos = place_minor_stars(cal.year_gan, cal.year_zhi, month_index, t_idx)
    _place_stars(sk, minor_pos, "minor", mutagens, "minor_stars")

    # 杂曜 38 颗（§8.2-8.6，默认派）
    adj_pos = adj.place_adjective_stars(
        cal.year_gan,
        cal.year_zhi,
        month_index,
        day_index,
        t_idx,
        sk.soul_palace_branch,
        sk.body_palace_branch,
        minor_pos["左辅"],
        minor_pos["右弼"],
        minor_pos["文昌"],
        minor_pos["文曲"],
    )
    _place_stars(sk, adj_pos, "adjective", mutagens, "adjective_stars")

    _mark_periods(sk, cal, birth.gender)

    return NatalChart(birth=birth, calendar=cal, skeleton=sk)

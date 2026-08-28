"""命盘 JSON 序列化：引擎内部索引制 → 前端/存储友好的中文结构。

设计原则（biz_requirement.md §5.4/§6）：
- 数据与布局分离：不输出坐标，宫位以地支标识，布局由前端主题引擎计算
- display 区只存主题偏好，不存坐标
"""

from __future__ import annotations

from typing import Any
from dataclasses import asdict

from ..chart.natal import NatalChart
from ..constants import EARTHLY_BRANCHES, HEAVENLY_STEMS
from ..rules.horoscope import HoroscopeInfo
from ..rules.patterns import PatternMatch

ENGINE_VERSION = "0.1.0"

_DEFAULT_DISPLAY = {
    "default_theme": "traditional_grid",
    "available_themes": ["traditional_grid", "circular_equal_nodes", "modern_clean"],
    "current_layout": "traditional_grid",
}


def _star(s: Any) -> dict[str, Any]:
    d: dict[str, Any] = {"name": s.name, "type": s.star_type}
    if s.mutagen:
        d["mutagen"] = s.mutagen
    if s.brightness:
        d["brightness"] = s.brightness
    return d


def chart_to_dict(chart: NatalChart, *, display: dict | None = None) -> dict[str, Any]:
    """NatalChart → 标准 JSON 结构（宫位按 寅→丑 输出）。"""
    cal = chart.calendar
    sk = chart.skeleton
    birth = chart.birth

    palaces = []
    for branch in (list(range(2, 12)) + [0, 1]):  # 寅起
        p = sk.palaces[branch]
        palaces.append({
            "branch": EARTHLY_BRANCHES[p.earthly_branch],
            "stem": HEAVENLY_STEMS[p.heavenly_stem],
            "name": p.name,
            "is_body_palace": p.is_body_palace,
            "is_original_palace": getattr(p, "is_original_palace", False),
            "changsheng12": getattr(p, "changsheng12", ""),
            "boshi12": getattr(p, "boshi12", ""),
            "suiqian12": getattr(p, "suiqian12", ""),
            "jiangqian12": getattr(p, "jiangqian12", ""),
            "ages": getattr(p, "ages", []),
            "decadal_range": list(getattr(p, "decadal_range", ())),
            "major_stars": [_star(s) for s in p.major_stars],
            "minor_stars": [_star(s) for s in p.minor_stars],
            "adjective_stars": [_star(s) for s in p.adjective_stars],
        })

    return {
        "engine_version": ENGINE_VERSION,
        "input": {
            "solar_date": f"{birth.solar_year:04d}-{birth.solar_month:02d}-{birth.solar_day:02d}",
            "hour_index": birth.hour_index,
            "gender": birth.gender,
        },
        "calendar": {
            "lunar_year": cal.lunar_year,
            "lunar_month": cal.lunar_month,
            "lunar_day": cal.lunar_day,
            "is_leap": cal.is_leap,
            "zodiac": cal.zodiac,
            "ganzhi": {
                "year": HEAVENLY_STEMS[cal.year_gan] + EARTHLY_BRANCHES[cal.year_zhi],
                "month": HEAVENLY_STEMS[cal.month_gan] + EARTHLY_BRANCHES[cal.month_zhi],
                "day": HEAVENLY_STEMS[cal.day_gan] + EARTHLY_BRANCHES[cal.day_zhi],
                "hour": HEAVENLY_STEMS[cal.hour_gan] + EARTHLY_BRANCHES[cal.hour_zhi],
            },
        },
        "meta": {
            "soul_palace_branch": EARTHLY_BRANCHES[sk.soul_palace_branch],
            "body_palace_branch": EARTHLY_BRANCHES[sk.body_palace_branch],
            "five_elements_class": sk.five_elements_class,
            "class_number": sk.class_number,
            "soul": sk.soul,
            "body": sk.body,
        },
        "palaces": palaces,
        "display": display or dict(_DEFAULT_DISPLAY),
    }


def horoscope_to_dict(h: HoroscopeInfo) -> dict[str, Any]:
    """HoroscopeInfo → JSON 结构（biz_requirement.md §4.1.2-4.1.4）。

    palace_names：运限十二宫 {地支: 宫名}，前端据此标注 大命/大兄…、流命…、小命…。
    """
    decadal = None
    if h.decadal is not None:
        decadal = {
            "index": h.decadal.index,
            "branch": EARTHLY_BRANCHES[h.decadal.palace_branch],
            "age_start": h.decadal.age_start,
            "age_end": h.decadal.age_end,
            "palace_names": dict(h.decadal_palace_names),
        }
    return {
        "target_date": h.target_date,
        "lunar_year": h.lunar_year,
        "nominal_age": h.nominal_age,
        "decadal": decadal,
        "yearly": {
            "gan": HEAVENLY_STEMS[h.yearly_gan],
            "zhi": EARTHLY_BRANCHES[h.yearly_zhi],
            "mutagens": dict(h.yearly_mutagens),
            "palace_names": dict(h.yearly_palace_names),
        },
        "xiaoxian_branch": EARTHLY_BRANCHES[h.xiaoxian_branch],
        "xiaoxian_palace_names": dict(h.xiaoxian_palace_names),
    }

def patterns_to_dict(matches: list[PatternMatch]) -> list[dict[str, Any]]:
    """格局识别结果 → JSON 数组。"""
    return [asdict(m) for m in matches]

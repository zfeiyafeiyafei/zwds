"""辅星 14 颗安法（对齐 iztro getMinorStar，iztro_rules.md §8.1）。

输入记号（全部地支索引 0=子；公式与文档一致，仅把宫位索引换算为地支索引）：
- month_index：正月=0 的月索引，含闰月修正（§14.1）
- t_idx：时支索引 = fixIndex(timeIndex)，晚子时 12 → 0（§14.2.5）
- year_gan / year_zhi：生年干支索引（yearDivide=normal，正月初一分界）

14 颗：左辅 右弼 文昌 文曲 天魁 天钺 禄存 擎羊 陀罗 火星 铃星 地空 地劫 天马。
"""

from __future__ import annotations

# 天魁/天钺：年干 → 地支索引（iztro_rules.md §8.1 表）
KUI_YUE_BY_GAN: dict[int, tuple[int, int]] = {
    0: (1, 7),   # 甲 → 丑/未
    1: (0, 8),   # 乙 → 子/申
    2: (11, 9),  # 丙 → 亥/酉
    3: (11, 9),  # 丁 → 亥/酉
    4: (1, 7),   # 戊 → 丑/未
    5: (0, 8),   # 己 → 子/申
    6: (1, 7),   # 庚 → 丑/未
    7: (6, 2),   # 辛 → 午/寅
    8: (3, 5),   # 壬 → 卯/巳
    9: (3, 5),   # 癸 → 卯/巳
}

# 禄存：年干 → 地支索引（甲寅 乙卯 丙巳 丁午 戊巳 己午 庚申 辛酉 壬亥 癸子）
LUCUN_BY_GAN: list[int] = [2, 3, 5, 6, 5, 6, 8, 9, 11, 0]

# 天马：年支三合局 → 地支索引（寅午戌→申，申子辰→寅，巳酉丑→亥，亥卯未→巳）
TIANMA_BY_ZHI: dict[int, int] = {
    2: 8, 6: 8, 10: 8,     # 寅午戌 → 申
    8: 2, 0: 2, 4: 2,      # 申子辰 → 寅
    5: 11, 9: 11, 1: 11,   # 巳酉丑 → 亥
    11: 5, 3: 5, 7: 5,     # 亥卯未 → 巳
}

# 火星/铃星起子时的宫位（再顺加 t_idx）：年支组 寅午戌/申子辰/巳酉丑/亥卯未
HUOXING_START: dict[int, int] = {
    2: 1, 6: 1, 10: 1,     # 寅午戌 → 丑
    8: 2, 0: 2, 4: 2,      # 申子辰 → 寅
    5: 3, 9: 3, 1: 3,      # 巳酉丑 → 卯
    11: 9, 3: 9, 7: 9,     # 亥卯未 → 酉
}
LINGXING_START: dict[int, int] = {
    2: 3, 6: 3, 10: 3,             # 寅午戌 → 卯
    8: 10, 0: 10, 4: 10,           # 申子辰 → 戌
    5: 10, 9: 10, 1: 10,           # 巳酉丑 → 戌
    11: 10, 3: 10, 7: 10,          # 亥卯未 → 戌
}

MINOR_STARS: list[str] = [
    "左辅", "右弼", "文昌", "文曲", "天魁", "天钺", "禄存",
    "擎羊", "陀罗", "火星", "铃星", "地空", "地劫", "天马",
]


def fix_month_index(lunar_month: int, is_leap: bool, lunar_day: int, hour_index: int) -> int:
    """月索引（正月=0），含闰月修正（iztro_rules.md §14.1 fixLunarMonthIndex）。

    fixLeap=true（默认）：闰月 15 日（含）前按当月，16 日起按下月；
    晚子时（hour_index=12）不做闰月修正。
    """
    add = 1 if (is_leap and lunar_day > 15 and hour_index != 12) else 0
    return (lunar_month - 1 + add) % 12


def fix_day_index(lunar_day: int, hour_index: int) -> int:
    """日偏移（初一=0），iztro_rules.md §14.2.4：晚子时不减 1。"""
    return lunar_day if hour_index >= 12 else lunar_day - 1


def kui_yue_index(year_gan: int) -> tuple[int, int]:
    """天魁/天钺地支（iztro_rules.md §8.1，location.ts:205）。"""
    return KUI_YUE_BY_GAN[year_gan]


def lu_yang_tuo_ma_index(year_gan: int, year_zhi: int) -> dict[str, int]:
    """禄存/擎羊/陀罗/天马（iztro_rules.md §8.1，location.ts:118-197）。"""
    lucun = LUCUN_BY_GAN[year_gan]
    return {
        "禄存": lucun,
        "擎羊": (lucun + 1) % 12,
        "陀罗": (lucun - 1) % 12,
        "天马": TIANMA_BY_ZHI[year_zhi],
    }


def chang_qu_index(t_idx: int) -> tuple[int, int]:
    """文昌/文曲：戌上逆时 / 辰上顺时（iztro_rules.md §8.1，location.ts:278）。"""
    return (10 - t_idx) % 12, (4 + t_idx) % 12


def huo_ling_index(year_zhi: int, t_idx: int) -> tuple[int, int]:
    """火星/铃星：年支组起点 + 时支顺加（iztro_rules.md §8.1，location.ts:372）。"""
    return (HUOXING_START[year_zhi] + t_idx) % 12, (LINGXING_START[year_zhi] + t_idx) % 12


def kong_jie_index(t_idx: int) -> tuple[int, int]:
    """地空/地劫：亥上逆时 / 亥上顺时（iztro_rules.md §8.1，location.ts:347）。"""
    return (11 - t_idx) % 12, (11 + t_idx) % 12


def place_minor_stars(
    year_gan: int, year_zhi: int, month_index: int, t_idx: int
) -> dict[str, int]:
    """返回 {辅星名: 地支索引}（14 颗）。"""
    kui, yue = kui_yue_index(year_gan)
    chang, qu = chang_qu_index(t_idx)
    huo, ling = huo_ling_index(year_zhi, t_idx)
    kong, jie = kong_jie_index(t_idx)
    positions = {
        # 月系：辰起正月顺数 / 戌起正月逆数（location.ts:255）
        "左辅": (4 + month_index) % 12,
        "右弼": (10 - month_index) % 12,
        "文昌": chang,
        "文曲": qu,
        "天魁": kui,
        "天钺": yue,
        "火星": huo,
        "铃星": ling,
        "地空": kong,
        "地劫": jie,
    }
    positions.update(lu_yang_tuo_ma_index(year_gan, year_zhi))
    return positions

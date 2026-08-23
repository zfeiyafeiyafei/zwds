"""杂曜 38 颗 + 四组神煞（对齐 iztro getAdjectiveStar / decorativeStar）。

默认派（algorithm='default'）安置 38 颗杂曜（iztro_rules.md §8.6）：
- flower：红鸾 天喜 天姚 咸池
- helper：解神（月解）年解
- adjective：其余 32 颗
中州派专属（劫杀/大耗/龙德/截空，且不安截路空亡）不实现。

四组神煞（§11，每宫一个字符串，list 下标 = 地支索引）：
- changsheng12 长生十二神：五行局起长生，阳男阴女顺行
- boshi12 博士十二神：禄存起博士，阳男阴女顺行
- suiqian12 岁前十二神：生年支宫起岁建，顺行
- jiangqian12 将前十二神：将星位起，顺行
"""

from __future__ import annotations

# ---------------------------------------------------------------- 杂曜查表
# 月系（iztro_rules.md §8.4，location.ts:821）
JIESHEN_BY_MONTH: list[int] = [8, 8, 10, 10, 0, 0, 2, 2, 4, 4, 6, 6]  # 正二申 三四戌 …
YINSHA_BY_MONTH: list[int] = [2, 0, 10, 8, 6, 4]  # 寅子戌申午辰，month_index % 6
TIANYUE_BY_MONTH: list[int] = [10, 5, 4, 2, 7, 3, 11, 7, 2, 6, 10, 2]  # 戌巳辰寅未卯亥未寅午戌寅
TIANWU_BY_MONTH: list[int] = [5, 8, 2, 11]  # 巳申寅亥，month_index % 4

# 年支系（iztro_rules.md §8.5，location.ts:446-786）；下标 = 年支索引
XIANCHI_BY_ZHI: dict[int, int] = {
    2: 3, 6: 3, 10: 3, 8: 9, 0: 9, 4: 9, 5: 6, 9: 6, 1: 6, 11: 0, 3: 0, 7: 0,
}  # 寅午戌→卯 申子辰→酉 巳酉丑→午 亥卯未→子
HUAGAI_BY_ZHI: dict[int, int] = {
    2: 10, 6: 10, 10: 10, 8: 4, 0: 4, 4: 4, 5: 1, 9: 1, 1: 1, 11: 7, 3: 7, 7: 7,
}  # 寅午戌→戌 申子辰→辰 巳酉丑→丑 亥卯未→未
GUCHEN_BY_ZHI: dict[int, int] = {
    2: 5, 3: 5, 4: 5, 5: 8, 6: 8, 7: 8, 8: 11, 9: 11, 10: 11, 11: 2, 0: 2, 1: 2,
}  # 寅卯辰→巳 巳午未→申 申酉戌→亥 亥子丑→寅
GUASU_BY_ZHI: dict[int, int] = {
    2: 1, 3: 1, 4: 1, 5: 4, 6: 4, 7: 4, 8: 7, 9: 7, 10: 7, 11: 10, 0: 10, 1: 10,
}  # 寅卯辰→丑 巳午未→辰 申酉戌→未 亥子丑→戌
POSUI_BY_ZHI: list[int] = [5, 1, 9]  # 年支索引 % 3 → 巳/丑/酉
FEILIAN_BY_ZHI: list[int] = [8, 9, 10, 5, 6, 7, 2, 3, 4, 11, 0, 1]  # 申酉戌巳午未寅卯辰亥子丑
NIANJIE_BY_ZHI: list[int] = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 11]  # 戌起子逆数

# 年干系（§8.5，location.ts:652-690）；下标 = 年干索引
TIANCHU_BY_GAN: list[int] = [5, 6, 0, 5, 6, 8, 2, 6, 9, 11]  # 巳午子巳午申寅午酉亥
TIANGUAN_BY_GAN: list[int] = [7, 4, 5, 2, 3, 9, 11, 9, 10, 6]  # 未辰巳寅卯酉亥酉戌午
TIANFU_BY_GAN: list[int] = [9, 8, 0, 11, 3, 2, 6, 5, 6, 5]  # 酉申子亥卯寅午巳午巳
JIELU_BY_GAN: list[int] = [8, 6, 4, 2, 0]  # 年干索引 % 5 → 申午辰寅子
KONGWANG_BY_GAN: list[int] = [9, 7, 5, 3, 1]  # 年干索引 % 5 → 酉未巳卯丑

# ---------------------------------------------------------------- 神煞
CHANGSHENG12: list[str] = [
    "长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养",
]
# 五行局数 → 长生起点地支（§11.1：水二申 木三亥 金四巳 土五申 火六寅）
CHANGSHENG_START: dict[int, int] = {2: 8, 3: 11, 4: 5, 5: 8, 6: 2}

BOSHI12: list[str] = [
    "博士", "力士", "青龙", "小耗", "将军", "奏书", "飞廉", "喜神", "病符", "大耗", "伏兵", "官府",
]
SUIQIAN12: list[str] = [
    "岁建", "晦气", "丧门", "贯索", "官符", "小耗", "大耗", "龙德", "白虎", "天德", "吊客", "病符",
]
JIANGQIAN12: list[str] = [
    "将星", "攀鞍", "岁驿", "息神", "华盖", "劫煞", "灾煞", "天煞", "指背", "咸池", "月煞", "亡神",
]
# 将星起点：年支三合局（§11.4：寅午戌→午 申子辰→子 巳酉丑→酉 亥卯未→卯）
JIANGXING_START: dict[int, int] = {
    2: 6, 6: 6, 10: 6, 8: 0, 0: 0, 4: 0, 5: 9, 9: 9, 1: 9, 11: 3, 3: 3, 7: 3,
}

ADJECTIVE_STARS: list[str] = [
    "红鸾", "天喜", "天姚", "咸池",  # flower
    "解神", "年解",  # helper
    "三台", "八座", "恩光", "天贵", "龙池", "凤阁", "天才", "天寿",
    "台辅", "封诰", "天巫", "华盖", "天官", "天福", "天厨", "天月",
    "天德", "月德", "天空", "旬空", "截路", "空亡", "孤辰", "寡宿",
    "蜚廉", "破碎", "天刑", "阴煞", "天哭", "天虚", "天使", "天伤",
]


def xunkong_index(year_gan: int, year_zhi: int) -> int:
    """旬空（iztro_rules.md §8.5，location.ts:695-707）。

    xunkong = 年支 + (9 − 年干 + 1)；若与年支阴阳不同（索引奇偶不同）则再进一宫。
    （宫位索引与地支索引同奇偶，偏移 2 不影响，直接用地支索引运算。）
    """
    xk = (year_zhi + 10 - year_gan) % 12
    if year_zhi % 2 != xk % 2:
        xk = (xk + 1) % 12
    return xk


def place_adjective_stars(
    year_gan: int,
    year_zhi: int,
    month_index: int,
    day_index: int,
    t_idx: int,
    soul_branch: int,
    body_branch: int,
    zuofu: int,
    youbi: int,
    wenchang: int,
    wenqu: int,
) -> dict[str, int]:
    """返回 {杂曜名: 地支索引}（默认派 38 颗）。

    日系星输入 left/chang/qu 索引来自 stars.minor（§8.2）；
    天伤=仆役宫、天使=疾厄宫（默认派固定，§8.5 location.ts:756）。
    """
    hongluan = (3 - year_zhi) % 12  # 卯起子年逆数（location.ts:426）
    return {
        # 日系（§8.2）
        "三台": (zuofu + day_index) % 12,
        "八座": (youbi - day_index) % 12,
        "恩光": (wenchang + day_index - 1) % 12,
        "天贵": (wenqu + day_index - 1) % 12,
        # 时系（§8.3）
        "台辅": (6 + t_idx) % 12,
        "封诰": (2 + t_idx) % 12,
        # 月系（§8.4）
        "解神": JIESHEN_BY_MONTH[month_index],
        "天姚": (1 + month_index) % 12,
        "天刑": (9 + month_index) % 12,
        "阴煞": YINSHA_BY_MONTH[month_index % 6],
        "天月": TIANYUE_BY_MONTH[month_index],
        "天巫": TIANWU_BY_MONTH[month_index % 4],
        # 年系（§8.5）
        "红鸾": hongluan,
        "天喜": (hongluan + 6) % 12,
        "咸池": XIANCHI_BY_ZHI[year_zhi],
        "华盖": HUAGAI_BY_ZHI[year_zhi],
        "孤辰": GUCHEN_BY_ZHI[year_zhi],
        "寡宿": GUASU_BY_ZHI[year_zhi],
        "天才": (soul_branch + year_zhi) % 12,
        "天寿": (body_branch + year_zhi) % 12,
        "天厨": TIANCHU_BY_GAN[year_gan],
        "破碎": POSUI_BY_ZHI[year_zhi % 3],
        "蜚廉": FEILIAN_BY_ZHI[year_zhi],
        "龙池": (4 + year_zhi) % 12,
        "凤阁": (10 - year_zhi) % 12,
        "天哭": (6 - year_zhi) % 12,
        "天虚": (6 + year_zhi) % 12,
        "天官": TIANGUAN_BY_GAN[year_gan],
        "天福": TIANFU_BY_GAN[year_gan],
        "天德": (9 + year_zhi) % 12,
        "月德": (5 + year_zhi) % 12,
        "天空": (year_zhi + 1) % 12,
        "截路": JIELU_BY_GAN[year_gan % 5],
        "空亡": KONGWANG_BY_GAN[year_gan % 5],
        "旬空": xunkong_index(year_gan, year_zhi),
        "天伤": (soul_branch + 5) % 12,  # 仆役宫
        "天使": (soul_branch + 7) % 12,  # 疾厄宫
        "年解": NIANJIE_BY_ZHI[year_zhi],
    }


def _spread(seq: list[str], start: int, direction: int) -> list[str]:
    """从 start 地支起按 direction（+1 顺 / −1 逆）把 seq 铺到 12 宫。"""
    out = [""] * 12
    for i, name in enumerate(seq):
        out[(start + direction * i) % 12] = name
    return out


def is_forward(year_zhi: int, gender: str) -> bool:
    """阳男阴女顺行（§11：年支索引偶为阳，男阳女阴，阴阳一致则顺）。"""
    return (year_zhi % 2 == 0) == (gender == "男")


def changsheng12(class_number: int, year_zhi: int, gender: str) -> list[str]:
    """长生十二神（§11.1，decorativeStar.ts:31）：五行局起长生，阳男阴女顺行。"""
    direction = 1 if is_forward(year_zhi, gender) else -1
    return _spread(CHANGSHENG12, CHANGSHENG_START[class_number], direction)


def boshi12(lucun_branch: int, year_zhi: int, gender: str) -> list[str]:
    """博士十二神（§11.2，decorativeStar.ts:123）：禄存起博士，阳男阴女顺行。"""
    direction = 1 if is_forward(year_zhi, gender) else -1
    return _spread(BOSHI12, lucun_branch, direction)


def suiqian12(year_zhi: int) -> list[str]:
    """岁前十二神（§11.3，decorativeStar.ts:204）：生年支宫起岁建，恒顺行。"""
    return _spread(SUIQIAN12, year_zhi, 1)


def jiangqian12(year_zhi: int) -> list[str]:
    """将前十二神（§11.4，decorativeStar.ts:170）：将星位起，恒顺行。"""
    return _spread(JIANGQIAN12, JIANGXING_START[year_zhi], 1)

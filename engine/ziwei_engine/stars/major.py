"""14 主星定位：紫微系 + 天府系。

规则（三合派传统，对齐 iztro）：
- 紫微定位：生日 ÷ 局数。整除：商数从寅起顺数（寅=1）。
  不整除：补最小非负 k 使 (日+k) % 局 == 0，商 q=(日+k)/局 从寅顺数 q 宫；
  k 为奇则再逆退 k 宫，k 为偶则顺进 k 宫。
- 天府：与紫微以寅申轴对称：tianfu = (4 - ziwei) % 12
- 紫微系（自紫微起地支递减）：紫微0 天机-1 太阳-3 武曲-4 天同-5 廉贞-8
- 天府系（自天府起地支递增）：天府0 太阴+1 贪狼+2 巨门+3 天相+4 天梁+5 七杀+6 破军+10
"""

# 星名 → 相对本系主星的地支偏移
ZIWEI_SERIES: dict[str, int] = {
    "紫微": 0, "天机": -1, "太阳": -3, "武曲": -4, "天同": -5, "廉贞": -8,
}
TIANFU_SERIES: dict[str, int] = {
    "天府": 0, "太阴": 1, "贪狼": 2, "巨门": 3, "天相": 4, "天梁": 5,
    "七杀": 6, "破军": 10,
}

MAJOR_STARS: list[str] = list(ZIWEI_SERIES) + list(TIANFU_SERIES)


def ziwei_branch(lunar_day: int, class_number: int) -> int:
    """紫微星地支索引。"""
    remainder = lunar_day % class_number
    if remainder == 0:
        quotient = lunar_day // class_number
        return (2 + quotient - 1) % 12
    k = class_number - remainder
    quotient = (lunar_day + k) // class_number
    base = (2 + quotient - 1) % 12
    if k % 2 == 1:  # 补数奇：逆退 k 宫
        return (base - k) % 12
    return (base + k) % 12


def tianfu_branch(ziwei: int) -> int:
    return (4 - ziwei) % 12


def place_major_stars(lunar_day: int, class_number: int) -> dict[str, int]:
    """返回 {主星名: 地支索引}。"""
    zw = ziwei_branch(lunar_day, class_number)
    tf = tianfu_branch(zw)
    positions: dict[str, int] = {}
    for name, offset in ZIWEI_SERIES.items():
        positions[name] = (zw + offset) % 12
    for name, offset in TIANFU_SERIES.items():
        positions[name] = (tf + offset) % 12
    return positions

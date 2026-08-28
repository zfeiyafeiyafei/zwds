"""时间周期：大限、流年、小限。

规则（三合派传统，对齐 iztro horoscope 输出）：
- 大限：命宫起限，虚岁区间 = [局数 + 10k, 局数 + 10k + 9]。
  阳男阴女顺行（地支递增，即 命→父母→福德…），阴男阳女逆行（地支递减）。
- 流年：流年命宫 = 流年地支所在宫；流年四化 = 流年干四化。
- 小限：按生年支三合局起宫（寅午戌起辰，申子辰起戌，巳酉丑起未，亥卯未起丑），
  一岁一宫，男顺女逆（阳顺阴逆无关）。虚岁 a 的小限宫 = 起宫 + (a-1) × 方向。
- 虚岁 = 目标农历年 - 生年农历年 + 1。
"""

from __future__ import annotations

from dataclasses import dataclass

# 生年支三合局 → 小限起宫：寅午戌起辰，申子辰起戌，巳酉丑起未，亥卯未起丑
XIAOXIAN_START: dict[int, int] = {
    2: 4, 6: 4, 10: 4,    # 寅午戌 → 辰
    8: 10, 0: 10, 4: 10,  # 申子辰 → 戌
    5: 7, 9: 7, 1: 7,     # 巳酉丑 → 未
    11: 1, 3: 1, 7: 1,    # 亥卯未 → 丑
}


@dataclass(frozen=True)
class Decadal:
    """一步大限。"""

    index: int  # 第几步大限，0=命宫起
    palace_branch: int
    age_start: int  # 虚岁
    age_end: int


def is_yang_year(year_gan: int) -> bool:
    return year_gan % 2 == 0  # 甲丙戊庚壬为阳


def decadal_direction(year_gan: int, gender: str) -> int:
    """阳男阴女顺行(+1，地支递增)，阴男阳女逆行(-1)。"""
    yang = is_yang_year(year_gan)
    forward = (yang and gender == "男") or (not yang and gender == "女")
    return 1 if forward else -1


def decadal_at(soul_branch: int, class_number: int, direction: int, nominal_age: int) -> Decadal:
    """定位某虚岁所在大限。"""
    if nominal_age < class_number:
        raise ValueError(f"虚岁 {nominal_age} 未上运（起限 {class_number} 岁）")
    index = (nominal_age - class_number) // 10
    branch = (soul_branch + direction * index) % 12
    start = class_number + index * 10
    return Decadal(index=index, palace_branch=branch, age_start=start, age_end=start + 9)


def all_decadals(soul_branch: int, class_number: int, direction: int, count: int = 12) -> list[Decadal]:
    """完整大限表。"""
    return [
        Decadal(
            index=i,
            palace_branch=(soul_branch + direction * i) % 12,
            age_start=class_number + i * 10,
            age_end=class_number + i * 10 + 9,
        )
        for i in range(count)
    ]


def xiaoxian_branch(year_zhi: int, gender: str, nominal_age: int) -> int:
    """小限宫：生年支起宫，一岁一宫，男顺女逆。"""
    start = XIAOXIAN_START[year_zhi]
    direction = 1 if gender == "男" else -1
    return (start + direction * (nominal_age - 1)) % 12

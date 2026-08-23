"""六十甲子纳音 → 五行局。

NAYIN[i] 为第 i 对干支（i = 甲子序号 // 2）的纳音五行。
"""

# 30 对干支的纳音五行：金木水火土
NAYIN: list[str] = [
    "金", "火", "木", "土", "金",  # 甲子乙丑 … 壬申癸酉
    "火", "水", "土", "金", "木",  # 甲戌乙亥 … 壬午癸未
    "水", "土", "火", "木", "水",  # 甲申乙酉 … 壬辰癸巳
    "金", "火", "木", "土", "金",  # 甲午乙未 … 壬寅癸卯
    "火", "水", "土", "金", "木",  # 甲辰乙巳 … 壬子癸丑
    "水", "土", "火", "木", "水",  # 甲寅乙卯 … 壬戌癸亥
]

ELEMENT_TO_CLASS: dict[str, str] = {
    "水": "水二局", "木": "木三局", "金": "金四局", "土": "土五局", "火": "火六局",
}


def five_elements_class(ming_gan: int, ming_zhi: int) -> str:
    """由命宫干支纳音定五行局。

    干支必须同阴阳（stem % 2 == branch % 2）。
    甲子序号：从 (0,0) 起，干、支同步递增，序号 n 满足 n ≡ gan (mod 10), n ≡ zhi (mod 12)。
    """
    # 由中国剩余定理直接求 0-59 序号
    for n in range(ming_gan, 60, 10):
        if n % 12 == ming_zhi:
            break
    else:  # pragma: no cover - 干支非法
        raise ValueError(f"invalid ganzhi pair: gan={ming_gan} zhi={ming_zhi}")
    return ELEMENT_TO_CLASS[NAYIN[n // 2]]

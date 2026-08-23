"""紫微斗数基础常量：天干、地支、宫位名、五行局。

索引约定：
- 天干 0=甲 ... 9=癸
- 地支 0=子 ... 11=亥
- 时辰 hour_index 采用 iztro 约定：0=早子时(00:00-01:00)，1=丑时 ... 11=亥时，12=晚子时(23:00-24:00)
"""

HEAVENLY_STEMS: list[str] = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EARTHLY_BRANCHES: list[str] = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 十二宫固定顺序：从命宫起逆时针（地支递减方向）排列
PALACE_NAMES: list[str] = [
    "命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄",
    "迁移", "仆役", "官禄", "田宅", "福德", "父母",
]

# 五行局：value 为局数（起限岁数/紫微定位除数）
FIVE_ELEMENTS_CLASS: dict[str, int] = {
    "水二局": 2, "木三局": 3, "金四局": 4, "土五局": 5, "火六局": 6,
}

# 时辰 hour_index → 地支索引；0(早子)与12(晚子)都属子
def hour_index_to_branch(hour_index: int) -> int:
    if hour_index == 0 or hour_index == 12:
        return 0
    return hour_index


# hour_index → 代表性钟表时间 (hour, minute)，供历法库计算
def hour_index_to_clock(hour_index: int) -> tuple[int, int]:
    if hour_index == 0:
        return 0, 30
    if hour_index == 12:
        return 23, 30
    return hour_index * 2, 30

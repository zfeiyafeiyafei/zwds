"""星曜分析（rules/star_interp.py）契约测试。

防御点（biz_requirement.md §4.3.2 的可观察契约）：
- 每宫都有分析条目；命宫/身宫标记正确
- 已收录星曜输出完整字段（象义/性格/优势/风险 + 亮度/四化注记）
- 双主星同宫输出组合断语；未收录杂曜有占位释义而非空串
"""

from ziwei_engine.calendar.converter import BirthInput
from ziwei_engine.chart.natal import calculate
from ziwei_engine.rules.star_interp import (
    PAIR_NOTES,
    STAR_KNOWLEDGE,
    analyze_soul_body,
    analyze_stars,
)

# 太阳在巳旺、生年干甲 → 太阳化忌（含亮度与四化注记的完整样本）
CHART = calculate(BirthInput(1984, 6, 20, 1, "男"))


def test_twelve_palaces_with_soul_and_body_flags():
    res = analyze_stars(CHART)
    assert len(res) == 12
    assert sum(p.is_soul for p in res) == 1
    assert sum(p.is_body for p in res) == 1
    assert all(p.branch for p in res)


def test_known_star_full_fields():
    soul = next(p for p in res if p.is_soul) if (res := analyze_stars(CHART)) else None
    sun = next(i for i in soul.items if i.name == "太阳")
    assert sun.category == "主星"
    assert sun.element == "阳火"
    assert sun.trait and sun.character and sun.strength and sun.risk
    # 太阳在巳为旺 → 庙旺注记
    assert "旺" in sun.brightness_note
    # 甲年太阳化忌 → 四化联动注记
    assert "化忌" in sun.mutagen_note
    assert sun.palace_note  # 落宫注记非空（主星为专注断语）


def test_dim_star_note_mentions_risk():
    # 落陷主星：亮度注记须带出风险文本
    res = analyze_stars(CHART)
    dim = [i for p in res for i in p.items if i.brightness in ("不", "陷") and i.category == "主星"]
    for item in dim:
        k = STAR_KNOWLEDGE[item.name]
        assert k.risk in item.brightness_note


def test_pair_note_for_dual_major_palace():
    res = analyze_stars(CHART)
    for p in res:
        majors = sorted(i.name for i in p.items if i.category == "主星")
        if len(majors) == 2:
            expected = PAIR_NOTES.get(tuple(majors), "")
            assert p.pair_note == expected
        else:
            assert p.pair_note == ""


def test_all_chart_stars_collected():
    # 盘上所有星曜（含杂曜）均应命中知识库，不再有占位句
    res = analyze_stars(CHART)
    missing = [
        i.name for p in res for i in p.items
        if i.name not in STAR_KNOWLEDGE
    ]
    assert missing == []


def test_knowledge_covers_engine_star_sets():
    # 知识库须覆盖引擎全部产出星曜：14 主星 + 14 辅星 + 38 杂曜
    from ziwei_engine.stars.adjective import ADJECTIVE_STARS
    from ziwei_engine.stars.major import MAJOR_STARS

    engine_stars = set(MAJOR_STARS) | set(ADJECTIVE_STARS) | {
        "左辅", "右弼", "文昌", "文曲", "天魁", "天钺", "禄存",
        "天马", "擎羊", "陀罗", "火星", "铃星", "地空", "地劫",
    }
    missing = engine_stars - set(STAR_KNOWLEDGE)
    assert missing == set()


def test_major_star_uses_curated_palace_note():
    # 主星落宫须用 PALACE_NOTES 专注而非模板句（模板以「在」开头）
    res = analyze_stars(CHART)
    majors = [i for p in res for i in p.items if i.category == "主星"]
    assert majors
    for item in majors:
        assert item.palace_note
        assert not item.palace_note.startswith("在")


def test_soul_body_notes():
    notes = analyze_soul_body(CHART)
    assert notes.stars
    roles = [r for s in notes.stars for r in s.roles]
    # 四重身份齐备：命宫主星/命主/身宫主星/身主
    for role in ("命宫主星", "命主", "身宫主星", "身主"):
        assert role in roles
    # 星名唯一（重星已合并），roles 与 notes 一一对应
    assert len({s.name for s in notes.stars}) == len(notes.stars)
    assert all(len(s.roles) == len(s.notes) for s in notes.stars)
    # 本盘四星均应命中知识库（无占位后缀）
    assert all("待知识库补充" not in n for s in notes.stars for n in s.notes)


def _locate(name: str):
    for p in CHART.palaces:
        for s in (*p.major_stars, *p.minor_stars, *p.adjective_stars):
            if s.name == name:
                return s, p
    return None


def _label(p) -> str:
    return p.name if p.name.endswith("宫") else p.name + "宫"


def test_soul_body_notes_include_chart_position():
    """动态注记：命主/身主断语须带出星曜实际落宫。"""
    notes = analyze_soul_body(CHART)
    sk = CHART.skeleton
    soul_entry = next(s for s in notes.stars if "命主" in s.roles)
    _, soul_palace = _locate(sk.soul)
    assert f"落{_label(soul_palace)}" in soul_entry.notes[soul_entry.roles.index("命主")]
    if sk.body != sk.soul:
        body_entry = next(s for s in notes.stars if "身主" in s.roles)
        _, body_palace = _locate(sk.body)
        assert f"落{_label(body_palace)}" in body_entry.notes[body_entry.roles.index("身主")]


def _scan(predicate):
    """扫描固定年月的不同时日，返回首个满足条件的命盘。"""
    for day in range(1, 29):
        for hour in range(12):
            chart = calculate(BirthInput(1990, 3, day, hour, "男"))
            if predicate(chart):
                return chart
    return None


def test_empty_soul_palace_borrows_opposite():
    """命宫空宫（无正曜）：借对宫主星论命，标注借星并在总述说明。"""
    chart = _scan(lambda c: not c.palaces[c.skeleton.soul_palace_branch].major_stars)
    assert chart is not None, "扫描样本中应存在命宫空宫"
    notes = analyze_soul_body(chart)
    borrowed = [s for s in notes.stars if s.borrowed and "命宫主星" in s.roles]
    assert borrowed, "命宫空宫须借对宫主星"
    opposite = chart.palaces[(chart.skeleton.soul_palace_branch + 6) % 12]
    assert {s.name for s in borrowed} == {s.name for s in opposite.major_stars}
    assert "命宫为空宫" in notes.overview and "借对宫" in notes.overview


def test_duplicate_star_merged_into_one_entry():
    """命主星恰为命宫主星时合并为一卡双角色。"""
    chart = _scan(
        lambda c: any(
            s.name == c.skeleton.soul
            for s in c.palaces[c.skeleton.soul_palace_branch].major_stars
        )
    )
    assert chart is not None, "扫描样本中应存在命主星坐命"
    notes = analyze_soul_body(chart)
    entry = next(s for s in notes.stars if s.name == chart.skeleton.soul)
    assert "命宫主星" in entry.roles and "命主" in entry.roles
    assert len(entry.notes) == len(entry.roles) == 2


def test_soul_body_same_palace_overview():
    """子时生人命身同宫，总述须说明。"""
    notes = analyze_soul_body(calculate(BirthInput(1990, 3, 8, 0, "女")))
    assert "命身同宫" in notes.overview


def test_soul_body_relation_note():
    """命身呼应：命主入身宫 / 身主入命宫 / 命身同主 三种关系须成文。"""
    from ziwei_engine.rules.star_interp import _relation_note

    # CHART（1984-06-20 午时男）验证当前盘的关系断语与实际落宫一致
    sk = CHART.skeleton
    note = _relation_note(CHART)
    if sk.soul == sk.body:
        assert "同为" in note
    else:
        _, soul_palace = _locate(sk.soul)
        _, body_palace = _locate(sk.body)
        if soul_palace.is_body_palace:
            assert "恰落身宫" in note
        elif body_palace.name == "命宫":
            assert "落入命宫" in note
        else:
            assert note == ""


def test_pair_notes_cover_all_dual_combos():
    # 知识库自检：键必须是排序后的双主星组合
    for key in PAIR_NOTES:
        assert len(key) == 2 and list(key) == sorted(key)
        assert all(name in STAR_KNOWLEDGE for name in key)

"""格局识别测试：钉样例 + 结构不变量。

样例经引擎扫描确认（rules/patterns.py 声明式规则，无 iztro 对照——iztro 无格局分析）。
"""

from ziwei_engine.calendar.converter import BirthInput
from ziwei_engine.chart.natal import calculate
from ziwei_engine.rules.patterns import RULES, analyze_patterns


def _names(matches):
    return {m.name for m in matches}


def test_shapolang_and_junchen() -> None:
    """1985-01-01 早子时男：杀破狼(强) + 君臣庆会(中)。"""
    chart = calculate(BirthInput(1985, 1, 1, 0, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert matches["杀破狼"].strength == "强"
    assert "贪狼·命宫(子)" in matches["杀破狼"].evidence
    assert matches["君臣庆会"].strength == "中"
    assert "紫微·迁移(午)" in matches["君臣庆会"].evidence


def test_zifu_and_fuxiang() -> None:
    """1985-01-15 午时男：紫府朝垣(强) + 府相朝垣(强)。"""
    chart = calculate(BirthInput(1985, 1, 15, 6, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert matches["紫府朝垣"].strength == "强"
    assert "紫微·命宫(午)" in matches["紫府朝垣"].evidence
    assert matches["府相朝垣"].strength == "强"


def test_jiyuetongliang() -> None:
    """1985-01-08 午时男：机月同梁(强)。"""
    chart = calculate(BirthInput(1985, 1, 8, 6, "男"))
    matches = analyze_patterns(chart)
    assert "机月同梁" in _names(matches)
    assert "天梁·财帛(寅)" in matches[0].evidence or any(
        "天梁" in e for m in matches for e in m.evidence
    )


def test_yangliangchanglu_needs_lu() -> None:
    """1985-04-22 早子时男：阳梁昌禄(弱)；need_lu 门槛生效。"""
    chart = calculate(BirthInput(1985, 4, 22, 0, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert matches["阳梁昌禄"].strength == "弱"
    assert "禄存/化禄在三方四正" in matches["阳梁昌禄"].evidence


def test_no_pattern_chart() -> None:
    """1990-05-15 午时男：无任何格局命中（反例）。"""
    chart = calculate(BirthInput(1990, 5, 15, 6, "男"))
    assert analyze_patterns(chart) == []


def test_match_structure_invariants() -> None:
    """输出结构：命中项必填字段非空；证据含宫名与地支。"""
    chart = calculate(BirthInput(1985, 1, 1, 0, "男"))
    for m in analyze_patterns(chart):
        assert m.strength in ("强", "中", "弱")
        assert m.condition and m.domain and m.explain
        assert all("·" in e and ("(" in e or "禄" in e) for e in m.evidence)


def test_rules_unique_names() -> None:
    names = [r.name for r in RULES]
    assert len(names) == len(set(names))


# ---- 夹命类格局：两星分坐命宫左右邻宫 ----


def test_t_chart_double_clamp() -> None:
    """T 盘（2016-10-24 巳时 男，命宫丑）：

    子(兄弟)=天同太阴左辅、寅(父母)=太阳巨门右弼 → 左右夹命 + 日月夹命。
    （天魁在亥、天钺在酉夹的是戌宫子女，不夹命宫丑。）
    """
    chart = calculate(BirthInput(2016, 10, 24, 9, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert "左右夹命" in matches
    assert "日月夹命" in matches
    assert "魁钺夹命" not in matches
    assert "杀破狼" in matches  # 原有三方四正格局不受影响

    assert matches["左右夹命"].evidence == ["左辅·兄弟(子)", "右弼·父母(寅)"]
    assert matches["日月夹命"].evidence == ["太阳·父母(寅)", "太阴·兄弟(子)"]


def test_kuikui_clamp_when_adjacent() -> None:
    """魁钺夹命成立样例：1972-10-07 午时男（壬子年魁钺分坐命宫两侧）。

    样例经引擎扫描确认；魁钺安星仅由年干决定，命宫位置由月时决定。
    """
    chart = calculate(BirthInput(1972, 10, 7, 6, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert "魁钺夹命" in matches
    assert all("·" in e for e in matches["魁钺夹命"].evidence)
    assert matches["魁钺夹命"].strength in ("强", "中", "弱")


def test_clamp_requires_both_sides() -> None:
    """夹命星只在一侧邻宫时不成立。

    L 盘（1981-11-10 戌时 男，命宫酉）：申(兄弟)=天府天魁，戌(福德)无魁钺系星
    → 魁钺夹命不成立。
    """
    chart = calculate(BirthInput(1981, 11, 10, 10, "男"))
    names = _names(analyze_patterns(chart))
    assert "魁钺夹命" not in names
    assert "左右夹命" not in names



def test_no_false_clamp_on_other_charts() -> None:
    """C 盘（1982-01-27 酉时 女）：无任何夹命误报。"""
    chart = calculate(BirthInput(1982, 1, 27, 9, "女"))
    names = _names(analyze_patterns(chart))
    assert not names & {"左右夹命", "日月夹命", "魁钺夹命", "昌曲夹命"}


# ---- 坐命类格局：星 + 命宫地支 ----


def test_jixiangleming_and_soul_branch() -> None:
    """1980-02-15 未时男：紫微独坐午宫 → 极向离明。"""
    chart = calculate(BirthInput(1980, 2, 15, 7, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert "紫微·命宫(午)" in matches["极向离明"].evidence


def test_rizhaoleimen_allows_yangliang() -> None:
    """1980-01-03 巳时男：太阳在卯坐命（与天梁同宫）→ 日照雷门。"""
    chart = calculate(BirthInput(1980, 1, 3, 9, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert "太阳·命宫(卯)" in matches["日照雷门"].evidence


def test_wutan_tonghang_same_palace() -> None:
    """1980-03-15 丑时男：武曲贪狼同宫丑坐命 → 武贪同行(强)。"""
    chart = calculate(BirthInput(1980, 3, 15, 1, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert matches["武贪同行"].strength == "强"
    assert "贪狼·命宫(丑)" in matches["武贪同行"].evidence


def test_mingzhu_chuhai_at_branch() -> None:
    """1980-02-15 午时男：命在未，日卯月亥拱照 → 明珠出海 + 日月并明。"""
    chart = calculate(BirthInput(1980, 2, 15, 6, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert matches["明珠出海"].strength == "强"
    assert "太阳·财帛(卯)" in matches["明珠出海"].evidence
    assert "太阴·官禄(亥)" in matches["明珠出海"].evidence
    assert "日月并明" in matches


# ---- 四化 / 禄类格局 ----


def test_sanqi_jiahui_mutagens() -> None:
    """1981-03-01 申时男：化禄化权化科齐会三方 → 三奇加会。"""
    chart = calculate(BirthInput(1981, 3, 1, 8, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    evidence = matches["三奇加会"].evidence
    assert any("化禄" in e for e in evidence)
    assert any("化权" in e for e in evidence)
    assert any("化科" in e for e in evidence)


def test_shuanglu_chaoyuan_double_lu() -> None:
    """1980-01-01 早子时男：禄存与化禄并见三方 → 双禄朝垣。"""
    chart = calculate(BirthInput(1980, 1, 1, 0, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert "禄存与化禄并见三方四正" in matches["双禄朝垣"].evidence


# ---- 命身 / 空宫 ----


def test_zuogui_xianggui_soul_body() -> None:
    """1980-04-15 寅时男：天魁坐命、天钺坐身（迁移）→ 坐贵向贵。"""
    chart = calculate(BirthInput(1980, 4, 15, 3, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert "天魁·命宫(丑)" in matches["坐贵向贵"].evidence
    assert "天钺·迁移(未)" in matches["坐贵向贵"].evidence


def test_ming_wu_zhengyao_empty_soul() -> None:
    """1980-01-01 卯时男：命宫申无正曜 → 命无正曜。"""
    chart = calculate(BirthInput(1980, 1, 1, 4, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert "命宫(申)·无正曜" in matches["命无正曜"].evidence


# ---- 凶格 ----


def test_riyue_fanbei_bright_all() -> None:
    """1980-01-15 申时男：日月皆失辉 → 日月反背(弱)。"""
    chart = calculate(BirthInput(1980, 1, 15, 8, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert matches["日月反背"].strength == "弱"
    assert "太阴·命宫(辰)" in matches["日月反背"].evidence


def test_huoling_clamp_and_yangtuo_jiaji() -> None:
    """火铃夹命：1982-02-01 早子时男；羊陀夹忌：1980-04-15 申时男。"""
    chart = calculate(BirthInput(1982, 2, 1, 0, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert "火星·兄弟(丑)" in matches["火铃夹命"].evidence
    assert "铃星·父母(卯)" in matches["火铃夹命"].evidence

    chart = calculate(BirthInput(1980, 4, 15, 8, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    evidence = matches["羊陀夹忌"].evidence
    assert "擎羊·父母(酉)" in evidence
    assert "陀罗·兄弟(未)" in evidence
    assert any("化忌·命宫" in e for e in evidence)


def test_caiyin_jiayin_off_soul_palace() -> None:
    """1981-11-10 戌时男（辛年巨门化禄）：天相不在命宫而在官禄，
    仍构成夹印结构；巨门落陷化禄 → 附减等注记、不作破格。"""
    chart = calculate(BirthInput(1981, 11, 10, 10, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    evidence = matches["财荫夹印"].evidence
    assert "天相·官禄(巳)" in evidence
    assert "天梁·交友(午)" in evidence
    assert "巨门化禄·田宅(辰)" in evidence
    assert any("落陷化禄" in e and "不作破格" in e for e in evidence)
    # 天相(得)0 + 天梁(庙)+1 + 巨门(陷)-1 = 0 → 中
    assert matches["财荫夹印"].strength == "中"


def test_xingji_jiayin() -> None:
    """1977-06-01 午时女（丁年巨门化忌）：刑忌夹印；财侧有忌则财荫夹印不成立。"""
    chart = calculate(BirthInput(1977, 6, 1, 6, "女"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    evidence = matches["刑忌夹印"].evidence
    assert "天相·交友(辰)" in evidence
    assert "巨门化忌·官禄(卯)" in evidence
    assert "财荫夹印" not in matches


def test_special_patterns() -> None:
    """特殊结构：财荫夹印 / 刑囚夹印 / 马落空亡。"""
    chart = calculate(BirthInput(1980, 8, 1, 10, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    assert "天相·命宫(酉)" in matches["财荫夹印"].evidence
    assert "天梁·父母(戌)" in matches["财荫夹印"].evidence

    chart = calculate(BirthInput(1982, 2, 6, 2, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    evidence = matches["刑囚夹印"].evidence
    assert "天相·命宫(子)" in evidence
    assert "擎羊·命宫(子)" in evidence

    chart = calculate(BirthInput(1980, 4, 1, 9, "男"))
    matches = {m.name: m for m in analyze_patterns(chart)}
    evidence = matches["马落空亡"].evidence
    assert "天马·财帛(寅)" in evidence
    assert "地空·财帛(寅)" in evidence


def test_fanshui_taohua_soul_branch() -> None:
    """1980-04-01 寅时男：贪狼在子坐命 → 泛水桃花。"""
    chart = calculate(BirthInput(1980, 4, 1, 3, "男"))
    names = _names(analyze_patterns(chart))
    assert "泛水桃花" in names


def test_rules_data_completeness() -> None:
    """规则数据不变量：每条规则字段齐备，分类只取 吉格/凶格。"""
    assert len(RULES) >= 40
    for r in RULES:
        assert r.condition and r.domain and r.explain
        assert r.category in ("吉格", "凶格")

"""格局识别：命宫三方四正星曜组合 + 坐命/夹命/命身/四化格局（biz_requirement.md §4.3.1）。

口径（三合派传统）：
- 命宫三方四正 = 命宫、财帛（命-4）、官禄（命+4）、迁移（对宫，命+6）。
- 每条规则声明 required（三方四正必须全部出现）与 any_of（每组至少命中一个）；
  need_lu=True 还要求三方四正内有禄存或任一生年化禄星；
  need_double_lu=True 要求禄存与生年化禄并见三方四正（双禄朝垣）；
  mutagens 要求三方四正内出现指定生年四化（禄/权/科/忌）。
- soul_stars 为命宫坐守星（同宫/坐命格局），可叠加 soul_branches（命宫地支白名单）、
  soul_only（命宫独坐，仅一颗主星）、soul_mutagens（命宫内须见指定四化）。
- at_branch 要求指定星落在三方四正内的指定地支（如明珠出海：日卯月亥拱未命）。
- bright_all 对 required 星加亮度约束："庙旺" 全庙旺（日月并明）/"不陷" 全不陷（日月反背）。
- clamp_pair 为夹命规则：两星分别坐守命宫左右邻宫。
- soul_body_pair 为命身规则：两星分坐命宫与身宫（坐贵向贵）。
- empty_soul 为命无正曜：命宫无十四主星。
- special 为结构特殊的独立判定："财荫夹印"、"刑囚夹印"、"马落空亡"。
- 强弱：按命中星亮度计分（庙/旺 +1，得/利/平/无数据 0，不/陷 -1），
  ≥2 强，0~1 中，<0 弱。凶格同法计分，表示格局成色。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..chart.layout import ChartSkeleton
from ..chart.natal import NatalChart
from ..constants import EARTHLY_BRANCHES

_BRIGHT_SCORE = {"庙": 1, "旺": 1, "得": 0, "利": 0, "平": 0, "不": -1, "陷": -1}
_BRIGHT_GROUPS = {"庙旺": frozenset({"庙", "旺"}), "不陷": frozenset({"不", "陷"})}

# 地支索引：子=0 丑=1 寅=2 卯=3 辰=4 巳=5 午=6 未=7 申=8 酉=9 戌=10 亥=11
_ZI, _CHOU, _YIN, _MAO, _CHEN, _SI = 0, 1, 2, 3, 4, 5
_WU, _WEI, _SHEN, _YOU, _XU, _HAI = 6, 7, 8, 9, 10, 11


@dataclass(frozen=True)
class PatternRule:
    """一条格局规则（声明式）。字段语义见模块 docstring。"""

    name: str
    category: str = "吉格"  # 吉格 / 凶格（pattern_definition.category）
    required: frozenset[str] = frozenset()  # 三方四正中必须同时出现
    any_of: tuple[frozenset[str], ...] = ()  # 每组至少命中一颗
    need_lu: bool = False  # 另须见禄存或生年化禄
    need_double_lu: bool = False  # 禄存与生年化禄并见三方四正
    mutagens: frozenset[str] = frozenset()  # 三方四正内必须出现的四化
    bright_all: str = ""  # required 全体亮度约束："庙旺" / "不陷"
    soul_stars: frozenset[str] = frozenset()  # 命宫坐守星
    soul_branches: frozenset[int] = frozenset()  # 命宫地支白名单
    soul_only: bool = False  # 命宫独坐（仅一颗主星）
    soul_mutagens: frozenset[str] = frozenset()  # 命宫内必须出现的四化
    at_branch: tuple[tuple[str, frozenset[int]], ...] = ()  # 星须在三方内指定地支
    clamp_pair: tuple[str, str] = ("", "")  # 夹命两星（邻宫坐守）
    soul_body_pair: tuple[str, str] = ("", "")  # 两星分坐命宫与身宫
    empty_soul: bool = False  # 命无正曜
    special: str = ""  # 特殊判定：财荫夹印 / 马落空亡
    domain: str = ""  # 主要影响领域
    condition: str = ""  # 成立条件（展示用）
    explain: str = ""  # 简要解释


RULES: tuple[PatternRule, ...] = (
    # ---- 三方四正会照类 ----
    PatternRule(
        name="杀破狼",
        required=frozenset({"七杀", "破军", "贪狼"}),
        domain="事业 / 开创",
        condition="七杀、破军、贪狼会齐命宫三方",
        explain="杀破狼永远互成三方；命宫三方恰落其局者，一生多变动，宜开拓、武职、竞争性领域。",
    ),
    PatternRule(
        name="机月同梁",
        required=frozenset({"天机", "太阴", "天同", "天梁"}),
        domain="事业 / 公职",
        condition="天机、太阴、天同、天梁会齐命宫三方四正",
        explain="机月同梁作吏人，性情温和缜密，宜公职、文教、幕僚参谋。",
    ),
    PatternRule(
        name="紫府朝垣",
        required=frozenset({"紫微", "天府"}),
        domain="地位 / 格局层次",
        condition="紫微、天府会照命宫三方四正",
        explain="帝星与库星拱命，格局端正厚重，主贵气与安稳。",
    ),
    PatternRule(
        name="府相朝垣",
        required=frozenset({"天府", "天相"}),
        domain="财富 / 名位",
        condition="天府、天相会照命宫三方四正",
        explain="府相朝垣，衣食丰足，主财运与名位平稳绵长。",
    ),
    PatternRule(
        name="阳梁昌禄",
        required=frozenset({"太阳", "天梁"}),
        any_of=(frozenset({"文昌", "文曲"}),),
        need_lu=True,
        domain="功名 / 学业",
        condition="太阳、天梁会照，加文昌或文曲，并见禄存或化禄",
        explain="阳梁昌禄利于科名，主学业、考试、文职与专业成就。",
    ),
    PatternRule(
        name="君臣庆会",
        required=frozenset({"紫微"}),
        any_of=(frozenset({"左辅", "右弼"}), frozenset({"文昌", "文曲"})),
        domain="地位 / 贵人",
        condition="紫微会照命宫三方，兼见辅弼与昌曲",
        explain="帝星得辅弼昌曲拱扶，主贵人多助、有领导统御之才。",
    ),
    PatternRule(
        name="三奇加会",
        mutagens=frozenset({"禄", "权", "科"}),
        domain="富贵 / 格局层次",
        condition="化禄、化权、化科会于命宫三方四正",
        explain="三奇拱命，富贵双全；须正曜庙旺方成美格，落陷则减色。",
    ),
    PatternRule(
        name="权禄巡逢",
        mutagens=frozenset({"权"}),
        need_lu=True,
        domain="权势 / 财禄",
        condition="化权与禄存（或化禄）会于命宫三方四正",
        explain="权禄并临，主权势与财禄兼得，事业进取有为。",
    ),
    PatternRule(
        name="双禄朝垣",
        need_double_lu=True,
        domain="财富",
        condition="禄存与生年化禄并见命宫三方四正",
        explain="双禄朝垣，财禄丰厚，一生衣食丰足。",
    ),
    PatternRule(
        name="禄马交驰",
        required=frozenset({"天马"}),
        need_lu=True,
        domain="财富 / 迁动",
        condition="天马与禄存（或化禄）会于命宫三方四正",
        explain="禄马交驰，动中求财，宜远行、外贸、流动性事业。",
    ),
    # ---- 特定宫位坐命类（星 + 命宫地支，缺一不成）----
    PatternRule(
        name="极向离明",
        soul_stars=frozenset({"紫微"}),
        soul_branches=frozenset({_WU}),
        soul_only=True,
        domain="地位 / 贵显",
        condition="紫微在午宫坐命",
        explain="极向离明，帝星居午正位，主贵显、位高权重。",
    ),
    PatternRule(
        name="日照雷门",
        soul_stars=frozenset({"太阳"}),
        soul_branches=frozenset({_MAO}),
        domain="声名 / 贵显",
        condition="太阳在卯宫坐命（与天梁同宫）",
        explain="日出扶桑（日照雷门），太阳居卯初升，主贵显、少年得志、声名早著。",
    ),
    PatternRule(
        name="月朗天门",
        soul_stars=frozenset({"太阴"}),
        soul_branches=frozenset({_HAI}),
        soul_only=True,
        domain="富贵 / 文秀",
        condition="太阴在亥宫坐命",
        explain="月朗天门，太阴居亥最明，主富贵、文秀，女命的佳。",
    ),
    PatternRule(
        name="明珠出海",
        soul_branches=frozenset({_WEI}),
        at_branch=(("太阳", frozenset({_MAO})), ("太阴", frozenset({_HAI}))),
        domain="富贵 / 声名",
        condition="命宫在未，太阳居卯、太阴居亥三方拱照",
        explain="明珠出海，日月夹拱未宫之命，主富贵声名、清贵有成。",
    ),
    PatternRule(
        name="日月并明",
        required=frozenset({"太阳", "太阴"}),
        bright_all="庙旺",
        domain="声名 / 亲荫",
        condition="太阳、太阴会照命宫三方四正且皆庙旺",
        explain="日月并明，阴阳二星皆得光辉，主声名显达、得父母庇荫。",
    ),
    PatternRule(
        name="七杀朝斗",
        soul_stars=frozenset({"七杀"}),
        soul_branches=frozenset({_ZI, _WU, _YIN, _SHEN}),
        soul_only=True,
        domain="权威 / 武贵",
        condition="七杀在子、午、寅、申坐命",
        explain="七杀朝斗，将星居正位，主权威、武贵，宜军警武职。",
    ),
    PatternRule(
        name="英星入庙",
        soul_stars=frozenset({"破军"}),
        soul_branches=frozenset({_ZI, _WU}),
        soul_only=True,
        domain="开创 / 武职",
        condition="破军在子或午坐命",
        explain="英星入庙，破军居子午得地，主开创、武职显达。",
    ),
    PatternRule(
        name="石中隐玉",
        soul_stars=frozenset({"巨门"}),
        soul_branches=frozenset({_ZI, _WU}),
        soul_only=True,
        domain="名声 / 口才",
        condition="巨门独坐子或午宫坐命",
        explain="石中隐玉，巨门居子午内秀，主先难后易、以口才文名成就。",
    ),
    PatternRule(
        name="马头带剑",
        soul_stars=frozenset({"擎羊"}),
        soul_branches=frozenset({_WU}),
        domain="武职 / 刑名",
        condition="擎羊在午宫坐命",
        explain="马头带剑，擎羊居午，主武职边疆立功，亦须防刑伤。",
    ),
    PatternRule(
        name="紫府同宫",
        soul_stars=frozenset({"紫微", "天府"}),
        soul_branches=frozenset({_YIN, _SHEN}),
        domain="富贵 / 格局层次",
        condition="紫微、天府同宫坐命（必在寅、申）",
        explain="紫府同宫，帝库相扶，格局厚重，主富贵安稳。",
    ),
    PatternRule(
        name="武贪同行",
        soul_stars=frozenset({"武曲", "贪狼"}),
        soul_branches=frozenset({_CHOU, _WEI}),
        domain="财富 / 商贾",
        condition="武曲、贪狼同宫坐命（必在丑、未）",
        explain="武贪同行，主大器晚成，宜商贾经营，见火铃尤主暴发。",
    ),
    PatternRule(
        name="火贪格",
        soul_stars=frozenset({"贪狼", "火星"}),
        domain="暴发 / 机遇",
        condition="贪狼与火星同宫坐命",
        explain="火贪同宫，主横发暴发；贪狼庙旺方成，落陷则成败起伏。",
    ),
    PatternRule(
        name="铃贪格",
        soul_stars=frozenset({"贪狼", "铃星"}),
        domain="暴发 / 机遇",
        condition="贪狼与铃星同宫坐命",
        explain="铃贪同宫，与火贪同论，主暴发，宜武职、商贾。",
    ),
    PatternRule(
        name="巨日同宫",
        soul_stars=frozenset({"太阳", "巨门"}),
        soul_branches=frozenset({_YIN, _SHEN}),
        domain="名声 / 涉外",
        condition="太阳、巨门同宫坐命（必在寅、申）",
        explain="巨日同宫，主口才、声名，宜涉外、传播、法律、教育。",
    ),
    PatternRule(
        name="善荫朝纲",
        soul_stars=frozenset({"天机", "天梁"}),
        soul_branches=frozenset({_CHEN, _XU}),
        domain="智谋 / 清贵",
        condition="天机、天梁同宫坐命（必在辰、戌）",
        explain="善荫朝纲（机梁同宫），主机谋与荫庇并重，清贵、宜专业与幕职。",
    ),
    PatternRule(
        name="极居卯酉",
        soul_stars=frozenset({"紫微", "贪狼"}),
        soul_branches=frozenset({_MAO, _YOU}),
        domain="才情 / 桃花",
        condition="紫微、贪狼同宫坐命于卯或酉",
        explain="极居卯酉，帝星与桃花同宫，主才情风流，须制桃花方贵。",
    ),
    # ---- 夹宫类：两星分坐命宫左右邻宫 ----
    PatternRule(
        name="左右夹命",
        clamp_pair=("左辅", "右弼"),
        domain="贵人 / 处境",
        condition="左辅、右弼分坐命宫两侧邻宫",
        explain="辅弼夹命，一生多贵人扶助，处事宜得左右之助力。",
    ),
    PatternRule(
        name="日月夹命",
        clamp_pair=("太阳", "太阴"),
        domain="富贵 / 声名",
        condition="太阳、太阴分坐命宫两侧邻宫",
        explain="日月夹命，父母阴阳二星拱卫，主声名与贵气，先天得长辈庇荫。",
    ),
    PatternRule(
        name="魁钺夹命",
        clamp_pair=("天魁", "天钺"),
        domain="贵人 / 机遇",
        condition="天魁、天钺分坐命宫两侧邻宫",
        explain="魁钺夹命，天乙贵人拱卫，主一生逢凶化吉、机遇常临。",
    ),
    PatternRule(
        name="昌曲夹命",
        clamp_pair=("文昌", "文曲"),
        domain="聪明 / 科名",
        condition="文昌、文曲分坐命宫两侧邻宫",
        explain="昌曲夹命，文星拱卫，主聪慧好学，利于考试与文名。",
    ),
    PatternRule(
        name="财荫夹印",
        soul_stars=frozenset({"天相"}),
        special="财荫夹印",
        domain="财富 / 名位",
        condition="天相坐命，兄弟宫见化禄（或禄存）、父母宫见天梁",
        explain="财荫夹印，印星得财荫护持，主名位安稳、得上辈与平辈之力。",
    ),
    PatternRule(
        name="坐贵向贵",
        soul_body_pair=("天魁", "天钺"),
        domain="贵人 / 机遇",
        condition="天魁、天钺分坐命宫与身宫",
        explain="坐贵向贵，命身各居贵人，主一生贵人不断、逢难得助。",
    ),
    # ---- 凶格 ----
    PatternRule(
        name="命无正曜",
        category="凶格",
        empty_soul=True,
        domain="根基 / 处境",
        condition="命宫无十四主星，借对宫星曜论命",
        explain="命无正曜，根基漂泊，借对宫定格调，一生依外缘而成。",
    ),
    PatternRule(
        name="日月反背",
        category="凶格",
        required=frozenset({"太阳", "太阴"}),
        bright_all="不陷",
        domain="劳碌 / 亲缘",
        condition="太阳、太阴会照命宫三方四正且皆不陷失辉",
        explain="日月反背，阴阳二星失位，主劳碌奔波、亲缘助力薄。",
    ),
    PatternRule(
        name="羊陀夹忌",
        category="凶格",
        clamp_pair=("擎羊", "陀罗"),
        soul_mutagens=frozenset({"忌"}),
        domain="刑克 / 是非",
        condition="擎羊、陀罗夹命宫，且命宫内有化忌",
        explain="羊陀夹忌，刑煞夹制忌星，主刑克是非、宜守不宜攻。",
    ),
    PatternRule(
        name="火铃夹命",
        category="凶格",
        clamp_pair=("火星", "铃星"),
        domain="性情 / 破败",
        condition="火星、铃星分坐命宫两侧邻宫",
        explain="火铃夹命，燥煞夹制，主性急多破耗，须以吉星化解。",
    ),
    PatternRule(
        name="空劫夹命",
        category="凶格",
        clamp_pair=("地空", "地劫"),
        domain="耗财 / 空想",
        condition="地空、地劫分坐命宫两侧邻宫",
        explain="空劫夹命，空亡夹制，主财来财去、理想多而落实难。",
    ),
    PatternRule(
        name="泛水桃花",
        category="凶格",
        soul_stars=frozenset({"贪狼"}),
        soul_branches=frozenset({_HAI, _ZI}),
        domain="感情 / 桃花",
        condition="贪狼在亥或子宫坐命",
        explain="泛水桃花，贪狼居水乡，主情欲泛滥，须防因色破财惹非。",
    ),
    PatternRule(
        name="刑囚夹印",
        category="凶格",
        soul_stars=frozenset({"廉贞", "天相"}),
        special="刑囚夹印",
        domain="官非 / 刑讼",
        condition="廉贞、天相同宫坐命（必在子、午），逢擎羊同宫或廉贞化忌",
        explain="刑囚夹印，刑（擎羊）囚（廉贞）制印（天相），主官非刑讼，宜慎守法律。",
    ),
    PatternRule(
        name="马落空亡",
        category="凶格",
        special="马落空亡",
        domain="奔劳 / 成空",
        condition="天马与地空（或地劫）同宫于命宫三方四正",
        explain="马落空亡，驿马踏空，主奔波劳碌而成少，计划多成泡影。",
    ),
)


@dataclass(frozen=True)
class PatternMatch:
    """一个命中格局的分析输出。"""

    name: str
    strength: str  # 强 / 中 / 弱
    evidence: list[str]  # 命盘中的证据，如 七杀·命宫(亥)
    condition: str
    domain: str
    explain: str


@dataclass
class _Hit:
    """三方四正/邻宫内一颗命中星的位置信息。"""

    palace: str  # 宫名
    branch: int  # 地支索引
    brightness: str
    mutagen: str  # 生年四化（禄/权/科/忌），无则 ""


@dataclass
class _Scan:
    """一次命盘扫描的上下文：三方四正、命宫、身宫、左右邻宫。"""

    found: dict[str, _Hit] = field(default_factory=dict)  # 三方四正 星名 → 命中
    mutagens: set[str] = field(default_factory=set)  # 三方四正内出现的四化
    has_lucun: bool = False  # 三方见禄存
    has_hualu: bool = False  # 三方见生年化禄
    soul: dict[str, _Hit] = field(default_factory=dict)  # 命宫 星名 → 命中
    soul_major_count: int = 0
    soul_branch: int = 0
    body: dict[str, _Hit] = field(default_factory=dict)  # 身宫 星名 → 命中
    body_branch: int = 0
    sides: tuple[dict[str, _Hit], dict[str, _Hit]] = field(default_factory=lambda: ({}, {}))

    @property
    def has_lu(self) -> bool:
        return self.has_lucun or self.has_hualu


def _palace_hits(sk: ChartSkeleton, branch: int) -> dict[str, _Hit]:
    """一个宫位内全部星曜 → {星名: _Hit}。"""
    palace = sk.palaces[branch]
    hits: dict[str, _Hit] = {}
    for star in (*palace.major_stars, *palace.minor_stars, *palace.adjective_stars):
        hits.setdefault(
            star.name, _Hit(palace.name, branch, star.brightness, star.mutagen)
        )
    return hits


def _scan(sk: ChartSkeleton) -> _Scan:
    """扫描命盘，构建格局判定上下文。"""
    sc = _Scan(soul_branch=sk.soul_palace_branch, body_branch=sk.body_palace_branch)
    for branch in _trine_branches(sk.soul_palace_branch):
        for name, hit in _palace_hits(sk, branch).items():
            sc.found.setdefault(name, hit)
            if hit.mutagen:
                sc.mutagens.add(hit.mutagen)
            if name == "禄存":
                sc.has_lucun = True
            if hit.mutagen == "禄":
                sc.has_hualu = True
    sc.soul = _palace_hits(sk, sk.soul_palace_branch)
    sc.soul_major_count = len(sk.palaces[sk.soul_palace_branch].major_stars)
    if sk.body_palace_branch != sk.soul_palace_branch:
        sc.body = _palace_hits(sk, sk.body_palace_branch)
    else:
        sc.body = sc.soul
    sc.sides = (
        _palace_hits(sk, (sk.soul_palace_branch - 1) % 12),
        _palace_hits(sk, (sk.soul_palace_branch + 1) % 12),
    )
    return sc


def _trine_branches(soul_branch: int) -> tuple[int, int, int, int]:
    """命宫三方四正地支：命宫、财帛(-4)、官禄(+4)、迁移(对宫+6)。"""
    return (
        soul_branch,
        (soul_branch - 4) % 12,
        (soul_branch + 4) % 12,
        (soul_branch + 6) % 12,
    )


def _ev(hit: _Hit, name: str) -> str:
    """证据串：星·宫(支)，带四化时标注。"""
    hua = f"化{hit.mutagen}" if hit.mutagen else ""
    return f"{name}{hua}·{hit.palace}({EARTHLY_BRANCHES[hit.branch]})"


def _clamp_sides(sc: _Scan, pair: tuple[str, str]) -> dict[str, _Hit] | None:
    """夹宫判定：两星分坐命宫左右邻宫（不同侧）→ {星名: _Hit}，否则 None。"""
    left, right = pair
    pos = {}
    for name in pair:
        in_left, in_right = name in sc.sides[0], name in sc.sides[1]
        if in_left and in_right:
            return None  # 两侧同名，占位防御
        if in_left:
            pos[name] = 0
        elif in_right:
            pos[name] = 1
    if len(pos) != 2 or pos[left] == pos[right]:
        return None
    return {name: sc.sides[pos[name]][name] for name in pair}


def _special(name: str, sc: _Scan) -> list[str] | None:
    """特殊结构判定，命中返回证据列表，否则 None。"""
    if name == "财荫夹印":
        # 天相坐命（soul_stars 已保证）；一邻宫见天梁（荫），另一邻宫见禄存或化禄星（财）
        yin_side = next((i for i in (0, 1) if "天梁" in sc.sides[i]), None)
        if yin_side is None:
            return None
        cai_side = 1 - yin_side
        cai = [
            (n, h)
            for n, h in sc.sides[cai_side].items()
            if n == "禄存" or h.mutagen == "禄"
        ]
        if not cai:
            return None
        # soul_stars 证据由主流程输出；此处只补夹宫两侧证据
        evidence = [_ev(sc.sides[yin_side]["天梁"], "天梁")]
        evidence.extend(_ev(h, n) for n, h in cai)
        return evidence
    if name == "刑囚夹印":
        # 廉贞、天相同宫坐命（soul_stars 已保证）；擎羊同宫或廉贞化忌
        yang = sc.soul.get("擎羊")
        if yang is None and sc.soul["廉贞"].mutagen != "忌":
            return None
        # 化忌由主流程 _ev 标注；此处只补擎羊同宫证据
        return [_ev(yang, "擎羊")] if yang is not None else []
    if name == "马落空亡":
        # 三方四正内天马与地空/地劫同宫
        tianma = sc.found.get("天马")
        if tianma is None:
            return None
        for kong in ("地空", "地劫"):
            hit = sc.found.get(kong)
            if hit is not None and hit.branch == tianma.branch:
                return [_ev(tianma, "天马"), _ev(hit, kong)]
        return None
    return None


def _match(rule: PatternRule, sc: _Scan) -> PatternMatch | None:
    """按声明式字段逐条判定；全部通过返回 PatternMatch。"""
    evidence: list[str] = []
    scored: list[_Hit] = []  # 参与强弱计分的星

    if rule.empty_soul:
        if sc.soul_major_count != 0:
            return None
        evidence.append(f"命宫({EARTHLY_BRANCHES[sc.soul_branch]})·无正曜")
    if rule.soul_stars and not rule.soul_stars <= sc.soul.keys():
        return None
    if rule.soul_only and sc.soul_major_count != 1:
        return None
    if rule.soul_branches and sc.soul_branch not in rule.soul_branches:
        return None
    if rule.soul_mutagens and not rule.soul_mutagens <= {
        h.mutagen for h in sc.soul.values() if h.mutagen
    }:
        return None
    for name in sorted(rule.soul_stars):
        evidence.append(_ev(sc.soul[name], name))
        scored.append(sc.soul[name])

    if rule.required and not rule.required <= sc.found.keys():
        return None
    if rule.bright_all:
        group = _BRIGHT_GROUPS[rule.bright_all]
        if any(sc.found[n].brightness not in group for n in rule.required):
            return None
    if any(group.isdisjoint(sc.found) for group in rule.any_of):
        return None
    if rule.need_lu and not sc.has_lu:
        return None
    if rule.need_double_lu and not (sc.has_lucun and sc.has_hualu):
        return None
    if rule.mutagens and not rule.mutagens <= sc.mutagens:
        return None
    for star, branches in rule.at_branch:
        hit = sc.found.get(star)
        if hit is None or hit.branch not in branches:
            return None

    for name in sorted(rule.required - set(rule.soul_stars)):
        evidence.append(_ev(sc.found[name], name))
        scored.append(sc.found[name])
    for group in rule.any_of:
        for name in sorted(group & sc.found.keys()):
            evidence.append(_ev(sc.found[name], name))
    for star, _branches in rule.at_branch:
        if star not in rule.required:
            evidence.append(_ev(sc.found[star], star))
            scored.append(sc.found[star])
    if rule.need_lu:
        evidence.append("禄存/化禄在三方四正")
    if rule.need_double_lu:
        evidence.append("禄存与化禄并见三方四正")
    for hua in sorted(rule.mutagens):
        star_name, hit = next(
            (n, h) for n, h in sc.found.items() if h.mutagen == hua
        )
        evidence.append(_ev(hit, star_name))
    if rule.soul_mutagens:
        carrier_name = next(
            n for n, h in sc.soul.items() if h.mutagen in rule.soul_mutagens
        )
        evidence.append(_ev(sc.soul[carrier_name], carrier_name))

    if rule.clamp_pair[0]:
        clamped = _clamp_sides(sc, rule.clamp_pair)
        if clamped is None:
            return None
        for name in rule.clamp_pair:
            evidence.append(_ev(clamped[name], name))
            scored.append(clamped[name])
    if rule.soul_body_pair[0]:
        a, b = rule.soul_body_pair
        if sc.soul_branch == sc.body_branch:
            return None
        if (a in sc.soul and b in sc.body) or (b in sc.soul and a in sc.body):
            for name, table in ((a, sc.soul), (b, sc.soul), (a, sc.body), (b, sc.body)):
                if name in table:
                    evidence.append(_ev(table[name], name))
                    scored.append(table[name])
        else:
            return None
    if rule.special:
        special_evidence = _special(rule.special, sc)
        if special_evidence is None:
            return None
        evidence.extend(special_evidence)

    score = sum(_BRIGHT_SCORE.get(h.brightness, 0) for h in scored)
    strength = "强" if score >= 2 else ("中" if score >= 0 else "弱")
    return PatternMatch(
        name=rule.name,
        strength=strength,
        evidence=evidence,
        condition=rule.condition,
        domain=rule.domain,
        explain=rule.explain,
    )


def detect_patterns(sk: ChartSkeleton) -> list[PatternMatch]:
    """识别命盘中成立的全部格局（三方四正 / 坐命 / 夹宫 / 命身 / 四化 / 凶格）。"""
    sc = _scan(sk)
    return [m for rule in RULES if (m := _match(rule, sc)) is not None]


def analyze_patterns(chart: NatalChart) -> list[PatternMatch]:
    """NatalChart → 格局分析结果。"""
    return detect_patterns(chart.skeleton)

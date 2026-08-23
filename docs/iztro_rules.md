# iztro 排盘规则文档（可实现级）

> 基准版本：**iztro v2.6.0**（npm 安装版，与 GitHub tag `v2.6.0` 一致）。
> 依赖：`lunar-lite@0.2.8`、`lunar-typescript@^1.7.8`。
> 本文所有行号均指 **TypeScript 源码**（`/tmp/iztro-src/src/...`，tag v2.6.0）。
> 本文是 Python 实现的唯一规则来源；一切以 iztro 实际代码为准，不以传统书籍为准。

## 0. 全局约定与基础数据

### 0.1 索引体系（贯穿全库）

- **地支索引** `EARTHLY_BRANCHES`（`data/constants.ts:19`）：
  `[子,丑,寅,卯,辰,巳,午,未,申,酉,戌,亥]`，子=0 … 亥=11。
- **天干索引** `HEAVENLY_STEMS`（`data/constants.ts:5`）：
  `[甲,乙,丙,丁,戊,己,庚,辛,壬,癸]`，甲=0 … 癸=9。
- **宫位索引**：紫微斗数以**寅宫为 0**，顺地支方向（寅→卯→辰→…→丑）编号 0~11。
  即 `宫位索引 = fixIndex(地支索引 - 2)`。
- `fixIndex(index, max=12)`（`utils/index.ts:40`）：取模归一到 `[0, max)`（负数循环加 max，≥max 循环减 max；`-0` 归一为 0）。天干场景传 `max=10`。
- `fixEarthlyBranchIndex(地支)`（`utils/index.ts:106`）：`fixIndex(地支索引 - 寅索引)`，即地支 → 宫位索引。

### 0.2 时辰索引（0~12）

`CHINESE_TIME` / `TIME_RANGE`（`data/constants.ts:96,113`）：

| timeIndex | 名称 | 时段 |
|---|---|---|
| 0 | 早子时 | 00:00~01:00 |
| 1 | 丑时 | 01:00~03:00 |
| 2 | 寅时 | 03:00~05:00 |
| 3 | 卯时 | 05:00~07:00 |
| 4 | 辰时 | 07:00~09:00 |
| 5 | 巳时 | 09:00~11:00 |
| 6 | 午时 | 11:00~13:00 |
| 7 | 未时 | 13:00~15:00 |
| 8 | 申时 | 15:00~17:00 |
| 9 | 酉时 | 17:00~19:00 |
| 10 | 戌时 | 19:00~21:00 |
| 11 | 亥时 | 21:00~23:00 |
| 12 | 晚子时 | 23:00~00:00 |

`timeToIndex(hour)`（`utils/index.ts:167`）：`hour==0→0`；`hour==23→12`；其余 `floor((hour+1)/2)`。

### 0.3 全局配置（`astro/astro.ts:103` `config()` / `getConfig()`）

| 配置 | 取值 | 默认 | 含义 |
|---|---|---|---|
| `yearDivide` | `'normal' \| 'exact'` | `'normal'` | 本命盘年分界：normal=正月初一，exact=立春 |
| `horoscopeDivide` | `'normal' \| 'exact'` | `'normal'` | 运限（年系/月系星、流年神煞等）分界 |
| `ageDivide` | `'normal' \| 'birthday'` | `'normal'` | 小限分割点：normal=自然年，birthday=生日 |
| `dayDivide` | `'current' \| 'forward'` | `'forward'` | 晚子时归属：forward=算来日，current=算当日 |
| `algorithm` | `'default' \| 'zhongzhou'` | `'default'` | 安星派别：default=《紫微斗数全书》，zhongzhou=中州派 |
| `mutagens` | 天干→4星数组 | 内置表 | 覆写四化 |
| `brightness` | 星→12亮度数组 | 内置表 | 覆写亮度 |

注意 iztro 内部默认值 **`yearDivide: 'normal'`（正月初一分界）**，与传统"立春换年"不同；lunar-lite 自身默认是 `exact`（`lunar-lite/lib/ganzhi.js:30`），iztro 显式传入了配置值。

### 0.4 干支获取（lunar-lite）

`getHeavenlyStemAndEarthlyBranchBySolarDate(dateStr, timeIndex, {year, month})`
（`lunar-lite/lib/ganzhi.js:29`）：

- 构造 `Solar.fromYmdHms(y, m, d, max(timeIndex*2-1, 0), 30, 0)`（timeIndex=12 → 23:30；timeIndex=0 → 00:30）。
- `yearly`：`year==='normal'` 用正月初一分界，`'exact'` 用立春分界。
- `monthly`：`month==='exact'` 用节气月；`'normal'` 用五虎遁按农历月初一算（闰月且日>15 时月份+1）。
- `daily`：`getDayGanExact/getDayZhiExact` —— **23:00~23:59 算作次日的日干支**（`lunar-typescript/dist/lib/Lunar.mjs:162` 附近，晚子时 dayGan/dayZhi 各 +1）。
- `hourly`：`getTimeGan/getTimeZhi`；时支 23:xx 为子（时支索引 0）；时干按**次日日干**以五鼠遁起。
- 因此 **timeIndex=12 与 timeIndex=0 的时支索引都是 0（子）**，二者区别只体现在农历日（+1）和日/时干支上。

`solar2lunar`（`lunar-lite/lib/convertor.js:39`）→ `{lunarYear, lunarMonth, lunarDay, isLeap}`（lunarMonth 已取绝对值）。
`getTotalDaysOfLunarMonth(solarDateStr)`（`lunar-lite/lib/misc.js:35`）→ 该农历月实际天数 29|30。

---

## 1. API：bySolar / byLunar 与 Astrolabe 结构

### 1.1 签名（`astro/astro.ts:173, 325`）

```ts
bySolar(solarDate: string, timeIndex: number, gender: GenderName,
        fixLeap: boolean = true, language?: Language): FunctionalAstrolabe

byLunar(lunarDateStr: string, timeIndex: number, gender: GenderName,
        isLeapMonth: boolean = false, fixLeap: boolean = true,
        language?: Language): FunctionalAstrolabe
```

- `solarDate`：`'YYYY-M-D'`；`lunarDateStr`：`'YYYY-M-D'`（如 2000-7-17）。
- `timeIndex`：0~12，见 §0.2。
- `gender`：`'男'|'女'` 或 `'male'|'female'`（`kot()` 反查，多语言皆可）。
- `isLeapMonth`：是否闰月；该年该月无闰月时不生效。`byLunar` 内部只是 `lunar2solar(lunarDateStr, isLeapMonth)` 后转调 `bySolar`（`astro/astro.ts:331`）。
- `fixLeap`：默认 `true`；闰月 15 日（含）之前按当月算、之后按下月算（见 §14）。
- `language`：`'en-US'|'ja-JP'|'ko-KR'|'zh-CN'|'zh-TW'|'vi-VN'`，设置后全局生效（`setLanguage`）。
- 旧名 `astrolabeBySolarDate` / `astrolabeByLunarDate` 为 deprecated 别名（`astro/astro.ts:153, 306`）。
- `withOptions(option)`（`astro/astro.ts:450`）：`{type:'solar'|'lunar', dateStr, timeIndex, gender, isLeapMonth?, fixLeap?, language?, config?, astroType?: 'heaven'|'earth'|'human'}`。`astroType='earth'` 以身宫干支为命宫重排（地盘），`'human'` 以福德宫干支为命宫重排（人盘），走 `rearrangeAstrolable`（`astro/astro.ts:338`）。

### 1.2 bySolar 主流程（`astro/astro.ts:173-276`）

1. 若 `dayDivide==='current'` 且 `timeIndex>=12`，把时辰改为 0（早子时，算当日）。
2. 取年干支（按 `yearDivide`），定 `heavenlyStemOfYear / earthlyBranchOfYear`。
3. `getSoulAndBody` → 命宫/身宫索引与命宫干支（§2）。
4. `getPalaceNames(soulIndex)` → 十二宫名（§3）。
5. `getMajorStar`（§7）、`getMinorStar`（§8）、`getAdjectiveStar`（§8）、`getchangsheng12`、`getBoShi12`、`getYearly12`（§11）、`getHoroscope`（§12/13）。
6. 组装 12 个宫位：`palaces[i]`（i=0 为寅宫，见 §3/§4）。
7. 组装 `FunctionalAstrolabe`（见下）。

### 1.3 Astrolabe 对象（toJSON 后的纯 JSON，`data/types/astro.ts:148`）

```
{
  gender: string,                       // 翻译后性别
  solarDate: string,                    // 'YYYY-M-D'
  lunarDate: string,                    // 中文农历串 lunar.toString()
  chineseDate: string,                  // '甲子 乙丑 丙寅 丁卯' 形式
  rawDates: { lunarDate: LunarDate, chineseDate: HeavenlyStemAndEarthlyBranchDate },
  time: string,                         // '早子时' 等
  timeRange: string,                    // '00:00~01:00'
  sign: string,                         // 星座（阳历算）
  zodiac: string,                       // 生肖（按年支）
  earthlyBranchOfSoulPalace: string,    // 命宫地支
  earthlyBranchOfBodyPalace: string,    // 身宫地支
  soul: string,                         // 命主星（见 §2.4）
  body: string,                         // 身主星（按生年支查表）
  fiveElementsClass: string,            // '水二局'...'火六局'
  palaces: Palace[12],                  // i=0 为寅宫
  copyright: string
}
```

身主表（`data/earthlyBranches.ts`，按生年支）：
子→火星，丑→天相，寅→天梁，卯→天同，辰→文昌，巳→天机，
午→火星，未→天相，申→天梁，酉→天同，戌→文昌，亥→天机。

### 1.4 Palace 对象（`data/types/palace.ts:44`；`astro/FunctionalPalace.ts:206`）

```
{
  index: number,                 // 宫位索引（寅=0）
  name: string,                  // '命宫'|'兄弟'|...（身宫不单独占宫，见 isBodyPalace）
  isBodyPalace: boolean,         // 身宫所在
  isOriginalPalace: boolean,     // 来因宫：宫支非子丑 且 宫干===生年干（astro.ts:200）
  heavenlyStem: string,          // 宫干
  earthlyBranch: string,         // 宫支
  majorStars: Star[],            // 主星
  minorStars: Star[],            // 辅星（14颗）
  adjectiveStars: Star[],        // 杂曜
  changsheng12: string,          // 长生12神之一
  boshi12: string,               // 博士12神之一
  jiangqian12: string,           // 将前12神之一
  suiqian12: string,             // 岁前12神之一
  decadal: { range: [number, number], heavenlyStem: string, earthlyBranch: string },
  ages: number[]                 // 本宫小限虚岁列表（10个）
}
```

### 1.5 Star 对象（`data/types/star.ts:19`）

```
{
  name: string,          // 星曜名（已翻译）
  type: 'major'|'soft'|'tough'|'adjective'|'flower'|'helper'|'lucun'|'tianma',
  scope: 'origin'|'decadal'|'yearly'|'monthly'|'daily'|'hourly',
  brightness?: string,   // '庙'|'旺'|'得'|'利'|'平'|'不'|'陷'；无数据为 '' 或 undefined
  mutagen?: string       // '禄'|'权'|'科'|'忌'；无四化为 undefined
}
```

注意：iztro 亮度七级为 **庙/旺/得/利/平/不/陷**（`i18n/locales/zh-CN/brightness.ts`），
没有"闲"；数据里用的是 `bu`（不）。

---

## 2. 命宫 / 身宫安法

`getSoulAndBody`（`astro/palace.ts:42-99`）。

1. 取时支索引 `tIdx = 时支在 EARTHLY_BRANCHES 的索引`（晚子时=子时=0，见 §0.4）。
2. 取月索引 `monthIndex = fixLunarMonthIndex(solarDate, timeIndex, fixLeap)`
   （`utils/index.ts:125`）：

   ```
   monthIndex = fixIndex(lunarMonth + 1 - 2 + (isLeap && fixLeap && lunarDay > 15 && timeIndex !== 12 ? 1 : 0))
   ```

   即**正月=0，二月=1，…，十二月=11**；闰月修正见 §14。
3. **命宫索引** `soulIndex = fixIndex(monthIndex - tIdx)`
   （寅起正月顺数至生月，再逆数生时）。
4. **身宫索引** `bodyIndex = fixIndex(monthIndex + tIdx)`（同点顺数生时）。
5. 命宫天干：`stemOfSoulIndex = fixIndex(TIGER_RULE[年干].索引 + soulIndex, 10)`（五虎遁，§4）。
6. 命宫地支：`EARTHLY_BRANCHES[fixIndex(soulIndex + 2)]`。

地盘/人盘重排（`from` 参数）时：`soulIndex = fixEarthlyBranchIndex(from.earthlyBranch)`；
身宫改为 `bodyIndex = fixIndex([0,2,4,6,8,10,0,2,4,6,8,10,0][timeIndex] + soulIndex)`
（`astro/palace.ts:69-73`）。

### 2.1 命主（soul）

- 默认派：按**命宫地支**查 `earthlyBranches[支].soul`；
- 中州派（`algorithm==='zhongzhou'`）：按**生年支**查（`astro/astro.ts:248-251`）。

命主表（`data/earthlyBranches.ts`）：子→贪狼，丑→巨门，寅→禄存，卯→文曲，辰→廉贞，
巳→武曲，午→破军，未→武曲，申→廉贞，酉→文曲，戌→禄存，亥→巨门。

---

## 3. 十二宫排列与地支映射

`PALACES` 常量（`data/constants.ts:51`）顺序（逆时针宫序，即远离命宫方向）：

```
[命宫, 父母, 福德, 田宅, 官禄, 仆役, 迁移, 疾厄, 财帛, 子女, 夫妻, 兄弟]
```

`getPalaceNames(soulIndex)`（`astro/palace.ts:162`）：
`palaceNames[i] = PALACES[fixIndex(i - soulIndex)]`，i = 宫位索引（寅=0）。

即：命宫在 soulIndex；沿**地支顺行方向**（寅→卯→…，宫位索引递增）依次是
父母、福德、田宅、官禄、仆役、迁移（命宫对宫，+6）、疾厄、财帛、子女、夫妻、兄弟。
等价传统口诀：从命宫**逆行**（宫位索引递减）安 兄弟、夫妻、子女、财帛、疾厄、迁移、
仆役、官禄、田宅、福德、父母。

宫位地支固定：`palaces[i].earthlyBranch = EARTHLY_BRANCHES[fixIndex(2 + i)]`
（`astro/astro.ts:196`），即 i=0 必为寅宫，i=11 必为丑宫。

---

## 4. 宫干：五虎遁

`TIGER_RULE`（`data/constants.ts:142`）：年干 → 寅宫天干。

| 年干 | 甲 | 乙 | 丙 | 丁 | 戊 | 己 | 庚 | 辛 | 壬 | 癸 |
|---|---|---|---|---|---|---|---|---|---|---|
| 寅宫干 | 丙 | 戊 | 庚 | 壬 | 甲 | 丙 | 戊 | 庚 | 壬 | 甲 |

宫位天干（`astro/astro.ts:191-194`）：

```
palaceStem[i] = HEAVENLY_STEMS[ fixIndex( indexOf(TIGER_RULE[年干]) + i, 10 ) ]   // i = 宫位索引(寅=0)
```

（源码写作 `indexOf(命宫干) - soulIndex + i`，二者等价，因为命宫干本身就是五虎遁+soulIndex 推出的。）

来因宫 `isOriginalPalace`：宫支非子、非丑，且宫干 === 生年干（`astro/astro.ts:200`）。

---

## 5. 五行局（纳音定局）

`getFiveElementsClass(heavenlyStem, earthlyBranch)`（`astro/palace.ts:137-159`），
输入为**命宫干支**（或重排盘的 from 干支）。

取数：

- 天干数 = `floor(天干索引 / 2) + 1`：甲乙=1，丙丁=2，戊己=3，庚辛=4，壬癸=5。
- 地支数 = `floor(fixIndex(地支索引, 6) / 2) + 1`：子丑/午未=1，寅卯/申酉=2，辰巳/戌亥=3。
- `n = 天干数 + 地支数`；`while (n > 5) n -= 5`。
- 查表 `['wood3rd','metal4th','water2nd','fire6th','earth5th'][n-1]`：

| n | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 局 | 木三局 | 金四局 | 水二局 | 火六局 | 土五局 |

`FiveElementsClass` 枚举（`data/constants.ts:84`）：水二局=2，木三局=3，金四局=4，土五局=5，火六局=6。
局数即起运虚岁（§12）。

---

## 6. 紫微星定位（起紫微诀）

`getStartIndex`（`star/location.ts:35-108`）。

1. 五行局数 `S = FiveElementsClass[局]`（2~6），由命宫干支定（§5）。
2. 农历日 `d = lunarDay`；**晚子时且 `dayDivide!=='current'` 时 `d = lunarDay + 1`**；
   若 `d > 当月总天数` 则 `d -= 当月总天数`（跨月归零处理，`location.ts:60-66`）。
3. 求最小非负整数 `offset`，使 `(d + offset) % S === 0`；`quotient = floor((d+offset)/S)`。
4. `quotient %= 12`；`ziweiIndex = quotient - 1`。
5. `offset` 为偶数：`ziweiIndex += offset`；为奇数：`ziweiIndex -= offset`。
6. `ziweiIndex = fixIndex(ziweiIndex)`（寅=0 的宫位索引）。
7. **天府**：`tianfuIndex = fixIndex(12 - ziweiIndex)`（与紫微关于寅申轴对称）。

---

## 7. 十四主星偏移表

`getMajorStar`（`star/majorStar.ts:24-86`）。数组下标 i 为**相对紫微/天府的宫位偏移**，
`''` 表示空位。

紫微系（逆行，宫位索引 = `fixIndex(ziweiIndex - i)`）：

| i | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| 星 | 紫微 | 天机 | — | 太阳 | 武曲 | 天同 | — | — | 廉贞 |

天府系（顺行，宫位索引 = `fixIndex(tianfuIndex + i)`）：

| i | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 星 | 天府 | 太阴 | 贪狼 | 巨门 | 天相 | 天梁 | 七杀 | — | — | — | 破军 |

每颗主星带 `brightness`（§9）与 `mutagen`（生年干四化，§10），`type='major'`, `scope='origin'`。

---

## 8. 辅星与杂曜安法（全表）

公共输入记号：年干 `YS`、年支 `YB`（均按 `yearDivide` 取；年系杂曜中部分按 `horoscopeDivide`，
见各条）、`monthIndex`（§2，正月=0）、`lunarMonth = monthIndex+1`、
`dayIndex = fixLunarDayIndex(lunarDay, timeIndex)`（`utils/index.ts:141`：
**timeIndex≥12 时 = lunarDay，否则 = lunarDay − 1**，即初一=0 的日偏移）、
`tIdx = fixIndex(timeIndex)`（晚子时 12 → 0）。

### 8.1 辅星 14 颗（`star/minorStar.ts:24`，type 见表）

| 星 | 输入 | 规则（宫位索引，寅=0） | 依据 |
|---|---|---|---|
| 左辅 (soft) | 月 | `fixIndex(辰宫索引4 + monthIndex)`，即辰起正月顺数 | location.ts:255 |
| 右弼 (soft) | 月 | `fixIndex(戌宫索引10 − monthIndex)`，戌起正月逆数 | location.ts:255 |
| 文昌 (soft) | 时 | `fixIndex(10 − tIdx)`，戌上逆时 | location.ts:278 |
| 文曲 (soft) | 时 | `fixIndex(4 + tIdx)`，辰上顺时 | location.ts:278 |
| 天魁 (soft) | 年干 | 见下表 | location.ts:205 |
| 天钺 (soft) | 年干 | 见下表 | location.ts:205 |
| 禄存 (lucun) | 年干 | 见下表 | location.ts:118 |
| 擎羊 (tough) | 年干 | `fixIndex(禄存+1)` | location.ts:196 |
| 陀罗 (tough) | 年干 | `fixIndex(禄存−1)` | location.ts:197 |
| 天马 (tianma) | 年支 | 见下表 | location.ts:131-155 |
| 火星 (tough) | 年支+时 | 见下表 + tIdx 顺加 | location.ts:372 |
| 铃星 (tough) | 年支+时 | 见下表 + tIdx 顺加 | location.ts:372 |
| 地空 (tough) | 时 | `fixIndex(亥宫索引11 − tIdx)` | location.ts:347 |
| 地劫 (tough) | 时 | `fixIndex(11 + tIdx)` | location.ts:347 |

天魁/天钺（年干 → 宫位地支）：

| 年干 | 甲戊庚 | 乙己 | 辛 | 丙丁 | 壬癸 |
|---|---|---|---|---|---|
| 天魁 | 丑 | 子 | 午 | 亥 | 卯 |
| 天钺 | 未 | 申 | 寅 | 酉 | 巳 |

禄存（年干 → 宫位地支）：甲寅、乙卯、丙巳、丁午、戊巳、己午、庚申、辛酉、壬亥、癸子。

天马（年支 → 宫位地支）：寅午戌→申；申子辰→寅；巳酉丑→亥；亥卯未→巳。

火星/铃星起子时的宫位（再顺加 tIdx，`fixIndex(起点 + tIdx)`）：

| 年支组 | 寅午戌 | 申子辰 | 巳酉丑 | 亥卯未 |
|---|---|---|---|---|
| 火星起点 | 丑 | 寅 | 卯 | 酉 |
| 铃星起点 | 卯 | 戌 | 戌 | 戌 |

（注意：巳酉丑与亥卯未两组铃星起点同为戌。）

### 8.2 日系星（`star/location.ts:302` `getDailyStarIndex`，输入：月+日+时）

| 星 (type=adjective) | 规则 |
|---|---|
| 三台 | `fixIndex(左辅索引 + dayIndex)`（左辅起初一顺行至生日） |
| 八座 | `fixIndex(右弼索引 − dayIndex)`（右弼起初一逆行） |
| 恩光 | `fixIndex(文昌索引 + dayIndex − 1)`（文昌起初一顺行再退一宫） |
| 天贵 | `fixIndex(文曲索引 + dayIndex − 1)`（文曲起初一顺行再退一宫） |

### 8.3 时系星（`star/location.ts:324`，输入：时）

| 星 (adjective) | 规则 |
|---|---|
| 台辅 | `fixIndex(午宫索引6 + tIdx)` |
| 封诰 | `fixIndex(寅宫索引0 + tIdx)` |

### 8.4 月系星（`star/location.ts:821` `getMonthlyStarIndex`，输入：`monthIndex`）

| 星 (type) | 规则 |
|---|---|
| 解神/月解 (helper) | `['申','戌','子','寅','辰','午'][floor(monthIndex/2)]`（正二在申，三四在戌，五六在子，七八在寅，九十在辰，十一十二在午） |
| 天姚 (flower) | `fixIndex(丑宫索引1 + monthIndex)`（丑起正月顺数） |
| 天刑 (adjective) | `fixIndex(酉宫索引9 + monthIndex)`（酉起正月顺数） |
| 阴煞 (adjective) | `['寅','子','戌','申','午','辰'][monthIndex % 6]`（正七寅，二八子，三九戌，四十申，五十一午，六十二辰） |
| 天月 (adjective) | `['戌','巳','辰','寅','未','卯','亥','未','寅','午','戌','寅'][monthIndex]`（正月起） |
| 天巫 (adjective) | `['巳','申','寅','亥'][monthIndex % 4]`（正五九巳，二六十申，三七十一寅，四八十二亥） |

### 8.5 年系星（`star/location.ts:640` `getYearlyStarIndex`）

`getYearlyStarIndex`（`star/location.ts:640`）内部的年干支按 **`horoscopeDivide`** 配置取
（`location.ts:643-646`）。**例外**：红鸾、天喜由 `getAdjectiveStar` 单独用 `yearDivide` 的年支计算
（`adjectiveStar.ts:25-28,35-36`）。除特殊说明外 type='adjective'。

| 星 | 输入 | 规则 |
|---|---|---|
| 红鸾 (flower) | 年支（**yearDivide**） | `fixIndex(卯宫索引3 − 年支索引)` | location.ts:426 |
| 天喜 (flower) | 年支（**yearDivide**） | `fixIndex(红鸾 + 6)`（对宫） | location.ts:429 |
| 咸池 (flower) | 年支 | 寅午戌→卯；申子辰→酉；巳酉丑→午；亥卯未→子 | location.ts:446 |
| 华盖 | 年支 | 寅午戌→戌；申子辰→辰；巳酉丑→丑；亥卯未→未 | location.ts:446 |
| 孤辰 | 年支 | 寅卯辰→巳；巳午未→申；申酉戌→亥；亥子丑→寅 | location.ts:498 |
| 寡宿 | 年支 | 寅卯辰→丑；巳午未→辰；申酉戌→未；亥子丑→戌 | location.ts:498 |
| 天才 | 年支+命宫 | `fixIndex(soulIndex + 年支索引)`（命宫起子顺数至年支） | location.ts:650 |
| 天寿 | 年支+身宫 | `fixIndex(bodyIndex + 年支索引)`（身宫起子顺数至年支） | location.ts:651 |
| 天厨 | 年干 | `['巳','午','子','巳','午','申','寅','午','酉','亥'][年干索引]`（甲巳乙午丙子丁巳戊午己申庚寅辛午壬酉癸亥） | location.ts:652 |
| 破碎 | 年支 | `['巳','丑','酉'][年支索引 % 3]`（子午卯酉→巳，丑辰未戌→丑，寅申巳亥→酉；按年支索引 mod 3：子0→巳、丑1→丑、寅2→酉…） | location.ts:657 |
| 蜚廉 | 年支 | `['申','酉','戌','巳','午','未','寅','卯','辰','亥','子','丑'][年支索引]` | location.ts:661 |
| 龙池 | 年支 | `fixIndex(辰宫索引4 + 年支索引)`（辰起子顺数） | location.ts:667 |
| 凤阁 | 年支 | `fixIndex(戌宫索引10 − 年支索引)`（戌起子逆数） | location.ts:668 |
| 天哭 | 年支 | `fixIndex(午宫索引6 − 年支索引)`（午起子逆数） | location.ts:669 |
| 天虚 | 年支 | `fixIndex(午宫索引6 + 年支索引)`（午起子顺数） | location.ts:670 |
| 天官 | 年干 | `['未','辰','巳','寅','卯','酉','亥','酉','戌','午'][年干索引]`（甲未乙辰丙巳丁寅戊卯己酉庚亥辛酉壬戌癸午） | location.ts:671 |
| 天福 | 年干 | `['酉','申','子','亥','卯','寅','午','巳','午','巳'][年干索引]`（甲酉乙申丙子丁亥戊卯己寅庚午辛巳壬午癸巳） | location.ts:676 |
| 天德 | 年支 | `fixIndex(酉宫索引9 + 年支索引)` | location.ts:682 |
| 月德 | 年支 | `fixIndex(巳宫索引5 + 年支索引)` | location.ts:683 |
| 天空 | 年支 | `fixIndex(年支宫位索引 + 1)`（年支后一宫） | location.ts:684 |
| 截路 | 年干 | `['申','午','辰','寅','子'][年干索引 % 5]`（甲己申、乙庚午、丙辛辰、丁壬寅、戊癸子） | location.ts:685 |
| 空亡 | 年干 | `['酉','未','巳','卯','丑'][年干索引 % 5]`（甲己酉、乙庚未、丙辛巳、丁壬卯、戊癸丑） | location.ts:690 |
| 旬空 | 年干支 | 见下 | location.ts:695-707 |
| 天伤 | 性别+年支阴阳+命宫 | 默认：`fixIndex(5 + soulIndex)`（仆役宫） | location.ts:756 |
| 天使 | 同上 | 默认：`fixIndex(7 + soulIndex)`（疾厄宫） | location.ts:756 |
| 年解 (helper) | 年支 | `['戌','酉','申','未','午','巳','辰','卯','寅','丑','子','亥'][年支索引]`（戌起子逆数至年支） | location.ts:786 |
| 劫杀（杂曜） | 年支 | 申子辰→3（巳）；亥卯未→6（申）；寅午戌→9（亥）；巳酉丑→0（寅）。**仅中州派安置** | location.ts:550 |
| 大耗（杂曜） | 年支 | 年支对冲后阴阳移位：见下。**仅中州派安置** | location.ts:581 |
| 龙德（杂曜） | — | 中州派：取岁前12神中龙德所在宫（即 `fixIndex(年支宫位+7)`）。**仅中州派** | adjectiveStar.ts:75 |
| 截空 | 年干+年支阴阳 | 中州派：年支阳→截路位，年支阴→空亡位（`jiekongIndex`，location.ts:711-713）。**仅中州派安置** | |

**旬空算法**（`location.ts:695-707`）：

```
xunkong = fixIndex(年支宫位索引 + indexOf(癸) − indexOf(年干) + 1)   // = 年支宫位 + (9 − 年干索引 + 1)
若 (年支索引 % 2) !== (xunkong % 2)，则 xunkong = fixIndex(xunkong + 1)
```

即旬空落在与年支同阴阳的那个空亡宫。

**大耗（杂曜，中州派）**（`location.ts:581-598`）：
`matched = ['未','午','酉','申','亥','戌','丑','子','卯','寅','巳','辰'][年支索引]`，
再 `fixIndex(matched 的地支索引 − 2)`（转宫位索引）。
展开：子→未，丑→午，寅→酉，卯→申，辰→亥，巳→戌，午→丑，未→子，申→卯，酉→寅，戌→巳，亥→辰。

**天伤/天使**：默认派固定 天伤=仆役、天使=疾厄（夹迁移）。中州派且阴男/阳女
（年支阴阳 ≠ 性别阴阳；年支索引偶为阳，male 记 0）时互换：天伤=疾厄、天使=仆役
（`location.ts:769-772`）。

### 8.6 杂曜安置总装（`star/adjectiveStar.ts:21`）

默认派安置：红鸾、天喜、天姚、咸池（flower）；月解、年解（helper）；三台、八座、恩光、
天贵、龙池、凤阁、天才、天寿、台辅、封诰、天巫、华盖、天官、天福、天厨、天月、天德、
月德、天空、旬空、截路、空亡、孤辰、寡宿、蜚廉、破碎、天刑、阴煞、天哭、天虚、天使、
天伤（adjective）。

中州派差异（`adjectiveStar.ts:68-88`）：**不安**截路、空亡；**改安** 龙德（岁前位）、
截空（单星）、劫杀、大耗。

---

## 9. 星曜亮度表（STARS_INFO）

数据源：`data/stars.ts:11`（`STARS_INFO`），键为星曜 key，`brightness` 数组**按宫位索引
（寅=0 起，顺地支）排列**。取用：`getBrightness(name, palaceIndex)`（`utils/index.ts:73`），
查不到（杂曜无数据）返回 `''`。可用 `config({brightness})` 全局覆写。

亮度 key → 中文：`miao 庙, wang 旺, de 得, li 利, ping 平, bu 不, xian 陷`。

**主星亮度表**（列 = 寅卯辰巳午未申酉戌亥子丑，即宫位索引 0~11）：

| 星 | 寅 | 卯 | 辰 | 巳 | 午 | 未 | 申 | 酉 | 戌 | 亥 | 子 | 丑 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 紫微 | 旺 | 旺 | 得 | 旺 | 庙 | 庙 | 旺 | 旺 | 得 | 旺 | 平 | 庙 |
| 天机 | 得 | 旺 | 利 | 平 | 庙 | 陷 | 得 | 旺 | 利 | 平 | 庙 | 陷 |
| 太阳 | 旺 | 庙 | 旺 | 旺 | 旺 | 得 | 得 | 陷 | 不 | 陷 | 陷 | 不 |
| 武曲 | 得 | 利 | 庙 | 平 | 旺 | 庙 | 得 | 利 | 庙 | 平 | 旺 | 庙 |
| 天同 | 利 | 平 | 平 | 庙 | 陷 | 不 | 旺 | 平 | 平 | 庙 | 旺 | 不 |
| 廉贞 | 庙 | 平 | 利 | 陷 | 平 | 利 | 庙 | 平 | 利 | 陷 | 平 | 利 |
| 天府 | 庙 | 得 | 庙 | 得 | 旺 | 庙 | 得 | 旺 | 庙 | 得 | 庙 | 庙 |
| 太阴 | 旺 | 陷 | 陷 | 陷 | 不 | 不 | 利 | 不 | 旺 | 庙 | 庙 | 庙 |
| 贪狼 | 平 | 利 | 庙 | 陷 | 旺 | 庙 | 平 | 利 | 庙 | 陷 | 旺 | 庙 |
| 巨门 | 庙 | 庙 | 陷 | 旺 | 旺 | 不 | 庙 | 庙 | 陷 | 旺 | 旺 | 不 |
| 天相 | 庙 | 陷 | 得 | 得 | 庙 | 得 | 庙 | 陷 | 得 | 得 | 庙 | 庙 |
| 天梁 | 庙 | 庙 | 庙 | 陷 | 庙 | 旺 | 陷 | 得 | 庙 | 陷 | 庙 | 旺 |
| 七杀 | 庙 | 旺 | 庙 | 平 | 旺 | 庙 | 庙 | 庙 | 庙 | 平 | 旺 | 庙 |
| 破军 | 得 | 陷 | 旺 | 平 | 庙 | 旺 | 得 | 陷 | 旺 | 平 | 庙 | 旺 |

**辅星亮度表**（同列序）：

| 星 | 寅 | 卯 | 辰 | 巳 | 午 | 未 | 申 | 酉 | 戌 | 亥 | 子 | 丑 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 文昌 | 陷 | 利 | 得 | 庙 | 陷 | 利 | 得 | 庙 | 陷 | 利 | 得 | 庙 |
| 文曲 | 平 | 旺 | 得 | 庙 | 陷 | 旺 | 得 | 庙 | 陷 | 旺 | 得 | 庙 |
| 火星 | 庙 | 利 | 陷 | 得 | 庙 | 利 | 陷 | 得 | 庙 | 利 | 陷 | 得 |
| 铃星 | 庙 | 利 | 陷 | 得 | 庙 | 利 | 陷 | 得 | 庙 | 利 | 陷 | 得 |
| 擎羊 | （空） | 陷 | 庙 | （空） | 陷 | 庙 | （空） | 陷 | 庙 | （空） | 陷 | 庙 |
| 陀罗 | 陷 | （空） | 庙 | 陷 | （空） | 庙 | 陷 | （空） | 庙 | 陷 | （空） | 庙 |

左辅、右弼、天魁、天钺、禄存、天马、地空、地劫及全部杂曜**无亮度数据**（`getBrightness`
返回 `''`）。源码注释称数组"从寅开始"（`data/stars.ts:8`），上表已按此对齐。

---

## 10. 生年四化表

数据：`data/heavenlyStems.ts:26`（每个天干的 `mutagen` 数组，顺序 **禄、权、科、忌**）。
取用：`getMutagen(starName, 年干)`（`utils/index.ts:85`）——星在数组中的下标即四化；
不在则 `mutagen=undefined`。可用 `config({mutagens})` 覆写。四化名称：`MUTAGEN =
['禄','权','科','忌']`（`data/stars.ts:2`）。

| 年干 | 禄 | 权 | 科 | 忌 |
|---|---|---|---|---|
| 甲 | 廉贞 | 破军 | 武曲 | 太阳 |
| 乙 | 天机 | 天梁 | 紫微 | 太阴 |
| 丙 | 天同 | 天机 | 文昌 | 廉贞 |
| 丁 | 太阴 | 天同 | 天机 | 巨门 |
| 戊 | 贪狼 | 太阴 | 右弼 | 天机 |
| 己 | 武曲 | 贪狼 | 天梁 | 文曲 |
| 庚 | 太阳 | 武曲 | 太阴 | 天同 |
| 辛 | 巨门 | 太阳 | 文曲 | 文昌 |
| 壬 | 天梁 | 紫微 | 左辅 | 武曲 |
| 癸 | 破军 | 巨门 | 太阴 | 贪狼 |

（即：庚科为太阴而非传统某些流派的"天府/天同"；戊科为右弼。以本表为准。）

---

## 11. 长生十二神、博士十二神、岁前/将前十二神

文件：`star/decorativeStar.ts`。均为每宫一个**字符串**（不是 Star 对象），
数组下标 = 宫位索引（寅=0）。顺逆判定统一为：
`GENDER[gender] === earthlyBranches[年支].yinYang`（年支索引偶数为阳；男=阳女=阴）
→ 一致（阳男/阴女）顺行，不一致（阴男/阳女）逆行。

### 11.1 长生十二神（`decorativeStar.ts:31,69`）

起点按五行局（`getChangesheng12StartIndex`）：

| 局 | 水二局 | 木三局 | 金四局 | 土五局 | 火六局 |
|---|---|---|---|---|---|
| 长生起点 | 申 | 亥 | 巳 | 申 | 寅 |

顺序：长生、沐浴、冠带、临官、帝旺、衰、病、死、墓、绝、胎、养。
阳男阴女：`fixIndex(startIdx + i)`；阴男阳女：`fixIndex(startIdx − i)`。

### 11.2 博士十二神（`decorativeStar.ts:123`）

从**禄存**宫位起，顺序：博士、力士、青龙、小耗、将军、奏书、飞廉、喜神、病符、大耗、
伏兵、官府。阳男阴女顺行 `fixIndex(luIndex + i)`，阴男阳女逆行 `fixIndex(luIndex − i)`。
（年干支按 `yearDivide` 取。）

### 11.3 岁前十二神（`decorativeStar.ts:204` `getYearly12`）

年干支按 **`horoscopeDivide`** 取。从**流年（生年）地支宫位**起顺行：

```
岁建、晦气、丧门、贯索、官符、小耗、大耗、龙德、白虎、天德、吊客、病符
suiqian12[fixIndex(年支宫位索引 + i)] = 上述第 i 个
```

中州派第 7 位（index 6）的"大耗"改名为 **岁破**（`decorativeStar.ts:219-237`）。

### 11.4 将前十二神（`decorativeStar.ts:170,204`）

起点（将星位，按年支）：寅午戌→午；申子辰→子；巳酉丑→酉；亥卯未→卯。
从起点顺行：

```
将星、攀鞍、岁驿、息神、华盖、劫煞、灾煞、天煞、指背、咸池、月煞、亡神
jiangqian12[fixIndex(起点 + i)] = 第 i 个
```

---

## 12. 大限

`getHoroscope`（`astro/palace.ts:186-234`）。

- 每宫大限虚岁区间：第 i 大限（从命宫数起，i 从 0）`range = [局数 + 10*i, 局数 + 10*i + 9]`。
  局数即 `FiveElementsClass[局]`（水二局=2 … 火六局=6）。
- 方向：阳男阴女（性别阴阳 === 生年支阴阳）**顺行** `idx = fixIndex(soulIndex + i)`；
  阴男阳女**逆行** `idx = fixIndex(soulIndex − i)`。`decadals[idx]` 存该宫大限。
- 大限干支 = 该宫位本身的干支（五虎遁推出，与 §4 一致）：`heavenlyStem =
  HEAVENLY_STEMS[fixIndex(TIGER_RULE[年干]索引 + idx, 10)]`，`earthlyBranch =
  EARTHLY_BRANCHES[fixIndex(2 + idx)]`。
- 年干支按 `yearDivide` 取。

---

## 13. 小限与流年（本命盘内数据）

### 13.1 小限（`astro/palace.ts:225-232` + `utils/index.ts:191` `getAgeIndex`）

小限起 1 虚岁的宫位（按生年支）：

| 年支组 | 寅午戌 | 申子辰 | 巳酉丑 | 亥卯未 |
|---|---|---|---|---|
| 起限宫 | 辰 | 戌 | 未 | 丑 |

第 i 个（i=0 起）小限宫的虚岁列表 `ages = [i+1, i+13, i+25, …, i+109]`（`12*j + i + 1, j=0..9`）。
**男顺行**：`ages[fixIndex(ageIdx + i)]`；**女逆行**：`ages[fixIndex(ageIdx − i)]`。
即每宫 `ages` 字段存有 10 个虚岁（1~109 中 ≡ 某值 mod 12 者）。

### 13.2 流年宫位映射

流年命宫 = 地支等于流年支的宫位：`yearlyIndex = fixEarthlyBranchIndex(流年支)`
（`FunctionalAstrolabe.ts:79`）。流年的十二宫名由 `getPalaceNames(yearlyIndex)` 重排。

---

## 14. 闰月与晚子时的精确行为

### 14.1 闰月修正 fixLeap（`utils/index.ts:125` `fixLunarMonthIndex`）

```
needToAdd = isLeap && fixLeap && lunarDay > 15 && timeIndex !== 12
月索引 = lunarMonth − 1 + (needToAdd ? 1 : 0)   （正月=0）
```

- `fixLeap=true`（默认）且生于闰月：闰月 15 日（含）前按当月算，16 日起按下月算。
- **timeIndex===12（晚子时）不做闰月修正**（`timeIndex !== 12` 条件）。
- 影响所有以月安星的星曜：命宫/身宫、左辅右弼、月系星、日系星（经 monthIndex）等。
- `byLunar` 的 `isLeapMonth` 只用于农历→阳历转换定位日期本身。

### 14.2 晚子时（timeIndex=12）行为汇总

1. `dayDivide==='forward'`（默认）：晚子时算来日——
   - 紫微定位用日 +1（`location.ts:60`，`d = lunarDay + 1`，超过当月天数则减月天数）；
   - 日干支按次日（lunar-typescript `getDayGanExact`，23 点归次日）；
   - 时干按次日日干起子时。
2. `dayDivide==='current'`：`bySolar` 入口处直接把 timeIndex 改为 0（`astro/astro.ts:184-187`），
   全部按当日早子时处理。
3. 不论哪种配置，**命身宫按时支=子（tIdx=0）计算**——即晚子时的命宫与同日早子时相同
   （`getSoulAndBody` 用的是时支索引而非 timeIndex）。
4. `fixLunarDayIndex`（`utils/index.ts:141`）：timeIndex≥12 时日偏移 = lunarDay（不减 1），
   否则 = lunarDay−1。影响三台、八座、恩光、天贵。
5. 时系星（文昌文曲、地空地劫、台辅、封诰、火铃顺加量）用 `fixIndex(timeIndex)`：
   晚子时 12 → 0，与早子时相同。

---

## 15. horoscope（运限）接口

`astrolabe.horoscope(date?, timeIndex?)`（`astro/FunctionalAstrolabe.ts:422` →
`_getHoroscopeBySolarDate`，:31-196）。返回 `FunctionalHoroscope`（toJSON 结构
`data/types/astro.ts:104` `Horoscope`）：

```
{
  solarDate, lunarDate,
  decadal: HoroscopeItem & { name: '大限'|'童限' },
  age:     HoroscopeItem & { nominalAge: number },      // 小限
  yearly:  HoroscopeItem & { yearlyDecStar: { jiangqian12[12], suiqian12[12] } },
  monthly: HoroscopeItem,
  daily:   HoroscopeItem,
  hourly:  HoroscopeItem
}

HoroscopeItem = {
  index: number,              // 运限命宫的本盘宫位索引
  name: string,
  heavenlyStem, earthlyBranch // 运限干支
  palaceNames: string[12],    // 以该运限命宫重排的十二宫名（getPalaceNames(index)）
  mutagen: string[4],         // 运限干四化星名数组 [禄,权,科,忌] 对应的星
  stars?: FunctionalStar[12][] // 流耀（见 15.3）；age 无 stars
}
```

### 15.1 虚岁与大限判定（`FunctionalAstrolabe.ts:48-118`）

- `nominalAge = 目标农历年 − 出生农历年`；`ageDivide==='normal'`（默认）再 +1；
  `'birthday'` 时仅当目标日期过了农历生日才 +1（判定式：同年同月且日更大，或
  `目标月 > 生月`——注意源码第二项**未比较年份**，跨年恒真，见 :56-62，如实实现）。
- 大限：找 `range` 包含 nominalAge 的宫；找不到（未起运）为**童限**，1~6 岁依次取
  `[命宫, 财帛, 疾厄, 夫妻, 福德, 官禄][nominalAge-1]` 所在宫（:106-118）。
- 小限：找 `ages` 包含 nominalAge 的宫（§13.1）。

### 15.2 流月/流日/流时索引（`FunctionalAstrolabe.ts:130-146`）

```
leapAddition      = 出生闰月且生日>15 ? 1 : 0
dateLeapAddition  = 目标闰月且目标日>15 ? 1 : 0
monthlyIndex = fixIndex( yearlyIndex − (生月 + leapAddition) + 出生时支索引 + (目标月 + dateLeapAddition) )
dailyIndex   = fixIndex( monthlyIndex + 目标农历日 − 1 )
hourlyIndex  = fixIndex( dailyIndex + 目标时支索引 )
```

（"出生时支索引"取 `rawDates.chineseDate.hourly[1]` 的地支索引 0~11；此处**直接用地支索引
参与宫位运算**，不减 2，照抄即可。）

### 15.3 流耀（`star/horoscopeStar.ts:21` `getHoroscopeStar`）

每个运限（decadal/yearly/monthly/daily/hourly）按**运限干支**重安 10 颗流耀，
规则与本命相同函数：魁钺=`getKuiYueIndex(干)`，昌曲=`getChangQuIndexByHeavenlyStem(干)`
（**注意流昌流曲用年干表而非时支表**，location.ts:864），禄羊陀马=`getLuYangTuoMaIndex(干,支)`，
鸾喜=`getLuanXiIndex(支)`。yearly 额外加年解（`getNianjieIndex(支)`）。

流昌流曲表（运限干 → 宫位地支）：

| 干 | 甲 | 乙 | 丙戊 | 丁己 | 庚 | 辛 | 壬 | 癸 |
|---|---|---|---|---|---|---|---|---|
| 流昌 | 巳 | 午 | 申 | 酉 | 亥 | 子 | 寅 | 卯 |
| 流曲 | 酉 | 申 | 午 | 巳 | 卯 | 寅 | 子 | 亥 |

流耀命名前缀（`horoscopeStar.ts:33-91`）：decadal=运X（运魁运钺运昌运曲运禄运羊运陀运马运鸾运喜），
yearly=流X，monthly=月X，daily=日X，hourly=时X。type 与本命对应星一致
（魁钺昌曲=soft，禄=lucun，羊陀=tough，马=tianma，鸾喜=flower）。

### 15.4 便捷列表（`FunctionalAstrolabe.ts:425,444,478`）

- `decadalList()`：12 宫按大限起运先后排序，每项 `{index, name, palaceName(本命宫名),
  ageRange, yearRange: [生年+起−1, 生年+止−1], heavenlyStem, earthlyBranch, palaceNames,
  mutagen, stars}`。
- `yearlyList(indexOrName)`：指定大限内 10 个虚岁的流年（每项加 `age, year`；内部以
  该年农历六月初一为目标日调 `horoscope()` 取 yearly）。
- `monthlyList(year, fixLeap=true)`：用 `lunar-typescript` 的 `LunarYear.getMonthsInYear()`
  枚举该年农历月；闰月且 fixLeap 时拆成 `{part:'first', dayRange:[1,15]}` 与
  `{part:'second', dayRange:[16,月末]}` 两项，故返回 12/13/14 项。每项
  `{index, name, age, year, month, isLeapMonth, part, dayRange, ...}`，目标日取该段第 1 天
  （second 段取 16 日）调 `horoscope()`。

---

## 附录 A. 星曜 key ↔ 中文名对照（zh-CN）

主星：ziweiMaj紫微 tianjiMaj天机 taiyangMaj太阳 wuquMaj武曲 tiantongMaj天同
lianzhenMaj廉贞 tianfuMaj天府 taiyinMaj太阴 tanlangMaj贪狼 jumenMaj巨门
tianxiangMaj天相 tianliangMaj天梁 qishaMaj七杀 pojunMaj破军。
辅星：zuofuMin左辅 youbiMin右弼 wenchangMin文昌 wenquMin文曲 lucunMin禄存
tianmaMin天马 qingyangMin擎羊 tuoluoMin陀罗 huoxingMin火星 lingxingMin铃星
tiankuiMin天魁 tianyueMin天钺 dikongMin地空 dijieMin地劫。
杂曜/神煞 key 见 `i18n/locales/zh-CN/star.ts`（含 changsheng12、boshi12、jiangqian12、
suiqian12 及运/流/月/日/时流耀全名）。

## 附录 B. 主要源码文件索引

| 文件 | 内容 |
|---|---|
| `astro/astro.ts` | bySolar/byLunar/withOptions/config、宫位与星盘组装 |
| `astro/palace.ts` | 命身宫、五行局、宫名、大限、小限 |
| `astro/FunctionalAstrolabe.ts` | horoscope()、decadalList/yearlyList/monthlyList |
| `astro/FunctionalHoroscope.ts` / `FunctionalPalace.ts` | 运限/宫位功能方法 |
| `star/location.ts` | 全部星曜索引算法 |
| `star/majorStar.ts` / `minorStar.ts` / `adjectiveStar.ts` / `decorativeStar.ts` / `horoscopeStar.ts` | 各类星安置 |
| `data/constants.ts` | 干支、宫位、时辰、五虎遁、五行局枚举 |
| `data/stars.ts` | 亮度表、四化名 |
| `data/heavenlyStems.ts` / `earthlyBranches.ts` | 天干四化表、地支属性/命主身主 |
| `utils/index.ts` | fixIndex 系列、闰月修正、小限起宫、亮度/四化取用 |
| `lunar-lite`（lib/ganzhi.js, convertor.js, misc.js） | 干支、阴阳历转换 |

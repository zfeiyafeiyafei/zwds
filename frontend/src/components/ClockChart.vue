<script setup lang="ts">
/**
 * 时钟圆盘布局（对应 display.available_themes 的 circular_equal_nodes）。
 *
 * 未来扩展预留（当前不实现）：
 * - 大限 / 流年等附加信息将以同心圆外环形式在 <g class="palace-ring"> 之外叠加新的环层；
 * - 环层转动（如流年旋转）通过对 <g class="palace-ring"> 施加 rotate transform 实现，
 *   因此 12 宫位节点全部归组于该 <g> 内；中心信息盘独立成 <g class="center-disc">，不随环转动。
 *
 * 几何参数（1280×860 视口整盘无滚动）：
 * - viewBox 780×780，12 个正圆节点半径 r=75，圆心等距落在 R=310 的圆周上（30° 均分）
 * - 运限徽标：三系徽标（大限/流年/小限）置于圆内最下方水平一行
 * - 不重叠约束：相邻中心距 2·R·sin15° ≈ 160.4，2r=150，缝隙 ≈10.4px ≥ 4px ✓
 * - 视口约束：总直径 2(R+r)=770 ≤ 780 ✓
 * - 节点内最长行（杂曜/小限）允许少量溢出圆边界（用户确认），不再为此缩字号
 */
import { computed } from 'vue'
import type { ChartResult, Horoscope, Palace, Star } from '../api'
import { hourLabel, lunarLabel, periodTags, relationEdges } from '../chartText'
import type { PeriodTag } from '../chartText'

const props = defineProps<{
  chart: ChartResult
  personName?: string
  selectedBranch?: string | null
  horoscope?: Horoscope | null
}>()

const emit = defineEmits<{
  select: [branch: string]
  'select-center': []
}>()

const CX = 390
const CY = 390
const RING_R = 310
const NODE_R = 75
const CENTER_R = 120

// 角度映射固定：午=正顶（12 点位，-90°），地支顺时针递增
// （酉=正右 3 点位 0°，子=正底 6 点位 90°，卯=正左 9 点位 180°）
const CLOCK_ORDER = ['午', '未', '申', '酉', '戌', '亥', '子', '丑', '寅', '卯', '辰', '巳']

const MUTAGEN_FILL: Record<string, string> = {
  禄: 'var(--badge-lu)',
  权: 'var(--badge-quan)',
  科: 'var(--badge-ke)',
  忌: 'var(--badge-ji)',
}

interface StarItem {
  star: Star
  x: number
  nameW: number
  brightW: number
  badgeW: number
}

/** 一行星曜的行内布局：整体居中，星名 + 亮度小字 + 四化圆标依次右排。 */
function layoutStarRow(stars: Star[], font: number, gap: number): StarItem[] {
  const items = stars.map((star) => ({
    star,
    x: 0,
    nameW: star.name.length * font,
    brightW: star.brightness ? font * 0.75 : 0,
    badgeW: star.mutagen ? font * 1.1 : 0,
  }))
  const total = items.reduce((acc, it) => acc + it.nameW + it.brightW + it.badgeW, 0) + gap * (items.length - 1)
  let cursor = -total / 2
  for (const it of items) {
    it.x = cursor
    cursor += it.nameW + it.brightW + it.badgeW + gap
  }
  return items
}

/** 杂曜行：通常一行；过宽时折成两行（仍须落在节点弦宽内）。 */
function adjLines(stars: Star[]): string[] {
  const names = stars.map((s) => s.name)
  if (names.length === 0) return []
  const one = names.join(' ')
  if (one.length * 8 <= 150 || names.length === 1) return [one]
  const mid = Math.ceil(names.length / 2)
  return [names.slice(0, mid).join(' '), names.slice(mid).join(' ')]
}

interface RingNode {
  palace: Palace
  x: number
  y: number
  badgeX: number
  majors: StarItem[]
  minors: StarItem[]
  adj: string[]
  footerY: number
  agesText: string
  pills: PillLayout[]
}

interface PillLayout {
  tag: PeriodTag
  cx: number
  cy: number
  w: number
}

/** 徽标宽度：CJK 按字宽 10、半角按 6 估，前后各留 4px 内边距。 */
function pillWidth(label: string): number {
  let w = 0
  for (const ch of label) w += /[\u2E80-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]/.test(ch) ? 10 : 6
  return w + 8
}

/**
 * 徽标布局：三系徽标（大限/流年/小限）置于圆内最下方，水平居中一行。
 * cy=48：徽标底边 56.5 处节点弦宽 ≈98.6px，三枚 2 字徽标 + 4px 间隙总宽 ~92px ✓
 */
function layoutPills(tags: PeriodTag[]): PillLayout[] {
  const widths = tags.map((t) => pillWidth(t.label))
  const gap = 4
  const total = widths.reduce((a, b) => a + b, 0) + gap * (tags.length - 1)
  let cursor = -total / 2
  return tags.map((tag, i) => {
    const cx = cursor + widths[i] / 2
    cursor += widths[i] + gap
    return { tag, cx, cy: 48, w: widths[i] }
  })
}

const nodes = computed<RingNode[]>(() =>
  props.chart.palaces.map((palace) => {
    const idx = CLOCK_ORDER.indexOf(palace.branch)
    const angle = ((-90 + idx * 30) * Math.PI) / 180
    const adj = adjLines(palace.adjective_stars)
    return {
      palace,
      x: CX + RING_R * Math.cos(angle),
      y: CY + RING_R * Math.sin(angle),
      // 宫名+干支合行整体居中：身宫徽标贴行尾（行宽 = 宫名×12 + 5 间隔 + 干支 2×10）
      badgeX: (palace.name.length * 12 + 5 + 20) / 2 + 8,
      majors: layoutStarRow(palace.major_stars, 14, 8),
      minors: layoutStarRow(palace.minor_stars, 9, 6),
      adj,
      footerY: adj.length > 1 ? 35 : 29,
      agesText: (palace.yearly_ages ?? palace.ages).join(','),
      pills: layoutPills(tagMap.value[palace.branch] ?? []),
    }
  }),
)

const tagMap = computed(() => periodTags(props.horoscope))

function mutagenFill(star: Star): string {
  return MUTAGEN_FILL[star.mutagen ?? ''] ?? 'var(--ink-faint)'
}

/** 三方四正虚线端点（节点圆心坐标；线段画在 palace-ring 之下，节点底色遮住线头）。 */
const relationSegs = computed(() => {
  const b = props.selectedBranch
  if (!b) return []
  const pos = new Map(nodes.value.map((n) => [n.palace.branch, n]))
  return relationEdges(b).flatMap(([from, to]) => {
    const p = pos.get(from)
    const q = pos.get(to)
    return p && q ? [{ x1: p.x, y1: p.y, x2: q.x, y2: q.y }] : []
  })
})

/** 当前运限摘要行（中心信息盘）。 */
const periodLine = computed(() => {
  const h = props.horoscope
  if (!h) return ''
  const dec = h.decadal
    ? `大限 ${h.decadal.branch}宫 ${h.decadal.age_start}~${h.decadal.age_end}`
    : '未上运'
  return `虚岁 ${h.nominal_age} · ${dec} · 流年 ${h.yearly.gan}${h.yearly.zhi}`
})

const infoLines = computed(() => {
  const c = props.chart
  return [
    ...(props.personName ? [`姓名 ${props.personName}`] : []),
    `性别 ${c.input.gender}`,
    `公历 ${c.input.solar_date} ${hourLabel(c.input.hour_index)}`,
    `农历 ${lunarLabel(c.calendar)}`,
    `四柱 ${c.calendar.ganzhi.year} ${c.calendar.ganzhi.month} ${c.calendar.ganzhi.day} ${c.calendar.ganzhi.hour}`,
    `五行局 ${c.meta.five_elements_class}`,
    `命主/身主 ${c.meta.soul} / ${c.meta.body}`,
    `生肖 ${c.calendar.zodiac}`,
    ...(periodLine.value ? [periodLine.value] : []),
  ]
})
</script>

<template>
  <svg class="clock-chart" viewBox="0 0 780 780" role="img" aria-label="紫微斗数时钟圆盘命盘">
    <g class="relation-lines">
      <line
        v-for="(seg, i) in relationSegs"
        :key="i"
        :x1="seg.x1"
        :y1="seg.y1"
        :x2="seg.x2"
        :y2="seg.y2"
      />
    </g>

    <g class="palace-ring">
      <g
        v-for="n in nodes"
        :key="n.palace.branch"
        class="palace-node"
        :transform="`translate(${n.x}, ${n.y})`"
        @click="emit('select', n.palace.branch)"
      >
        <circle
          :r="NODE_R"
          class="node-circle"
          :class="{ soul: n.palace.name === '命宫', selected: selectedBranch === n.palace.branch }"
        />
        <g v-for="(p, pi) in n.pills" :key="p.tag.label + pi" class="node-period">
          <rect
            :x="p.cx - p.w / 2"
            :y="p.cy - 8.5"
            :width="p.w"
            height="17"
            rx="8.5"
            class="period-pill"
            :class="[p.tag.kind, { filled: p.tag.filled }]"
          />
          <text
            :x="p.cx"
            :y="p.cy"
            text-anchor="middle"
            dominant-baseline="central"
            class="period-pill-text"
            :class="[p.tag.kind, { filled: p.tag.filled }]"
          >
            {{ p.tag.label }}
          </text>
        </g>

        <text y="-45" class="node-head">
          <tspan class="node-name" :class="{ bold: n.palace.name === '命宫' }">{{
            n.palace.name
          }}</tspan>
          <tspan class="node-ganzhi" dx="5">{{ n.palace.stem }}{{ n.palace.branch }}</tspan>
        </text>
        <g v-if="n.palace.is_body_palace" class="body-badge">
          <circle :cx="n.badgeX" cy="-49" r="6.5" />
          <text :x="n.badgeX" y="-49">{{ '身' }}</text>
        </g>

        <g transform="translate(0, -15)">
          <g v-for="it in n.majors" :key="it.star.name">
            <text :x="it.x" class="star-name" :class="{ ji: it.star.mutagen === '忌' }">
              {{ it.star.name }}
            </text>
            <text v-if="it.star.brightness" :x="it.x + it.nameW + 2" class="star-brightness">
              {{ it.star.brightness }}
            </text>
            <g v-if="it.star.mutagen">
              <circle
                :cx="it.x + it.nameW + it.brightW + 8"
                cy="-4.5"
                r="6.5"
                :fill="mutagenFill(it.star)"
              />
              <text :x="it.x + it.nameW + it.brightW + 8" y="-4.5" class="badge-text">
                {{ it.star.mutagen }}
              </text>
            </g>
          </g>
        </g>

        <g transform="translate(0, 0)">
          <g v-for="it in n.minors" :key="it.star.name">
            <text :x="it.x" class="minor-name">{{ it.star.name }}</text>
            <text v-if="it.star.brightness" :x="it.x + it.nameW + 1.5" class="minor-brightness">
              {{ it.star.brightness }}
            </text>
            <g v-if="it.star.mutagen">
              <circle
                :cx="it.x + it.nameW + it.brightW + 5.5"
                cy="-3"
                r="5"
                :fill="mutagenFill(it.star)"
              />
              <text :x="it.x + it.nameW + it.brightW + 5.5" y="-3" class="badge-text minor-badge">
                {{ it.star.mutagen }}
              </text>
            </g>
          </g>
        </g>

        <text
          v-for="(line, i) in n.adj"
          :key="line"
          :y="14 + i * 10"
          class="adj-line"
        >
          {{ line }}
        </text>

        <text :y="n.footerY" class="node-footer">
          <tspan class="ages">{{ n.agesText }}</tspan>
        </text>
        <!-- 大限年龄段独立一行：圆内最下方（三系徽标之下） -->
        <text y="68" class="decadal-line">
          {{ n.palace.decadal_range[0] }}~{{ n.palace.decadal_range[1] }}
        </text>
      </g>
    </g>

    <g class="center-disc clickable" @click="emit('select-center')">
      <circle :cx="CX" :cy="CY" :r="CENTER_R" class="center-circle" />
      <text :x="CX" :y="CY - 78" class="center-title">紫微斗数命盘</text>
      <text
        v-for="(line, i) in infoLines"
        :key="line"
        :x="CX"
        :y="CY - 54 + i * 16"
        class="center-line"
      >
        {{ line }}
      </text>
      <text :x="CX" :y="CY + 96" class="center-version">engine {{ chart.engine_version }}</text>
    </g>
  </svg>
</template>

<style scoped>
.clock-chart {
  display: block;
  width: 100%;
  /* 保持比例的同时钳制尺寸；viewBox 780×780（正方形，徽标已收进圆内） */
  max-width: calc(100vh - 132px);
  margin: 0 auto;
  height: auto;
  background: var(--paper);
  border: 1px solid var(--line-strong);
}

.relation-lines line {
  stroke: var(--vermilion);
  stroke-opacity: 0.5;
  stroke-width: 1.5;
  stroke-dasharray: 6 4;
}

.palace-node {
  cursor: pointer;
}

.node-circle {
  fill: var(--panel);
  stroke: var(--line-strong);
  stroke-width: 1;
}

.node-circle.soul {
  fill: #faf3e2;
}

.node-circle.selected {
  fill: #f6e9da;
  stroke: var(--vermilion);
  stroke-width: 1.5;
}

.node-head {
  text-anchor: middle;
}

.node-name {
  font-size: 12px;
  fill: var(--ink-soft);
}

.node-name.bold {
  font-weight: 700;
  fill: var(--ink);
}

.body-badge circle {
  fill: none;
  stroke: var(--accent);
  stroke-width: 1;
}

.body-badge text {
  font-size: 8px;
  fill: var(--accent);
  text-anchor: middle;
  dominant-baseline: central;
}

.node-ganzhi {
  font-size: 10px;
  font-weight: 600;
  fill: var(--ink);
}

.star-name {
  font-size: 14px;
  font-weight: 600;
  fill: var(--vermilion);
}

.star-name.ji {
  fill: var(--vermilion-deep);
}

.star-brightness {
  font-size: 9px;
  fill: var(--ink-faint);
}

.badge-text {
  font-size: 8px;
  fill: #fdfaf2;
  text-anchor: middle;
  dominant-baseline: central;
}

.minor-name {
  font-size: 9px;
  fill: var(--ink);
}

.minor-brightness {
  font-size: 7px;
  fill: var(--ink-faint);
}

.minor-badge {
  font-size: 7px;
}

.adj-line {
  font-size: 8px;
  fill: var(--ink-faint);
  text-anchor: middle;
}

.node-footer {
  text-anchor: middle;
}

.decadal-line {
  font-size: 8px;
  font-weight: 600;
  fill: var(--accent);
  text-anchor: middle;
}

/* 流年岁序独占页脚行：字号由 8px 增至 9.5px（最长 30 字符 ≈128px，节点弦宽 132px 可容） */
.ages {
  font-size: 9.5px;
  fill: var(--ink-faint);
}

.center-disc {
  cursor: default;
}

.center-disc.clickable {
  cursor: pointer;
}

.center-circle {
  fill: var(--panel);
  stroke: var(--line-strong);
  stroke-width: 1;
}

.center-title {
  font-size: 16px;
  letter-spacing: 4px;
  fill: var(--ink);
  text-anchor: middle;
}

.center-line {
  font-size: 11px;
  fill: var(--ink);
  text-anchor: middle;
}

.center-version {
  font-size: 9px;
  fill: var(--ink-faint);
  text-anchor: middle;
}
.period-pill {
  fill: var(--panel);
  stroke-width: 1.2;
}

.period-pill.decadal {
  stroke: var(--accent);
}

.period-pill.yearly {
  stroke: var(--vermilion);
}

.period-pill.xiaoxian {
  stroke: var(--badge-quan);
}

.period-pill-text {
  font-size: 10px;
}

.period-pill-text.decadal {
  fill: var(--accent);
}

.period-pill-text.yearly {
  fill: var(--vermilion);
}

.period-pill-text.xiaoxian {
  fill: var(--badge-quan);
}

/* 运限十二宫实心徽标：三系各自成色（大限绿 / 流年红 / 小限紫） */
.period-pill.filled.decadal {
  fill: var(--accent);
  stroke: var(--accent);
}

.period-pill.filled.yearly {
  fill: var(--vermilion);
  stroke: var(--vermilion);
}

.period-pill.filled.xiaoxian {
  fill: var(--badge-quan);
  stroke: var(--badge-quan);
}

.period-pill-text.filled {
  fill: #f8f5ec;
}
</style>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { ChartResult, Horoscope, Palace } from '../api'
import { hourLabel, lunarLabel, periodTags, relationEdges } from '../chartText'
import PalaceCell from './PalaceCell.vue'

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

/** 传统宫格：地支 → [row, col]（0 起）。中央 2×2 为命盘信息。 */
const GRID_POS: Record<string, [number, number]> = {
  巳: [0, 0],
  午: [0, 1],
  未: [0, 2],
  申: [0, 3],
  辰: [1, 0],
  酉: [1, 3],
  卯: [2, 0],
  戌: [2, 3],
  寅: [3, 0],
  丑: [3, 1],
  子: [3, 2],
  亥: [3, 3],
}

const cells = computed(() =>
  props.chart.palaces.map((palace: Palace) => ({
    palace,
    pos: GRID_POS[palace.branch] ?? [0, 0],
  })),
)

/** 地支 → 运限标签（大限/流年/小限）。 */
const tagMap = computed(() => periodTags(props.horoscope))

const lunarText = computed(() => lunarLabel(props.chart.calendar))

const hourText = computed(() => hourLabel(props.chart.input.hour_index))

/** 三方四正 overlay：以各 cell DOM 中心为端点，容器相对坐标。 */
interface Point {
  x: number
  y: number
}

const gridRef = ref<HTMLElement>()
const gridSize = ref<Point>({ x: 0, y: 0 })
const centers = ref<Record<string, Point>>({})

function measure() {
  const el = gridRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  gridSize.value = { x: rect.width, y: rect.height }
  const map: Record<string, Point> = {}
  for (const cell of el.querySelectorAll('.palace')) {
    const branch = cell.getAttribute('data-branch')
    if (!branch) continue
    const r = cell.getBoundingClientRect()
    map[branch] = { x: r.left - rect.left + r.width / 2, y: r.top - rect.top + r.height / 2 }
  }
  centers.value = map
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  measure()
  resizeObserver = new ResizeObserver(measure)
  if (gridRef.value) resizeObserver.observe(gridRef.value)
})

onBeforeUnmount(() => resizeObserver?.disconnect())

watch(
  () => props.chart,
  () => nextTick(measure),
)

const lineSegments = computed(() => {
  const b = props.selectedBranch
  if (!b) return []
  return relationEdges(b).flatMap(([from, to]) => {
    const p = centers.value[from]
    const q = centers.value[to]
    return p && q ? [{ x1: p.x, y1: p.y, x2: q.x, y2: q.y }] : []
  })
})
</script>

<template>
  <div class="chart-grid" ref="gridRef">
    <svg
      v-if="lineSegments.length"
      class="relation-overlay"
      :viewBox="`0 0 ${gridSize.x} ${gridSize.y}`"
      preserveAspectRatio="none"
    >
      <line
        v-for="(seg, i) in lineSegments"
        :key="i"
        :x1="seg.x1"
        :y1="seg.y1"
        :x2="seg.x2"
        :y2="seg.y2"
      />
    </svg>

    <PalaceCell
      v-for="cell in cells"
      :key="cell.palace.branch"
      :palace="cell.palace"
      :selected="selectedBranch === cell.palace.branch"
      :tags="tagMap[cell.palace.branch] ?? []"
      :style="{ gridRow: cell.pos[0] + 1, gridColumn: cell.pos[1] + 1 }"
      @select="emit('select', $event)"
    />

    <div class="center-panel clickable" @click="emit('select-center')">
      <h1 class="center-title">紫微斗数命盘</h1>
      <dl class="center-info">
        <div v-if="personName">
          <dt>姓名</dt>
          <dd>{{ personName }}</dd>
        </div>
        <div>
          <dt>性别</dt>
          <dd>{{ chart.input.gender }}</dd>
        </div>
        <div>
          <dt>公历</dt>
          <dd>{{ chart.input.solar_date }} {{ hourText }}</dd>
        </div>
        <div>
          <dt>农历</dt>
          <dd>{{ lunarText }}</dd>
        </div>
        <div>
          <dt>四柱</dt>
          <dd>
            {{ chart.calendar.ganzhi.year }} {{ chart.calendar.ganzhi.month }}
            {{ chart.calendar.ganzhi.day }} {{ chart.calendar.ganzhi.hour }}
          </dd>
        </div>
        <div>
          <dt>五行局</dt>
          <dd>{{ chart.meta.five_elements_class }}</dd>
        </div>
        <div>
          <dt>命主 / 身主</dt>
          <dd>{{ chart.meta.soul }} / {{ chart.meta.body }}</dd>
        </div>
        <div>
          <dt>生肖</dt>
          <dd>{{ chart.calendar.zodiac }}</dd>
        </div>
      </dl>
      <p class="center-version">engine {{ chart.engine_version }}</p>
    </div>
  </div>
</template>

<style scoped>
.chart-grid {
  position: relative;
  display: grid;
  /* 容器取视口允许范围内的最大正方形：4×4 等分轨道，宫位单元格恒为正方形 */
  width: 100%;
  max-width: calc(100vh - 96px);
  aspect-ratio: 1 / 1;
  margin-inline: auto;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-template-rows: repeat(4, minmax(0, 1fr));
  gap: 0;
  border: 1px solid var(--line-strong);
  background: var(--line);
  grid-auto-flow: dense;
}

.relation-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 2;
}

.relation-overlay line {
  stroke: var(--vermilion);
  stroke-opacity: 0.5;
  stroke-width: 1.5;
  stroke-dasharray: 6 4;
}

.chart-grid > :deep(.palace) {
  outline: 1px solid var(--line);
  overflow: hidden;
}

.chart-grid > :deep(.palace.selected) {
  outline: 1.5px solid var(--vermilion);
  outline-offset: -1.5px;
  background: #f6e9da;
}

.center-panel {
  grid-row: 2 / 4;
  grid-column: 2 / 4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px;
  background: var(--panel);
  outline: 1px solid var(--line);
}

.center-panel.clickable {
  cursor: pointer;
}

.center-title {
  margin: 0;
  font-size: 20px;
  letter-spacing: 0.4em;
  text-indent: 0.4em;
  color: var(--ink);
}

.center-info {
  margin: 0;
  display: grid;
  grid-template-columns: auto auto;
  gap: 3px 14px;
  font-size: 13px;
}

.center-info div {
  display: contents;
}

.center-info dt {
  color: var(--ink-faint);
  text-align: right;
}

.center-info dd {
  margin: 0;
  color: var(--ink);
}

.center-version {
  margin: 0;
  font-size: 10px;
  color: var(--ink-faint);
}
</style>

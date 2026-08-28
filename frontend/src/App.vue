<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import {
  calculate,
  copyChartJson,
  deleteChart,
  exportChart,
  getChart,
  importChart,
  listCharts,
} from './api'
import type { BirthPayload, ChartResult, ChartSummary } from './api'
import BirthForm from './components/BirthForm.vue'
import ChartGrid from './components/ChartGrid.vue'
import ClockChart from './components/ClockChart.vue'
import EditChartDialog from './components/EditChartDialog.vue'
import PatternPanel from './components/PatternPanel.vue'
import { shortHourLabel } from './hours'

type LayoutKey = 'grid' | 'clock'

const LAYOUT_STORAGE_KEY = 'ziwei.layout'

const layout = ref<LayoutKey>(
  localStorage.getItem(LAYOUT_STORAGE_KEY) === 'clock' ? 'clock' : 'grid',
)
watch(layout, (v) => localStorage.setItem(LAYOUT_STORAGE_KEY, v))

const formRef = ref<InstanceType<typeof BirthForm>>()
const chart = ref<ChartResult | null>(null)
const personName = ref('')
const saved = ref<ChartSummary[]>([])
const listError = ref('')
const selectedBranch = ref<string | null>(null)

// 当前展示的已保存命盘 id（null = 来自临时排盘）
const currentChartId = ref<number | null>(null)
// 编辑中的命盘（非 null 时显示编辑对话框）
const editingItem = ref<ChartSummary | null>(null)

// ---- 运限定位（biz_requirement.md §4.1.2-4）：默认今天，可切日期重算 ----
const todayISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const targetDate = ref(todayISO())
const lastPayload = ref<BirthPayload | null>(null)
const periodBusy = ref(false)

/** ‹ › 步进一年（保持月日；闰日由浏览器归一为 3-01）。 */
function shiftTargetDate(years: number) {
  const d = new Date(`${targetDate.value}T12:00:00`)
  d.setFullYear(d.getFullYear() + years)
  targetDate.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function recalcHoroscope() {
  if (!lastPayload.value) return
  periodBusy.value = true
  try {
    chart.value = await calculate({ ...lastPayload.value, target_date: targetDate.value })
  } finally {
    periodBusy.value = false
  }
}

watch(targetDate, recalcHoroscope)

/** 三方四正联动：点其他宫换选，再点同一宫取消。 */
function onSelectPalace(branch: string) {
  selectedBranch.value = selectedBranch.value === branch ? null : branch
}

function onCalculated(result: ChartResult, name: string, payload: BirthPayload) {
  chart.value = result
  personName.value = name
  lastPayload.value = payload
  currentChartId.value = null
}

async function refreshList() {
  try {
    saved.value = await listCharts()
    listError.value = ''
  } catch (e) {
    listError.value = e instanceof Error ? e.message : String(e)
  }
}

async function onExport(item: ChartSummary) {
  try {
    await exportChart(item.chart_id, item.person)
  } catch (e) {
    listError.value = e instanceof Error ? e.message : String(e)
  }
}

const importInput = ref<HTMLInputElement>()

async function onImportFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许重复选择同一文件
  if (!file) return
  try {
    const snapshot = JSON.parse(await file.text())
    await importChart(snapshot, file.name.replace(/\.json$/i, '').replace(/^ziwei_/, ''))
    await refreshList()
  } catch (err) {
    listError.value = err instanceof Error ? err.message : String(err)
  }
}

async function loadSaved(item: ChartSummary) {
  try {
    chart.value = await getChart(item.chart_id)
    personName.value = item.person
    currentChartId.value = item.chart_id
    // 快照不含运限区块：按同一出生参数补一次当前日期的运限定位
    lastPayload.value = {
      solar_date: chart.value.input.solar_date,
      hour_index: chart.value.input.hour_index,
      gender: chart.value.input.gender,
    }
    await recalcHoroscope()
  } catch (e) {
    listError.value = e instanceof Error ? e.message : String(e)
  }
}

/** 编辑保存成功后：刷新列表；若编辑的是当前展示命盘则同步重载。 */
async function onEdited(chartId: number) {
  await refreshList()
  const item = saved.value.find((x) => x.chart_id === chartId)
  if (currentChartId.value === chartId && item) await loadSaved(item)
}

async function onDelete(item: ChartSummary) {
  if (!window.confirm(`确定删除「${item.person}」（${item.solar_datetime ?? ''}）的命盘吗？`)) return
  try {
    await deleteChart(item.chart_id)
    if (currentChartId.value === item.chart_id) {
      currentChartId.value = null
      chart.value = null
    }
    await refreshList()
  } catch (e) {
    listError.value = e instanceof Error ? e.message : String(e)
  }
}

// ---- 复制当前命盘 JSON 到剪贴板 ----
const copyHint = ref('')
let copyTimer: ReturnType<typeof setTimeout> | undefined

async function onCopyJson() {
  if (!chart.value) return
  try {
    await copyChartJson(chart.value)
    copyHint.value = '已复制'
  } catch (e) {
    copyHint.value = e instanceof Error ? e.message : String(e)
  } finally {
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => (copyHint.value = ''), 2000)
  }
}

onMounted(async () => {
  // 默认示例盘：1990-05-15 午时 男
  formRef.value?.onCalculate()
  await refreshList()
})
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <BirthForm ref="formRef" @calculated="onCalculated" @saved="refreshList" />

      <section class="saved-panel">
        <div class="saved-head">
          <h2 class="saved-title">已保存命盘</h2>
          <button type="button" class="import-btn" @click="importInput?.click()">导入 JSON</button>
          <input
            ref="importInput"
            type="file"
            accept=".json,application/json"
            hidden
            @change="onImportFile"
          />
        </div>
        <p v-if="listError" class="saved-error">{{ listError }}</p>
        <p v-else-if="saved.length === 0" class="saved-empty">暂无保存记录，填好生辰后点「保存」。</p>
        <ul v-else class="saved-list">
          <li v-for="item in saved" :key="item.chart_id" class="saved-row">
            <button type="button" class="saved-item" @click="loadSaved(item)">
              <span class="saved-person">{{ item.person }}</span>
              <span class="saved-meta">
                {{ item.solar_datetime?.slice(0, 10) ?? ''
                }}<template v-if="item.hour_index != null">
                  · {{ shortHourLabel(item.hour_index) }}</template
                >
                · {{ item.gender }}
              </span>
            </button>
            <button
              type="button"
              class="row-btn"
              title="编辑（姓名 / 出生信息）"
              @click.stop="editingItem = item"
            >
              ✎
            </button>
            <button
              type="button"
              class="row-btn"
              title="删除命盘"
              @click.stop="onDelete(item)"
            >
              ✕
            </button>
            <button
              type="button"
              class="row-btn"
              title="导出 JSON 文件"
              @click.stop="onExport(item)"
            >
              ⇩
            </button>
          </li>
        </ul>
      </section>

      <EditChartDialog :item="editingItem" @close="editingItem = null" @saved="onEdited" />
    </aside>

    <main class="content">
      <div class="toolbar">
        <div class="layout-switch" role="group" aria-label="命盘布局">
        <button
          type="button"
          :class="{ active: layout === 'grid' }"
          :aria-pressed="layout === 'grid'"
          @click="layout = 'grid'"
        >
          传统宫格
        </button>
        <button
          type="button"
          :class="{ active: layout === 'clock' }"
          :aria-pressed="layout === 'clock'"
          @click="layout = 'clock'"
        >
          时钟圆盘
        </button>
      </div>
        <div class="toolbar-right">
          <div class="period-nav" role="group" aria-label="运限日期">
            <button type="button" title="上一年" @click="shiftTargetDate(-1)">‹</button>
            <input v-model="targetDate" type="date" aria-label="运限目标日期" />
            <button type="button" title="下一年" @click="shiftTargetDate(1)">›</button>
            <span v-if="chart?.horoscope" class="age-chip">
              虚岁 {{ chart.horoscope.nominal_age
              }}<template v-if="chart.horoscope.decadal">
                · 大限 {{ chart.horoscope.decadal.age_start }}~{{ chart.horoscope.decadal.age_end }}</template
              >
            </span>
            <span v-if="periodBusy" class="period-busy">定位中…</span>
          </div>
          <button v-if="chart" type="button" class="copy-btn" @click="onCopyJson">
            {{ copyHint || '复制 JSON' }}
          </button>
        </div>
      </div>

      <template v-if="chart">
        <ChartGrid
          v-if="layout === 'grid'"
          :chart="chart"
          :person-name="personName"
          :selected-branch="selectedBranch"
          :horoscope="chart.horoscope"
          @select="onSelectPalace"
        />
        <ClockChart
          v-else
          :chart="chart"
          :person-name="personName"
          :selected-branch="selectedBranch"
          :horoscope="chart.horoscope"
          @select="onSelectPalace"
        />
      </template>
      <p v-else class="loading">排盘中…</p>
      <PatternPanel v-if="chart?.analysis" :patterns="chart.analysis.patterns" />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
  padding: 16px;
  align-items: start;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 16px;
}

.saved-panel {
  padding: 16px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.saved-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.saved-title {
  margin: 0;
  font-size: 14px;
  letter-spacing: 0.2em;
}

.import-btn {
  padding: 3px 10px;
  font-size: 12px;
  color: var(--ink-soft);
  background: transparent;
  border: 1px dashed var(--line-strong);
  border-radius: 4px;
}

.import-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.saved-row {
  display: flex;
  gap: 2px;
}

.row-btn {
  flex: none;
  width: 26px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: var(--ink-faint);
  font-size: 13px;
}

.row-btn:hover {
  background: #f2ecdc;
  border-color: var(--line);
  color: var(--accent);
}

.saved-empty {
  margin: 0;
  font-size: 12px;
  color: var(--ink-faint);
}

.saved-error {
  margin: 0;
  font-size: 12px;
  color: var(--vermilion-deep);
}

.saved-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 40vh;
  overflow-y: auto;
}

.saved-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 6px 8px;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
}

.saved-item:hover {
  background: #f2ecdc;
  border-color: var(--line);
}

.saved-item:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.saved-person {
  font-size: 13px;
  color: var(--ink);
}

.saved-meta {
  font-size: 11px;
  color: var(--ink-faint);
}

.content {
  min-width: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  /* 页面滚动时保持可见（布局切换 / 运限日期 / 复制按钮都在这里） */
  position: sticky;
  top: 0;
  z-index: 5;
  padding: 8px 0;
  margin-top: -8px;
  background: var(--paper);
}

.layout-switch {
  display: inline-flex;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  overflow: hidden;
  background: var(--panel);
}

.layout-switch button {
  padding: 6px 18px;
  border: none;
  background: transparent;
  color: var(--ink-soft);
  font-size: 13px;
}

.layout-switch button + button {
  border-left: 1px solid var(--line);
}

.layout-switch button.active {
  background: var(--accent);
  color: #f8f5ec;
}

.layout-switch button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.toolbar-right {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.copy-btn {
  padding: 5px 12px;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: var(--panel);
  color: var(--ink-soft);
  font-size: 12px;
  white-space: nowrap;
}

.copy-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: #f2ecdc;
}

.period-nav {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.period-nav button {
  padding: 4px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: var(--panel);
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.2;
}

.period-nav button:hover {
  background: #f2ecdc;
}

.period-nav input[type='date'] {
  padding: 4px 6px;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: var(--panel);
  font-size: 13px;
}

.age-chip {
  margin-left: 4px;
  font-size: 12px;
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 999px;
  padding: 2px 10px;
  white-space: nowrap;
}

.period-busy {
  font-size: 12px;
  color: var(--ink-faint);
}

.loading {
  color: var(--ink-faint);
  padding: 32px;
  text-align: center;
}
</style>

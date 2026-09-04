<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import {
  calculate,
  copyChartJson,
  deleteChart,
  exportAllCharts,
  exportChart,
  getChart,
  importChart,
  listCharts,
} from './api'
import type { BirthPayload, ChartResult, ChartSummary } from './api'
import BirthForm from './components/BirthForm.vue'
import ChartGrid from './components/ChartGrid.vue'
import ClockChart from './components/ClockChart.vue'
import DateField from './components/DateField.vue'
import EditChartDialog from './components/EditChartDialog.vue'
import ManageChartsDialog from './components/ManageChartsDialog.vue'
import PatternPanel from './components/PatternPanel.vue'
import SavedChartsPanel from './components/SavedChartsPanel.vue'
import StarDetail from './components/StarDetail.vue'

type LayoutKey = 'grid' | 'clock'

const LAYOUT_STORAGE_KEY = 'ziwei.layout'

const layout = ref<LayoutKey>(
  localStorage.getItem(LAYOUT_STORAGE_KEY) === 'clock' ? 'clock' : 'grid',
)
watch(layout, (v) => localStorage.setItem(LAYOUT_STORAGE_KEY, v))
// ---- 主题切换：localStorage 持久化，未选择时跟随系统 ----
type ThemeKey = 'light' | 'dark'
const THEME_STORAGE_KEY = 'zwds-theme'

const storedTheme = localStorage.getItem(THEME_STORAGE_KEY)
const theme = ref<ThemeKey>(
  storedTheme === 'dark' || storedTheme === 'light'
    ? storedTheme
    : window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light',
)

function applyTheme(v: ThemeKey) {
  document.documentElement.dataset.theme = v
}
applyTheme(theme.value)

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem(THEME_STORAGE_KEY, theme.value)
  applyTheme(theme.value)
}

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
// 命盘管理对话框开关
const manageOpen = ref(false)

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

/** 三方四正联动：点其他宫换选，再点同一宫取消；右侧解析栏跟随选中宫。 */
const detailBranch = ref<string | null>(null)
const detailCenter = ref(false)

function onSelectPalace(branch: string) {
  selectedBranch.value = selectedBranch.value === branch ? null : branch
  detailBranch.value = branch
  detailCenter.value = false
}

function onSelectCenter() {
  detailCenter.value = true
  detailBranch.value = null
}

/** 新盘默认在右侧展示命宫解析。 */
function focusSoulPalace() {
  detailBranch.value = chart.value?.meta.soul_palace_branch ?? null
  detailCenter.value = false
}

function onCalculated(result: ChartResult, name: string, payload: BirthPayload) {
  chart.value = result
  personName.value = name
  lastPayload.value = payload
  currentChartId.value = null
  focusSoulPalace()
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

/** 导出全部命盘为单个 JSON 文件（备份/迁移）。 */
async function onExportAll() {
  try {
    await exportAllCharts()
  } catch (e) {
    listError.value = e instanceof Error ? e.message : String(e)
  }
}

async function onImportFile(file: File) {
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
    focusSoulPalace()
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

/** 管理对话框中双击/回车记录：加载命盘并收起对话框。 */
async function onManageSelect(item: ChartSummary) {
  manageOpen.value = false
  await loadSaved(item)
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
      <SavedChartsPanel
        :items="saved"
        :error="listError"
        @select="loadSaved"
        @manage="manageOpen = true"
        @import-file="onImportFile"
      />

      <BirthForm ref="formRef" @calculated="onCalculated" @saved="refreshList" />

      <ManageChartsDialog
        :open="manageOpen"
        :items="saved"
        @close="manageOpen = false"
        @select="onManageSelect"
        @edit="editingItem = $event"
        @remove="onDelete"
        @export="onExport"
        @export-all="onExportAll"
      />

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
            <DateField v-model="targetDate" />
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
          <button
            type="button"
            class="theme-toggle"
            :title="theme === 'dark' ? '切换为浅色主题' : '切换为深色主题'"
            :aria-label="theme === 'dark' ? '切换为浅色主题' : '切换为深色主题'"
            @click="toggleTheme"
          >
            {{ theme === 'dark' ? '☀' : '☾' }}
          </button>
        </div>
      </div>

      <div class="main-row">
        <PatternPanel v-if="chart?.analysis" :patterns="chart.analysis.patterns" />
        <div class="chart-col">
          <template v-if="chart">
            <ChartGrid
              v-if="layout === 'grid'"
              :chart="chart"
              :person-name="personName"
              :selected-branch="selectedBranch"
              :horoscope="chart.horoscope"
              @select="onSelectPalace"
              @select-center="onSelectCenter"
            />
            <ClockChart
              v-else
              :chart="chart"
              :person-name="personName"
              :selected-branch="selectedBranch"
              :horoscope="chart.horoscope"
              @select="onSelectPalace"
              @select-center="onSelectCenter"
            />
          </template>
          <p v-else class="loading">排盘中…</p>
        </div>
        <StarDetail
          v-if="chart?.analysis"
          :analysis="chart.analysis"
          :branch="detailBranch"
          :center="detailCenter"
        />
      </div>
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

/* 命盘区 + 右侧星曜解析栏 */
.main-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-top: 12px;
}

.chart-col {
  flex: 1;
  min-width: 0;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 16px;
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
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--panel);
  box-shadow: var(--shadow-sm);
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
  color: var(--on-accent);
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
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--ink-soft);
  font-size: 12px;
  white-space: nowrap;
}

.copy-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--hover-bg);
}

.period-nav {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.period-nav button {
  padding: 4px 10px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.2;
}

.period-nav button:hover {
  background: var(--hover-bg);
}

.period-nav .date-field {
  width: 148px;
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
.theme-toggle {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1;
}

.theme-toggle:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--hover-bg);
}

.theme-toggle:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--ring);
}

.loading {
  color: var(--ink-faint);
  padding: 32px;
  text-align: center;
}
</style>

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
import AIChat from './components/AIChat.vue'
import AISettingsDialog from './components/AISettingsDialog.vue'
import BirthForm from './components/BirthForm.vue'
import ChartGrid from './components/ChartGrid.vue'
import ClockChart from './components/ClockChart.vue'
import DateField from './components/DateField.vue'
import EditChartDialog from './components/EditChartDialog.vue'
import InsightPanel from './components/InsightPanel.vue'
import ManageChartsDialog from './components/ManageChartsDialog.vue'
import NavRail from './components/NavRail.vue'
import SavedChartsPanel from './components/SavedChartsPanel.vue'

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

// ---- 一级视图（导航栏驱动，ui_design.md §3.1） ----
type ViewKey = 'chart' | 'ai'
const view = ref<ViewKey>('chart')
const settingsOpen = ref(false)
const aiChatRef = ref<InstanceType<typeof AIChat>>()
// 排盘表单抽屉（§4.1：低频操作收纳）
const formOpen = ref(false)
// 窄屏抽屉：<1280 洞察栏抽屉化，<900 数据栏抽屉化（§4.3/§4.4）
const insightOpen = ref(false)
const dataOpen = ref(false)

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

/** 三方四正联动：点其他宫换选，再点同一宫取消；洞察栏星曜 tab 跟随选中宫。 */
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

/** 新盘默认展示命宫解析。 */
function focusSoulPalace() {
  detailBranch.value = chart.value?.meta.soul_palace_branch ?? null
  detailCenter.value = false
}

function onCalculated(result: ChartResult, name: string, payload: BirthPayload) {
  chart.value = result
  personName.value = name
  lastPayload.value = payload
  currentChartId.value = null
  formOpen.value = false
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
  <div class="app">
    <NavRail
      :view="view"
      :theme="theme"
      @select="view = $event"
      @toggle-theme="toggleTheme"
      @open-settings="settingsOpen = true"
    />

    <!-- 数据栏：命盘检索 + 新建入口（排盘表单收进抽屉，ui_design.md §4.1） -->
    <aside v-show="view === 'chart'" class="data-col" :class="{ open: dataOpen }">
      <SavedChartsPanel
        :items="saved"
        :error="listError"
        @select="loadSaved"
        @manage="manageOpen = true"
        @import-file="onImportFile"
      />
      <button type="button" class="btn btn-primary new-chart-btn" @click="formOpen = true">
        ＋ 新建命盘
      </button>
    </aside>

    <!-- 排盘表单抽屉：常驻挂载（onMounted 默认排盘依赖 formRef），v-show 控制显隐 -->
    <div v-show="formOpen" class="drawer-mask" @click.self="formOpen = false">
      <div class="form-drawer" role="dialog" aria-label="新建命盘">
        <div class="drawer-head">
          <h2 class="drawer-title">新建命盘</h2>
          <button type="button" class="btn btn-icon" title="关闭" @click="formOpen = false">✕</button>
        </div>
        <BirthForm
          ref="formRef"
          @calculated="onCalculated"
          @saved="(formOpen = false), refreshList()"
        />
      </div>
    </div>

    <main class="workspace">
      <div v-show="view === 'chart'" class="chart-view">
        <section class="chart-card">
          <header class="card-head">
            <div class="card-title">
              <strong>{{ personName || '未命名' }}</strong>
              <span v-if="chart" class="card-meta">
                {{ chart.input.solar_date }} · {{ chart.input.gender }}
              </span>
            </div>
            <div class="card-actions">
              <div class="period-nav" role="group" aria-label="运限日期">
                <button type="button" class="btn btn-icon" title="上一年" @click="shiftTargetDate(-1)">‹</button>
                <DateField v-model="targetDate" />
                <button type="button" class="btn btn-icon" title="下一年" @click="shiftTargetDate(1)">›</button>
                <span v-if="chart?.horoscope" class="age-chip">
                  虚岁 {{ chart.horoscope.nominal_age
                  }}<template v-if="chart.horoscope.decadal">
                    · 大限 {{ chart.horoscope.decadal.age_start }}~{{ chart.horoscope.decadal.age_end }}</template
                  >
                </span>
                <span v-if="periodBusy" class="period-busy">定位中…</span>
              </div>
              <div class="layout-toggle" role="group" aria-label="命盘布局">
                <button
                  type="button"
                  class="btn btn-icon"
                  :class="{ active: layout === 'grid' }"
                  title="传统宫格"
                  :aria-pressed="layout === 'grid'"
                  @click="layout = 'grid'"
                >
                  ▦
                </button>
                <button
                  type="button"
                  class="btn btn-icon"
                  :class="{ active: layout === 'clock' }"
                  title="时钟圆盘"
                  :aria-pressed="layout === 'clock'"
                  @click="layout = 'clock'"
                >
                  ◔
                </button>
              </div>
              <button v-if="chart" type="button" class="btn" @click="onCopyJson">
                {{ copyHint || '复制 JSON' }}
              </button>
              <button
                type="button"
                class="btn insight-toggle"
                @click="insightOpen = !insightOpen"
              >
                洞察
              </button>
              <button
                type="button"
                class="btn btn-icon data-toggle"
                title="命盘列表"
                @click="dataOpen = !dataOpen"
              >
                ☰
              </button>
            </div>
          </header>
          <div class="chart-canvas">
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
        </section>

        <!-- 洞察栏：宽屏常驻右栏，窄屏右侧抽屉 -->
        <InsightPanel
          v-if="chart?.analysis"
          class="insight-col"
          :class="{ open: insightOpen }"
          :patterns="chart.analysis.patterns"
          :analysis="chart.analysis"
          :branch="detailBranch"
          :center="detailCenter"
        />
        <div v-if="insightOpen" class="drawer-mask insight-mask" @click="insightOpen = false"></div>
      </div>

      <!-- v-show 而非 v-if：切换视图不卸载组件，对话状态保留 -->
      <AIChat
        v-show="view === 'ai'"
        ref="aiChatRef"
        :chart="chart"
        :person-name="personName"
        @open-settings="settingsOpen = true"
      />
    </main>

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

    <AISettingsDialog
      :open="settingsOpen"
      @close="settingsOpen = false"
      @changed="aiChatRef?.reloadSkills()"
    />
  </div>
</template>

<style scoped>
.app {
  display: grid;
  grid-template-columns: 64px auto 1fr;
  min-height: 100vh;
}

.workspace {
  min-width: 0;
  padding: 16px;
}

/* ---- 排盘工作台：数据栏 + 命盘卡片 + 洞察栏 ---- */
.chart-view {
  display: flex;
  gap: 16px;
  align-items: stretch;
}

.data-col {
  position: sticky;
  top: 0;
  width: 296px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 0 16px 16px;
  max-height: 100vh;
  box-sizing: border-box;
}

.chart-card {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  /* 页面滚动时保持可见（运限导航 / 布局 / 导出都在这里） */
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--panel);
  border-radius: var(--radius) var(--radius) 0 0;
}

.card-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 14px;
}

.card-meta {
  font-size: 12px;
  color: var(--ink-faint);
}

.card-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.chart-canvas {
  padding: 12px;
}

.insight-col {
  width: 360px;
  flex-shrink: 0;
  max-height: calc(100vh - 32px);
  position: sticky;
  top: 16px;
}

.new-chart-btn {
  width: 100%;
}

/* ---- 抽屉通用 ---- */
.drawer-mask {
  position: fixed;
  inset: 0;
  background: var(--mask);
  z-index: 40;
}

.form-drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: min(320px, 92vw);
  background: var(--paper);
  border-right: 1px solid var(--line);
  padding: 16px;
  overflow-y: auto;
  z-index: 41;
}

.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.drawer-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.period-nav {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.period-nav .date-field {
  width: 148px;
}

.age-chip {
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

.layout-toggle {
  display: inline-flex;
  gap: 4px;
}

.insight-toggle,
.data-toggle {
  display: none;
}

.loading {
  color: var(--ink-faint);
  padding: 32px;
  text-align: center;
}

/* ---- 断点体系（ui_design.md §4.2-4.4） ---- */

/* 中屏：洞察栏收窄 */
@media (max-width: 1439px) {
  .insight-col {
    width: 320px;
  }
}

/* 窄屏（1080p 窗口等）：洞察栏抽屉化，命盘画布优先 */
@media (max-width: 1279px) {
  .insight-toggle {
    display: inline-block;
  }

  .insight-col {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(360px, 92vw);
    max-height: none;
    z-index: 41;
    transform: translateX(105%);
    transition: transform 200ms ease-out;
    border-radius: 0;
  }

  .insight-col.open {
    transform: translateX(0);
  }

  .insight-mask {
    z-index: 40;
  }
}

/* 移动断点：数据栏也抽屉化 */
@media (max-width: 899px) {
  .data-toggle {
    display: inline-flex;
  }

  .data-col {
    position: fixed;
    top: 0;
    left: 64px;
    bottom: 0;
    margin: 0;
    width: min(300px, 85vw);
    background: var(--paper);
    border-right: 1px solid var(--line);
    padding: 16px;
    z-index: 41;
    transform: translateX(-110%);
    transition: transform 200ms ease-out;
  }

  .data-col.open {
    transform: translateX(0);
  }
}
</style>

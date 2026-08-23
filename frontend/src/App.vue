<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { getChart, listCharts } from './api'
import type { ChartResult, ChartSummary } from './api'
import BirthForm from './components/BirthForm.vue'
import ChartGrid from './components/ChartGrid.vue'
import ClockChart from './components/ClockChart.vue'

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

/** 三方四正联动：点其他宫换选，再点同一宫取消。 */
function onSelectPalace(branch: string) {
  selectedBranch.value = selectedBranch.value === branch ? null : branch
}

function onCalculated(result: ChartResult, name: string) {
  chart.value = result
  personName.value = name
}

async function refreshList() {
  try {
    saved.value = await listCharts()
    listError.value = ''
  } catch (e) {
    listError.value = e instanceof Error ? e.message : String(e)
  }
}

async function loadSaved(item: ChartSummary) {
  try {
    chart.value = await getChart(item.chart_id)
    personName.value = item.person
  } catch (e) {
    listError.value = e instanceof Error ? e.message : String(e)
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
        <h2 class="saved-title">已保存命盘</h2>
        <p v-if="listError" class="saved-error">{{ listError }}</p>
        <p v-else-if="saved.length === 0" class="saved-empty">暂无保存记录，填好生辰后点「保存」。</p>
        <ul v-else class="saved-list">
          <li v-for="item in saved" :key="item.chart_id">
            <button type="button" class="saved-item" @click="loadSaved(item)">
              <span class="saved-person">{{ item.person }}</span>
              <span class="saved-meta">{{ item.solar_datetime }} · {{ item.gender }}</span>
            </button>
          </li>
        </ul>
      </section>
    </aside>

    <main class="content">
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

      <template v-if="chart">
        <ChartGrid
          v-if="layout === 'grid'"
          :chart="chart"
          :person-name="personName"
          :selected-branch="selectedBranch"
          @select="onSelectPalace"
        />
        <ClockChart
          v-else
          :chart="chart"
          :person-name="personName"
          :selected-branch="selectedBranch"
          @select="onSelectPalace"
        />
      </template>
      <p v-else class="loading">排盘中…</p>
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

.saved-title {
  margin: 0 0 8px;
  font-size: 14px;
  letter-spacing: 0.2em;
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

.layout-switch {
  display: inline-flex;
  margin-bottom: 12px;
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

.loading {
  color: var(--ink-faint);
  padding: 32px;
  text-align: center;
}
</style>

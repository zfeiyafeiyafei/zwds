<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ChartResult, PatternMatch } from '../api'
import PatternPanel from './PatternPanel.vue'
import StarDetail from './StarDetail.vue'

/** 洞察栏：格局 | 星曜 合并为单栏内部 tab（ui_design.md §4.1）。
 *
 * 点击宫位时自动切到星曜 tab。
 */
const props = defineProps<{
  patterns: PatternMatch[]
  analysis: ChartResult['analysis']
  /** 当前选中宫位地支；null = 中央信息盘 */
  branch: string | null
  center: boolean
}>()

type TabKey = 'patterns' | 'stars'
const tab = ref<TabKey>('patterns')

watch(
  () => [props.branch, props.center],
  () => {
    if (props.branch || props.center) tab.value = 'stars'
  },
)
</script>

<template>
  <div class="insight">
    <div class="insight-tabs" role="group" aria-label="洞察内容">
      <button
        type="button"
        :class="{ active: tab === 'patterns' }"
        @click="tab = 'patterns'"
      >
        格局
      </button>
      <button
        type="button"
        :class="{ active: tab === 'stars' }"
        @click="tab = 'stars'"
      >
        星曜
      </button>
    </div>
    <div class="insight-body">
      <PatternPanel v-show="tab === 'patterns'" :patterns="patterns" />
      <StarDetail
        v-show="tab === 'stars'"
        :analysis="analysis"
        :branch="branch"
        :center="center"
      />
    </div>
  </div>
</template>

<style scoped>
.insight {
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  height: 100%;
}

.insight-tabs {
  display: flex;
  border-bottom: 1px solid var(--line);
  flex-shrink: 0;
}

.insight-tabs button {
  flex: 1;
  padding: 10px 0;
  border: none;
  background: transparent;
  color: var(--ink-soft);
  font-size: 13px;
  border-bottom: 2px solid transparent;
}

.insight-tabs button.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}

.insight-body {
  flex: 1;
  min-height: 0;
  display: flex;
}

/* 子组件原为一等栏（340px 固定宽+自带边框背景），并入本栏后归位 */
.insight-body > .pattern-panel,
.insight-body > .detail-panel {
  width: 100%;
  flex: 1;
  border: none;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
}
</style>

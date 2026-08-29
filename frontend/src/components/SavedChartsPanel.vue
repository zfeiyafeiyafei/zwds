<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ChartSummary } from '../api'
import { chartMeta, matchChart } from '../savedSearch'

/**
 * 已有命盘检索区块（替代原全量列表）：
 * - 输入姓名或出生日期（YYYYMMDD 或其片段）自动匹配
 * - 点结果行加载命盘；右下角「管理」进入编辑/删除/导出
 */
const props = defineProps<{
  items: ChartSummary[]
  error: string
}>()
const emit = defineEmits<{
  select: [item: ChartSummary]
  manage: []
  importFile: [file: File]
}>()

const query = ref('')

// 空查询不展开全量清单（避免长列表），提示用户输入条件
const filtered = computed(() =>
  query.value.trim() ? props.items.filter((it) => matchChart(it, query.value)) : [],
)

const importInput = ref<HTMLInputElement>()

function onImportChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许重复选择同一文件
  if (file) emit('importFile', file)
}
</script>

<template>
  <section class="saved-panel">
    <div class="saved-head">
      <h2 class="saved-title">已有命盘检索</h2>
      <button type="button" class="import-btn" @click="importInput?.click()">导入 JSON</button>
      <input
        ref="importInput"
        type="file"
        accept=".json,application/json"
        hidden
        @change="onImportChange"
      />
    </div>

    <input
      v-model="query"
      type="search"
      class="search-input"
      placeholder="姓名或出生日期，如 19840620"
      aria-label="检索已有命盘"
    />

    <p v-if="error" class="saved-error">{{ error }}</p>
    <p v-else-if="items.length === 0" class="saved-empty">暂无保存记录，填好生辰后点「保存」。</p>
    <template v-else>
      <p v-if="!query.trim()" class="saved-empty">共 {{ items.length }} 盘，输入条件自动匹配。</p>
      <p v-else-if="filtered.length === 0" class="saved-empty">无匹配结果，换个关键字试试。</p>
      <ul v-else class="saved-list">
        <li v-for="item in filtered" :key="item.chart_id" class="saved-row">
          <button type="button" class="saved-item" @click="emit('select', item)">
            <span class="saved-person">{{ item.person }}</span>
            <span class="saved-meta">{{ chartMeta(item) }}</span>
          </button>
        </li>
      </ul>
    </template>

    <div class="saved-foot">
      <button
        type="button"
        class="manage-btn"
        :disabled="items.length === 0"
        @click="emit('manage')"
      >
        管理
      </button>
    </div>
  </section>
</template>

<style scoped>
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

.search-input {
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 8px;
  padding: 6px 8px;
  font-size: 13px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 4px;
}

.search-input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.saved-row {
  display: flex;
  gap: 2px;
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

.saved-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.manage-btn {
  padding: 4px 14px;
  font-size: 12px;
  color: var(--ink-soft);
  background: transparent;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
}

.manage-btn:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
  background: #f2ecdc;
}

.manage-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>

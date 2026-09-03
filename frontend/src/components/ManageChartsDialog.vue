<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ChartSummary } from '../api'
import { chartMeta, matchChart } from '../savedSearch'

/** 命盘管理对话框：检索已有命盘后执行编辑 / 删除 / 导出。 */
const props = defineProps<{
  open: boolean
  items: ChartSummary[]
}>()
const emit = defineEmits<{
  close: []
  select: [item: ChartSummary]
  edit: [item: ChartSummary]
  remove: [item: ChartSummary]
  export: [item: ChartSummary]
}>()

const query = ref('')

// 每次打开清空上次检索条件
watch(
  () => props.open,
  (v) => {
    if (v) query.value = ''
  },
)

// 管理界面空查询时展示全量（管理需要浏览全部数据）
const filtered = computed(() => props.items.filter((it) => matchChart(it, query.value)))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="dialog-mask" @click.self="emit('close')">
      <div class="dialog" role="dialog" aria-label="命盘管理">
        <div class="dialog-head">
          <h2 class="dialog-title">命盘管理</h2>
          <button type="button" class="close-btn" title="关闭" @click="emit('close')">✕</button>
        </div>

        <input
          v-model="query"
          type="search"
          class="search-input"
          placeholder="姓名或出生日期，如 19840620"
          aria-label="检索命盘"
        />

        <p v-if="filtered.length === 0" class="empty">无匹配结果。</p>
        <ul v-else class="manage-list">
          <li v-for="item in filtered" :key="item.chart_id" class="manage-row">
            <div
              class="row-info"
              role="button"
              tabindex="0"
              title="双击或回车查看命盘"
              @dblclick="emit('select', item)"
              @keydown.enter="emit('select', item)"
            >
              <span class="row-person">{{ item.person }}</span>
              <span class="row-meta">{{ chartMeta(item) }}</span>
            </div>
            <button type="button" class="row-btn" title="编辑（姓名 / 出生信息）" @click="emit('edit', item)">✎</button>
            <button type="button" class="row-btn" title="删除命盘" @click="emit('remove', item)">✕</button>
            <button type="button" class="row-btn" title="导出 JSON 文件" @click="emit('export', item)">⇩</button>
          </li>
        </ul>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.dialog-mask {
  position: fixed;
  inset: 0;
  background: var(--mask);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.dialog {
  width: min(440px, calc(100vw - 48px));
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-title {
  margin: 0;
  font-size: 16px;
  letter-spacing: 0.02em;
  font-weight: 600;
}

.close-btn {
  padding: 2px 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink-faint);
  font-size: 13px;
}

.close-btn:hover {
  background: var(--hover-bg);
  border-color: var(--line);
  color: var(--accent);
}

.search-input {
  padding: 7px 10px;
  font-size: 13px;
  background: var(--input-bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}

.search-input:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--ring);
}

.empty {
  margin: 0;
  font-size: 12px;
  color: var(--ink-faint);
}

.manage-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 50vh;
  overflow-y: auto;
}

.manage-row {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 6px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
}

.manage-row:hover {
  background: var(--hover-bg);
  border-color: var(--line);
}

.row-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
  cursor: pointer;
  border-radius: var(--radius-sm);
}

.row-info:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.row-person {
  font-size: 13px;
  color: var(--ink);
}

.row-meta {
  font-size: 11px;
  color: var(--ink-faint);
}

.row-btn {
  flex: none;
  width: 26px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink-faint);
  font-size: 13px;
}

.row-btn:hover {
  background: var(--hover-bg);
  border-color: var(--line);
  color: var(--accent);
}
</style>

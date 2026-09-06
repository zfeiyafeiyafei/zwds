<script setup lang="ts">
/** 左侧应用导航栏：唯一全局导航（ui_design.md §3.1）。
 *
 * 上部为一级功能，底部为全局操作（主题 / 设置）。当前项左侧强调色指示条。
 */
defineProps<{
  view: 'chart' | 'ai'
  theme: 'light' | 'dark'
}>()
const emit = defineEmits<{
  select: [view: 'chart' | 'ai']
  toggleTheme: []
  openSettings: []
}>()
</script>

<template>
  <nav class="rail" aria-label="主导航">
    <button type="button" class="rail-item brand" title="紫微斗数" @click="emit('select', 'chart')">紫</button>

    <div class="rail-group">
      <button
        type="button"
        class="rail-item"
        :class="{ active: view === 'chart' }"
        title="排盘工作台"
        aria-label="排盘工作台"
        @click="emit('select', 'chart')"
      >
        ▦
      </button>
      <button
        type="button"
        class="rail-item"
        :class="{ active: view === 'ai' }"
        title="AI 分析"
        aria-label="AI 分析"
        @click="emit('select', 'ai')"
      >
        ✦
      </button>
    </div>

    <div class="rail-bottom">
      <button
        type="button"
        class="rail-item"
        :title="theme === 'dark' ? '切换为浅色主题' : '切换为深色主题'"
        :aria-label="theme === 'dark' ? '切换为浅色主题' : '切换为深色主题'"
        @click="emit('toggleTheme')"
      >
        {{ theme === 'dark' ? '☀' : '☾' }}
      </button>
      <button type="button" class="rail-item" title="设置" aria-label="设置" @click="emit('openSettings')">⚙</button>
    </div>
  </nav>
</template>

<style scoped>
.rail {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  background: var(--panel);
  border-right: 1px solid var(--line);
}

.brand {
  font-weight: 700;
  color: var(--vermilion);
  margin-bottom: 16px;
}

.rail-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.rail-bottom {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rail-item {
  position: relative;
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--radius);
  background: transparent;
  color: var(--ink-soft);
  font-size: 17px;
  line-height: 1;
}

.rail-item:hover {
  background: var(--hover-bg);
  color: var(--accent);
}

.rail-item.active {
  background: var(--chip-accent-bg);
  color: var(--accent);
}

/* 当前项指示条 */
.rail-item.active::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  border-radius: 2px;
  background: var(--accent);
}

.rail-item:focus-visible {
  outline: none;
  box-shadow: var(--ring);
}
</style>

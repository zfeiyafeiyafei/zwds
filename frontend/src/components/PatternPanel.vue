<script setup lang="ts">
import type { PatternMatch } from '../api'

defineProps<{ patterns: PatternMatch[] }>()

const STRENGTH_CLASS: Record<string, string> = { 强: 's-strong', 中: 's-mid', 弱: 's-weak' }

function strengthClass(s: string): string {
  return STRENGTH_CLASS[s] ?? ''
}
</script>

<template>
  <section class="pattern-panel" aria-label="格局分析">
    <h2 class="panel-title">格局分析</h2>
    <p v-if="patterns.length === 0" class="panel-empty">未识别到成立格局。</p>
    <ul v-else class="pattern-list">
      <li v-for="p in patterns" :key="p.name" class="pattern-card">
        <header class="pattern-head">
          <span class="pattern-name">{{ p.name }}</span>
          <span class="strength" :class="strengthClass(p.strength)">{{ p.strength }}</span>
          <span class="domain">{{ p.domain }}</span>
        </header>
        <p class="condition">成格条件：{{ p.condition }}</p>
        <p class="evidence">
          <span v-for="e in p.evidence" :key="e" class="evidence-chip">{{ e }}</span>
        </p>
        <p class="explain">{{ p.explain }}</p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.pattern-panel {
  /* 左侧栏：与右侧 StarDetail 镜像对应 */
  width: 340px;
  flex-shrink: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  padding: 12px 14px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  align-self: stretch;
  box-shadow: var(--shadow-sm);
}

.panel-title {
  margin: 0 0 10px;
  font-size: 14px;
  letter-spacing: 0.02em;
  font-weight: 600;
}

.panel-empty {
  margin: 0;
  font-size: 12px;
  color: var(--ink-faint);
}

.pattern-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pattern-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 8px 10px;
  background: var(--surface-2);
}

.pattern-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.pattern-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.strength {
  font-size: 11px;
  padding: 0 6px;
  border-radius: 999px;
  border: 1px solid currentColor;
}

.strength.s-strong {
  color: var(--accent);
}

.strength.s-mid {
  color: var(--ink-soft);
}

.strength.s-weak {
  color: var(--vermilion);
}

.domain {
  margin-left: auto;
  font-size: 11px;
  color: var(--ink-faint);
}

.condition {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--ink-soft);
}

.evidence {
  margin: 6px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.evidence-chip {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  background: var(--chip-bg);
  color: var(--ink-soft);
}

.explain {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ink);
}
</style>

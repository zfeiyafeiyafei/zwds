<script setup lang="ts">
import { computed } from 'vue'
import type { ChartResult, PalaceStarAnalysis, StarItem } from '../api'

/**
 * 右侧星曜解析栏（biz_requirement.md §4.3.2 / §5.8 交互）：
 * - 点宫位 → 该宫星曜解析（主星含落宫专注断语）
 * - 点中央信息盘 → 命主/身主断语
 */
const props = defineProps<{
  analysis?: ChartResult['analysis']
  /** 当前选中宫位地支；null 表示选中中央信息盘；undefined 表示未选择 */
  branch?: string | null
  center?: boolean
}>()

const palace = computed<PalaceStarAnalysis | null>(() =>
  props.center || !props.branch
    ? null
    : (props.analysis?.stars?.find((p) => p.branch === props.branch) ?? null),
)

const soulBody = computed(() => (props.center ? props.analysis?.soul_body : null))

function isFull(item: StarItem): boolean {
  return !!item.character
}

/** 断语若以「角色+星名：」开头（如"命主武曲："），面板已有角色标签，去掉重复前缀。 */
function stripRolePrefix(role: string, starName: string, note: string): string {
  const prefix = `${role}${starName}：`
  return note.startsWith(prefix) ? note.slice(prefix.length) : note
}
</script>

<template>
  <aside class="detail-panel" aria-label="星曜解析">
    <template v-if="soulBody">
      <h2 class="panel-title">命身四星解析</h2>
      <p v-if="soulBody.overview" class="pair-note">{{ soulBody.overview }}</p>
      <div v-for="star in soulBody.stars" :key="star.name" class="star-card">
        <header class="star-head">
          <span class="star-name major">{{ star.name }}</span>
          <span
            v-for="role in star.roles"
            :key="role"
            class="chip role"
            :class="{ body: role.startsWith('身') }"
          >
            {{ role }}
          </span>
          <span v-if="star.borrowed" class="chip mutagen">借对宫</span>
          <span v-if="star.brightness" class="chip bright">{{ star.brightness }}</span>
          <span v-if="star.mutagen" class="chip mutagen">化{{ star.mutagen }}</span>
        </header>
        <p v-for="(note, i) in star.notes" :key="i" class="line">
          <span class="role-tag">{{ star.roles[i] }}</span
          >{{ stripRolePrefix(star.roles[i], star.name, note) }}
        </p>
      </div>
    </template>

    <template v-else-if="palace">
      <h2 class="panel-title">
        {{ palace.palace }} · {{ palace.branch }}宫
        <span v-if="palace.is_soul" class="chip role">命宫</span>
        <span v-if="palace.is_body" class="chip role body">身宫</span>
      </h2>
      <p v-if="palace.pair_note" class="pair-note">{{ palace.pair_note }}</p>
      <ul class="star-list">
        <li v-for="s in palace.items" :key="s.name" class="star-card">
          <header class="star-head">
            <span class="star-name" :class="{ major: s.category === '主星' }">{{ s.name }}</span>
            <span class="chip">{{ s.category }}</span>
            <span v-if="s.element" class="chip">{{ s.element }}</span>
            <span v-if="s.brightness" class="chip bright">{{ s.brightness }}</span>
            <span v-if="s.mutagen" class="chip mutagen">化{{ s.mutagen }}</span>
          </header>
          <template v-if="isFull(s)">
            <p class="line trait">{{ s.trait }}</p>
            <p class="line">性格：{{ s.character }}</p>
            <p class="line">优势：{{ s.strength }}</p>
            <p class="line">风险：{{ s.risk }}</p>
            <p v-if="s.brightness_note" class="line note">{{ s.brightness_note }}</p>
            <p v-if="s.mutagen_note" class="line note">{{ s.mutagen_note }}</p>
            <p class="line note">{{ s.palace_note }}</p>
          </template>
          <p v-else class="line note">{{ s.trait }}</p>
        </li>
      </ul>
    </template>

    <p v-else class="panel-empty">点击宫位查看该宫星曜解析；点击中央信息盘查看命主、身主断语。</p>
  </aside>
</template>

<style scoped>
.detail-panel {
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
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-weight: 600;
}

.panel-empty {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.8;
  color: var(--ink-faint);
}

.pair-note {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
}

.star-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.star-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 8px 10px;
  margin-bottom: 8px;
  background: var(--surface-2);
}

.star-head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}

.star-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.star-name.major {
  color: var(--vermilion);
}

.chip {
  font-size: 10px;
  padding: 0 5px;
  border-radius: var(--radius-sm);
  background: var(--chip-bg);
  color: var(--ink-soft);
}

.chip.bright {
  background: var(--chip-accent-bg);
  color: var(--accent);
}

.chip.mutagen {
  background: var(--chip-vermilion-bg);
  color: var(--vermilion);
}

.chip.role {
  background: var(--chip-accent-bg);
  color: var(--accent);
}

.chip.role.body {
  background: var(--chip-vermilion-bg);
  color: var(--vermilion);
}

.line {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ink);
}

.line.trait {
  font-weight: 600;
}

.line.note {
  color: var(--ink-soft);
}

.role-tag {
  display: inline-block;
  margin-right: 6px;
  font-size: 10px;
  font-weight: 600;
  color: var(--accent);
}
</style>

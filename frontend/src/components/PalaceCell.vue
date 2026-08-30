<script setup lang="ts">
import { computed } from 'vue'
import type { Palace, Star } from '../api'
import type { PeriodTag } from '../chartText'

const props = defineProps<{ palace: Palace; selected?: boolean; tags?: PeriodTag[] }>()

const emit = defineEmits<{
  select: [branch: string]
}>()

/** 三系徽标分流：小限入宫名行；大限/流年入页脚大限年龄段之后。 */
const decadalTag = computed(() => props.tags?.find((t) => t.kind === 'decadal'))
const yearlyTag = computed(() => props.tags?.find((t) => t.kind === 'yearly'))
const xiaoxianTag = computed(() => props.tags?.find((t) => t.kind === 'xiaoxian'))

/** 流年岁序：太岁入宫虚岁（10 个）；旧快照无 yearly_ages 时回退小限口径。 */
const agesText = computed(() => (props.palace.yearly_ages ?? props.palace.ages).join(','))

const MUTAGEN_CLASS: Record<string, string> = {
  禄: 'lu',
  权: 'quan',
  科: 'ke',
  忌: 'ji',
}

function mutagenClass(star: Star): string {
  return MUTAGEN_CLASS[star.mutagen ?? ''] ?? ''
}
</script>

<template>
  <div
    class="palace"
    :class="{ soul: palace.name === '命宫', selected }"
    :data-branch="palace.branch"
    @click="emit('select', palace.branch)"
  >
    <header class="palace-head">
      <span class="palace-name" :class="{ bold: palace.name === '命宫' }">
        {{ palace.name }}
        <em v-if="palace.is_body_palace" class="body-badge">身</em>
      </span>
      <span class="head-tags">
        <i v-if="xiaoxianTag" class="period-tag xiaoxian" :class="{ filled: xiaoxianTag.filled }">{{
          xiaoxianTag.label
        }}</i>
      </span>
      <span class="palace-ganzhi">{{ palace.stem }}{{ palace.branch }}</span>
    </header>

    <div class="stars-wrap">
      <section class="stars major">
        <span
          v-for="s in palace.major_stars"
          :key="s.name"
          class="star major-star"
          :class="{ ji: s.mutagen === '忌' }"
        >
          {{ s.name }}<span v-if="s.brightness" class="brightness">{{ s.brightness }}</span
          ><i v-if="s.mutagen" class="mutagen" :class="mutagenClass(s)">{{ s.mutagen }}</i>
        </span>
      </section>

      <section class="stars minor">
        <span v-for="s in palace.minor_stars" :key="s.name" class="star">
          {{ s.name }}<i v-if="s.mutagen" class="mutagen" :class="mutagenClass(s)">{{ s.mutagen }}</i>
        </span>
      </section>

      <section class="stars adjective">
        <span v-for="s in palace.adjective_stars" :key="s.name" class="star">{{ s.name }}</span>
      </section>
    </div>

    <footer class="palace-foot">
      <div class="foot-line">
        <span class="decadal">{{ palace.decadal_range[0] }}~{{ palace.decadal_range[1] }}</span>
        <i v-if="decadalTag" class="period-tag decadal" :class="{ filled: decadalTag.filled }">{{
          decadalTag.label
        }}</i>
        <i v-if="yearlyTag" class="period-tag yearly" :class="{ filled: yearlyTag.filled }">{{
          yearlyTag.label
        }}</i>
      </div>
      <div class="ages">{{ agesText }}</div>
    </footer>
  </div>
</template>

<style scoped>
.palace {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 5px 8px;
  min-height: 0; /* 高度由宫格轨道（正方形）决定 */
  overflow: hidden; /* 溢出收进 stars-wrap 滚动区，不再顶出 footer */
  background: var(--panel);
  cursor: pointer;
}

.palace.soul {
  background: #faf3e2;
}

.palace-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: 3px;
  border-bottom: 1px solid var(--line);
  font-size: 12px;
  color: var(--ink-soft);
}

.palace-name.bold {
  font-weight: 700;
  color: var(--ink);
}

.body-badge {
  font-style: normal;
  font-size: 10px;
  padding: 0 3px;
  margin-left: 2px;
  border: 1px solid var(--accent);
  border-radius: 3px;
  color: var(--accent);
  vertical-align: 1px;
}

.palace-ganzhi {
  font-weight: 600;
  color: var(--ink);
}

/* 小限徽标：宫名之后、干支之前 */
.head-tags {
  flex: 1;
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 3px;
  min-width: 0;
}

/* 星曜区：杂曜过多时内部滚动，header/徽标/footer 保持恒可见 */
.stars-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stars {
  display: flex;
  flex-wrap: wrap;
  gap: 1px 5px;
  line-height: 1.3;
}

.major-star {
  font-size: 14px;
  font-weight: 600;
  color: var(--vermilion);
}

.major-star.ji {
  color: var(--vermilion-deep);
}

.brightness {
  font-size: 10px;
  font-weight: 400;
  color: var(--ink-faint);
  margin-left: 1px;
}

.mutagen {
  font-style: normal;
  font-size: 9px;
  line-height: 1;
  padding: 1px 3px;
  margin-left: 2px;
  border-radius: 50%;
  color: #fdfaf2;
  vertical-align: 2px;
}

.mutagen.lu {
  background: var(--badge-lu);
}

.mutagen.quan {
  background: var(--badge-quan);
}

.mutagen.ke {
  background: var(--badge-ke);
}

.mutagen.ji {
  background: var(--badge-ji);
}

.minor .star {
  font-size: 12px;
  color: var(--ink);
}

.adjective .star {
  font-size: 11px;
  color: var(--ink-faint);
}

.palace-foot {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding-top: 3px;
  border-top: 1px dashed var(--line);
}

/* 页脚首行：大限年龄段 + 大限/流年徽标 */
.foot-line {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.decadal {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  white-space: nowrap;
}

/* 流年岁序：独立一行内完整显示（10 个虚岁最长 ≈33 字符，8.5px 不换行可容） */
.ages {
  font-size: 8.5px;
  color: var(--ink-faint);
  white-space: nowrap;
}
.period-tag {
  font-style: normal;
  font-size: 10px;
  line-height: 1.4;
  padding: 0 5px;
  border-radius: 3px;
  border: 1px solid currentColor;
  white-space: nowrap;
}

.period-tag.decadal {
  color: var(--accent);
}

.period-tag.yearly {
  color: var(--vermilion);
}

.period-tag.xiaoxian {
  color: var(--badge-quan);
}

/* 运限十二宫实心徽标：三系各自成色（大限绿 / 流年红 / 小限紫）。
   必须位于上方配色规则之后，同特异性下保证文字色生效。 */
.period-tag.filled {
  border-color: transparent;
  color: #f8f5ec;
}

.period-tag.filled.decadal {
  background: var(--accent);
}

.period-tag.filled.yearly {
  background: var(--vermilion);
}

.period-tag.filled.xiaoxian {
  background: var(--badge-quan);
}
</style>

<script setup lang="ts">
import type { Palace, Star } from '../api'

defineProps<{ palace: Palace; selected?: boolean }>()

const emit = defineEmits<{
  select: [branch: string]
}>()

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
      <span class="palace-ganzhi">{{ palace.stem }}{{ palace.branch }}</span>
    </header>

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

    <footer class="palace-foot">
      <span class="decadal">{{ palace.decadal_range[0] }}~{{ palace.decadal_range[1] }}</span>
      <span class="ages">{{ palace.ages.join(',') }}</span>
    </footer>
  </div>
</template>

<style scoped>
.palace {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 8px;
  min-height: 148px;
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

.stars {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 6px;
}

.major-star {
  font-size: 15px;
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
  margin-top: auto;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 6px;
  padding-top: 3px;
  border-top: 1px dashed var(--line);
}

.decadal {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  white-space: nowrap;
}

.ages {
  font-size: 10px;
  color: var(--ink-faint);
  text-align: right;
  word-break: break-all;
}
</style>

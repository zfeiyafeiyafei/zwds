<script setup lang="ts">
import { computed, ref, watch } from 'vue'

/**
 * 自绘日期选择器（替代原生 type=date）：
 * - 原生控件在 WebKitGTK 下点外部不收起弹层，只能 Tab/Esc，体验差
 * - 本组件：点外部 / Esc / 选中日期均收起；支持直接键入 YYYY-MM-DD
 * - 日历周一为首列，提供年/月双向步进
 */
const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const open = ref(false)
const root = ref<HTMLElement>()
const text = ref(props.modelValue)

watch(
  () => props.modelValue,
  (v) => (text.value = v),
)

// ---- 面板视图（年/月） ----
const viewY = ref(2000)
const viewM = ref(1)

function syncView() {
  const m = /^(\d{4})-(\d{2})-\d{2}$/.exec(props.modelValue)
  const d = m ? new Date(+m[1], +m[2] - 1, 1) : new Date()
  viewY.value = d.getFullYear()
  viewM.value = d.getMonth() + 1
}

watch(open, (v) => {
  if (v) {
    syncView()
    window.addEventListener('pointerdown', onDocPointer, true)
    window.addEventListener('keydown', onKey)
  } else {
    window.removeEventListener('pointerdown', onDocPointer, true)
    window.removeEventListener('keydown', onKey)
  }
})

function onDocPointer(e: Event) {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') open.value = false
}

// ---- 日期合法性 ----
function validDate(y: number, m: number, d: number): boolean {
  if (y < 1 || m < 1 || m > 12 || d < 1) return false
  const dt = new Date(y, m - 1, d)
  return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d
}

const fmt = (y: number, m: number, d: number) =>
  `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`

// ---- 键入：完整合法日期即时生效；失焦时非法输入回退为当前值 ----
// 注意从事件目标读值：v-model 与本 handler 的触发顺序不定，ref 可能是旧值
function onInput(e: Event) {
  const v = (e.target as HTMLInputElement).value
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v)
  if (m && validDate(+m[1], +m[2], +m[3])) emit('update:modelValue', v)
}

function onBlur() {
  if (text.value !== props.modelValue) text.value = props.modelValue
}

// ---- 日历网格（周一为首） ----
const cells = computed(() => {
  const first = new Date(viewY.value, viewM.value - 1, 1)
  const offset = (first.getDay() + 6) % 7
  const days = new Date(viewY.value, viewM.value, 0).getDate()
  const arr: (number | null)[] = Array.from({ length: offset }, () => null)
  for (let d = 1; d <= days; d++) arr.push(d)
  return arr
})

function shiftMonth(delta: number) {
  const total = viewY.value * 12 + (viewM.value - 1) + delta
  viewY.value = Math.floor(total / 12)
  viewM.value = (total % 12) + 1
}

function pick(d: number) {
  emit('update:modelValue', fmt(viewY.value, viewM.value, d))
  open.value = false
}

const todayStr = (() => {
  const d = new Date()
  return fmt(d.getFullYear(), d.getMonth() + 1, d.getDate())
})()

const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']
</script>

<template>
  <div ref="root" class="date-field">
    <input
      v-model="text"
      type="text"
      inputmode="numeric"
      placeholder="YYYY-MM-DD"
      pattern="\d{4}-\d{2}-\d{2}"
      required
      aria-label="公历日期"
      @input="onInput"
      @blur="onBlur"
      @focus="open = true"
    />
    <button
      type="button"
      class="toggle"
      title="打开日历"
      aria-label="打开日历"
      @click="open = !open"
    >
      ▾
    </button>

    <div v-if="open" class="picker" role="dialog" aria-label="日期选择">
      <div class="picker-head">
        <button type="button" title="上一年" @click="shiftMonth(-12)">«</button>
        <button type="button" title="上一月" @click="shiftMonth(-1)">‹</button>
        <span class="picker-title">{{ viewY }} 年 {{ viewM }} 月</span>
        <button type="button" title="下一月" @click="shiftMonth(1)">›</button>
        <button type="button" title="下一年" @click="shiftMonth(12)">»</button>
      </div>
      <div class="picker-grid">
        <span v-for="w in WEEKDAYS" :key="w" class="weekday">{{ w }}</span>
        <template v-for="(c, i) in cells" :key="i">
          <button
            v-if="c !== null"
            type="button"
            class="day"
            :class="{
              selected: fmt(viewY, viewM, c) === modelValue,
              today: fmt(viewY, viewM, c) === todayStr,
            }"
            @click="pick(c)"
          >
            {{ c }}
          </button>
          <span v-else class="day-blank" />
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.date-field {
  position: relative;
  display: flex;
  gap: 4px;
}

.date-field input {
  flex: 1;
  min-width: 0;
  padding: 7px 10px;
  background: var(--input-bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}

.date-field input:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--ring);
}

.toggle {
  flex: none;
  width: 26px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--ink-soft);
  font-size: 12px;
}

.toggle:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.picker {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 30;
  width: 232px;
  padding: 8px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.picker-head button {
  width: 24px;
  padding: 2px 0;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.2;
}

.picker-head button:hover {
  background: var(--hover-bg);
  border-color: var(--line);
  color: var(--accent);
}

.picker-title {
  font-size: 13px;
  color: var(--ink);
}

.picker-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.weekday {
  text-align: center;
  font-size: 11px;
  color: var(--ink-faint);
  padding: 2px 0;
}

.day {
  padding: 3px 0;
  text-align: center;
  font-size: 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink);
}

.day:hover {
  background: var(--hover-bg);
  border-color: var(--line);
}

.day.today {
  border-color: var(--accent);
}

.day.selected {
  background: var(--accent);
  color: var(--on-accent);
}

.day-blank {
  padding: 3px 0;
}
</style>

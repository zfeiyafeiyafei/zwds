<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { getChart, updateChart } from '../api'
import type { ChartSummary } from '../api'
import { HOURS } from '../hours'
import DateField from './DateField.vue'

const props = defineProps<{ item: ChartSummary | null }>()
const emit = defineEmits<{ close: []; saved: [chartId: number] }>()

const busy = ref(false)
const error = ref('')

const form = reactive({
  person_name: '',
  solar_date: '',
  hour_index: 6,
  gender: '男' as '男' | '女',
})

// 每次打开时从所选命盘回填
watch(
  () => props.item,
  (it) => {
    if (!it) return
    error.value = ''
    form.person_name = it.person
    // 列表里是 ISO datetime，取日期段
    form.solar_date = (it.solar_datetime ?? '').slice(0, 10)
    form.hour_index = 6
    form.gender = it.gender === '女' ? '女' : '男'
    if (it.chart_id) void restoreHourIndex(it.chart_id)
  },
)

/** 列表摘要不带时辰：读一次快照回填 hour_index。 */
async function restoreHourIndex(chartId: number) {
  try {
    const snap = await getChart(chartId)
    form.hour_index = snap.input.hour_index
  } catch {
    /* 回填失败保持默认值，用户可手动改 */
  }
}

async function onSave() {
  if (!props.item) return
  if (!form.solar_date) {
    error.value = '请选择公历日期'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await updateChart(props.item.chart_id, {
      solar_date: form.solar_date,
      hour_index: form.hour_index,
      gender: form.gender,
      person_name: form.person_name.trim() || '未命名',
    })
    emit('saved', props.item.chart_id)
    emit('close')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="item" class="dialog-mask" @click.self="emit('close')">
      <form class="dialog" @submit.prevent="onSave">
        <h2 class="dialog-title">编辑命盘</h2>

        <label class="field">
          <span>姓名</span>
          <input v-model="form.person_name" type="text" maxlength="32" />
        </label>

        <label class="field">
          <span>性别</span>
          <select v-model="form.gender">
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </label>

        <label class="field">
          <span>公历日期</span>
          <DateField v-model="form.solar_date" />
        </label>

        <label class="field">
          <span>时辰</span>
          <select v-model.number="form.hour_index">
            <option v-for="h in HOURS" :key="h.index" :value="h.index">{{ h.label }}</option>
          </select>
        </label>

        <p class="hint">修改出生参数会按新参数重新排盘并覆盖此命盘。</p>
        <p v-if="error" class="form-error">{{ error }}</p>

        <div class="actions">
          <button type="button" class="btn" :disabled="busy" @click="emit('close')">取消</button>
          <button type="submit" class="btn primary" :disabled="busy">保存</button>
        </div>
      </form>
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
  width: min(340px, calc(100vw - 48px));
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.dialog-title {
  margin: 0;
  font-size: 16px;
  letter-spacing: 0.02em;
  font-weight: 600;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--ink-soft);
}

.field input,
.field select {
  padding: 7px 10px;
  background: var(--input-bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}

.field input:focus-visible,
.field select:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--ring);
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--ink-faint);
}

.form-error {
  margin: 0;
  font-size: 12px;
  color: var(--vermilion-deep);
}

.actions {
  display: flex;
  gap: 8px;
}

.btn {
  flex: 1;
  padding: 7px 0;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--ink);
  font-weight: 500;
}

.btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--on-accent);
}

.btn:hover:not(:disabled) {
  filter: brightness(0.96);
}
.btn:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--ring);
}

.btn:disabled {
  opacity: 0.55;
  cursor: default;
}
</style>

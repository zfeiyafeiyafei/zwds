<script setup lang="ts">
import { reactive, ref } from 'vue'
import { calculate, saveChart } from '../api'
import type { BirthPayload, ChartResult } from '../api'
import { HOURS } from '../hours'
import DateField from './DateField.vue'

const emit = defineEmits<{
  calculated: [chart: ChartResult, personName: string, payload: BirthPayload]
  saved: []
}>()

const form = reactive<BirthPayload & { person_name: string }>({
  person_name: '',
  solar_date: '1990-05-15',
  hour_index: 6,
  gender: '男',
})

const busy = ref(false)
const error = ref('')

function payload(): BirthPayload {
  return { solar_date: form.solar_date, hour_index: form.hour_index, gender: form.gender }
}

async function onCalculate() {
  busy.value = true
  error.value = ''
  try {
    const p = payload()
    const chart = await calculate(p)
    emit('calculated', chart, form.person_name.trim(), p)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

async function onSave() {
  busy.value = true
  error.value = ''
  try {
    const name = form.person_name.trim()
    const p = payload()
    const chart = await calculate(p)
    await saveChart(name ? { ...p, person_name: name } : p)
    emit('calculated', chart, name, p)
    emit('saved')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

defineExpose({ onCalculate })
</script>

<template>
  <form class="birth-form" @submit.prevent="onCalculate">
    <h2 class="form-title">排盘</h2>

    <label class="field">
      <span>姓名（可选）</span>
      <input v-model="form.person_name" type="text" placeholder="未命名" maxlength="32" />
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

    <p v-if="error" class="form-error">{{ error }}</p>

    <div class="actions">
      <button type="submit" class="btn primary" :disabled="busy">排盘</button>
      <button type="button" class="btn" :disabled="busy" @click="onSave">保存</button>
    </div>
  </form>
</template>

<style scoped>
.birth-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.form-title {
  margin: 0 0 4px;
  font-size: 16px;
  letter-spacing: 0.2em;
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
  padding: 6px 8px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 4px;
}

.field input:focus-visible,
.field select:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.actions {
  display: flex;
  gap: 8px;
}

.btn {
  flex: 1;
  padding: 7px 0;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: var(--panel);
  color: var(--ink);
}

.btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #f8f5ec;
}

.btn:hover:not(:disabled) {
  filter: brightness(0.96);
}

.btn:disabled {
  opacity: 0.55;
  cursor: default;
}

.form-error {
  margin: 0;
  font-size: 12px;
  color: var(--vermilion-deep);
}
</style>

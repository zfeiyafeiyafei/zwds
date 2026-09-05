<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import type { ChartResult, ChatMessage, Skill } from '../api'
import { listSkills, streamChat } from '../api'

/** AI 分析页签：skill 选择 + 流式对话（biz_requirement.md §4.4.3）。 */
const props = defineProps<{ chart: ChartResult | null }>()
const emit = defineEmits<{ openSettings: [] }>()

type UIMessage = ChatMessage & { reasoning?: string }

const skills = ref<Skill[]>([])
const selectedSkillId = ref<number | null>(null)
const messages = ref<UIMessage[]>([])
const streaming = ref(false)
const statusText = ref('')
const followUp = ref('')
const threadRef = ref<HTMLElement>()
// 对话所基于的命盘引用：切换命盘后提示重开（§4.4.3-4）
const contextChart = ref<ChartResult | null>(null)

let abort: AbortController | null = null

async function reloadSkills() {
  skills.value = await listSkills()
  if (!skills.value.some((s) => s.id === selectedSkillId.value)) {
    selectedSkillId.value = skills.value[0]?.id ?? null
  }
}
defineExpose({ reloadSkills })
onMounted(reloadSkills)

async function scrollToEnd() {
  await nextTick()
  threadRef.value?.scrollTo({ top: threadRef.value.scrollHeight })
}

/** 发起一轮对话（首轮或追问），流式渲染回复。 */
async function run(userText: string) {
  if (!props.chart || selectedSkillId.value == null || streaming.value) return
  contextChart.value = props.chart
  messages.value.push({ role: 'user', content: userText })
  const reply: UIMessage = { role: 'assistant', content: '', reasoning: '' }
  messages.value.push(reply)
  streaming.value = true
  statusText.value = '连接中…'
  abort = new AbortController()
  try {
    await streamChat(
      {
        skill_id: selectedSkillId.value,
        chart: props.chart,
        // 历史不含刚 push 的空 assistant 占位
        messages: messages.value.slice(0, -1),
      },
      (text, kind) => {
        if (kind === 'reasoning') {
          // 推理模型的思考过程：折叠展示，同时让"生成中"状态可见
          reply.reasoning! += text
          statusText.value = '思考中…'
        } else {
          reply.content += text
          statusText.value = '生成中…'
        }
        void scrollToEnd()
      },
      abort.signal,
    )
  } catch (e) {
    if (!abort.signal.aborted) {
      reply.content = reply.content || `出错了：${e instanceof Error ? e.message : String(e)}`
    }
  } finally {
    streaming.value = false
    statusText.value = ''
    abort = null
    void scrollToEnd()
  }
}

/** 选中 skill：发起首轮分析。 */
function onPickSkill() {
  if (selectedSkillId.value == null) return
  const skill = skills.value.find((s) => s.id === selectedSkillId.value)
  messages.value = []
  void run(`请对此命盘进行「${skill?.name ?? ''}」。`)
}

function sendFollowUp() {
  const text = followUp.value.trim()
  if (!text) return
  followUp.value = ''
  void run(text)
}

function stop() {
  abort?.abort()
}

/** 以当前命盘重新开始对话。 */
function restartWithCurrentChart() {
  messages.value = []
  contextChart.value = null
}
// 以出生参数判定是否换盘：同一盘重新计算会产生新对象引用，不能按引用比较
const chartChanged = computed(
  () =>
    contextChart.value != null &&
    props.chart != null &&
    JSON.stringify(contextChart.value.input) !== JSON.stringify(props.chart.input),
)
</script>

<template>
  <div class="ai-panel">
    <div class="ai-toolbar">
      <select v-model="selectedSkillId" class="skill-select" :disabled="streaming" aria-label="选择分析 skill">
        <option v-for="s in skills" :key="s.id" :value="s.id">
          {{ s.name }}{{ s.is_builtin ? '' : '（自定义）' }}
        </option>
      </select>
      <button
        type="button"
        class="primary-btn"
        :disabled="!chart || selectedSkillId == null || streaming"
        @click="onPickSkill"
      >
        开始分析
      </button>
      <button type="button" class="row-btn" title="AI 设置" @click="emit('openSettings')">⚙ 设置</button>
      <span v-if="statusText" class="status">{{ statusText }}</span>
    </div>

    <p v-if="!chart" class="empty">请先在「排盘」页签生成命盘。</p>

    <template v-else>
      <p v-if="chartChanged" class="notice">
        当前对话基于先前的命盘。
        <button type="button" class="link-btn" @click="restartWithCurrentChart">以新命盘重新开始</button>
      </p>

      <div ref="threadRef" class="thread">
        <p v-if="messages.length === 0" class="empty">选择 skill 后点击「开始分析」，命盘 JSON 会自动附加给 AI。</p>
        <div
          v-for="(m, i) in messages"
          :key="i"
          class="bubble"
          :class="m.role"
        >
          <div class="bubble-role">{{ m.role === 'user' ? '我' : 'AI' }}</div>
          <div class="bubble-body">
            <details v-if="m.reasoning" class="reasoning">
              <summary>思考过程</summary>{{ m.reasoning }}
            </details>
            {{ m.content }}<span
              v-if="streaming && i === messages.length - 1 && m.role === 'assistant'"
              class="cursor"
            >▍</span>
          </div>
        </div>
      </div>

      <div class="composer">
        <textarea
          v-model="followUp"
          rows="2"
          placeholder="追问：如「今年适合换工作吗？」"
          :disabled="streaming || messages.length === 0"
          @keydown.enter.exact.prevent="sendFollowUp"
        ></textarea>
        <button v-if="streaming" type="button" class="row-btn" @click="stop">停止</button>
        <button
          v-else
          type="button"
          class="primary-btn"
          :disabled="!followUp.trim() || messages.length === 0"
          @click="sendFollowUp"
        >
          发送
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ai-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: calc(100vh - 150px);
  min-height: 420px;
}

.ai-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.skill-select {
  padding: 6px 10px;
  font-size: 13px;
  background: var(--input-bg);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  min-width: 160px;
}

.primary-btn {
  padding: 6px 16px;
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: var(--on-accent);
  font-size: 13px;
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.row-btn {
  padding: 6px 12px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--ink-soft);
  font-size: 13px;
}

.row-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--hover-bg);
}

.status {
  font-size: 12px;
  color: var(--accent);
}

.notice {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  background: var(--panel);
}

.link-btn {
  border: none;
  background: transparent;
  color: var(--accent);
  font-size: 12px;
  padding: 0 4px;
  text-decoration: underline;
}

.thread {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
}

.empty {
  margin: 0;
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--ink-faint);
}

.bubble {
  max-width: 82%;
  padding: 10px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
}

.bubble.user {
  align-self: flex-end;
  background: var(--hover-bg);
}

.bubble.assistant {
  align-self: flex-start;
  background: transparent;
}

.bubble-role {
  font-size: 11px;
  color: var(--ink-faint);
  margin-bottom: 4px;
}

.bubble-body {
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.reasoning {
  margin-bottom: 8px;
  padding: 6px 10px;
  border-left: 2px solid var(--line-strong);
  font-size: 12px;
  color: var(--ink-faint);
  line-height: 1.6;
}

.reasoning summary {
  cursor: pointer;
  color: var(--ink-soft);
  font-size: 11px;
  margin-bottom: 4px;
}

.cursor {
  color: var(--accent);
  animation: blink 0.9s steps(2) infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.composer {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.composer textarea {
  flex: 1;
  resize: none;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
  line-height: 1.6;
  background: var(--input-bg);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}

.composer textarea:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--ring);
}
</style>

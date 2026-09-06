<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { ChartResult, ChatMessage, Skill } from '../api'
import { clearAIHistory, getAIHistory, listSkills, streamChat } from '../api'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

/** LLM 输出为 Markdown；marked 渲染后经 DOMPurify 消毒（内容不可信，防 XSS）。 */
function renderMd(text: string): string {
  return DOMPurify.sanitize(marked.parse(text, { async: false }))
}

/** AI 分析工作台：skill chips + 流式对话（ui_design.md §5，biz_requirement.md §4.4.3）。 */
const props = defineProps<{ chart: ChartResult | null; personName: string }>()
const emit = defineEmits<{ openSettings: [] }>()

type UIMessage = ChatMessage & { reasoning?: string }

const skills = ref<Skill[]>([])
const selectedSkillId = ref<number | null>(null)
const messages = ref<UIMessage[]>([])
const streaming = ref(false)
const statusText = ref('')
const followUp = ref('')
const threadRef = ref<HTMLElement>()

/** 命盘线程键：出生参数三元组，与服务端 _chart_key 对齐。 */
const chartKey = computed(() => {
  const inp = props.chart?.input
  return inp ? `${inp.solar_date}|${inp.hour_index}|${inp.gender}` : null
})

let abort: AbortController | null = null

async function reloadSkills() {
  skills.value = await listSkills()
  if (!skills.value.some((s) => s.id === selectedSkillId.value)) {
    selectedSkillId.value = skills.value[0]?.id ?? null
  }
}
defineExpose({ reloadSkills })
onMounted(reloadSkills)

/** 切换命盘：中止当前流，加载该命盘的对话线程（历史 by 命盘）。 */
async function loadHistory() {
  abort?.abort()
  if (!chartKey.value) {
    messages.value = []
    return
  }
  try {
    const rows = await getAIHistory(chartKey.value)
    messages.value = rows.map((r) => ({
      role: r.role,
      content: r.content,
      reasoning: r.reasoning ?? undefined,
    }))
    const lastSkill = [...rows].reverse().find((r) => r.skill_id != null)?.skill_id
    if (lastSkill != null) selectedSkillId.value = lastSkill
  } catch {
    messages.value = []
  }
}

watch(chartKey, () => void loadHistory(), { immediate: true })

/** 清空当前命盘的对话线程。 */
async function clearThread() {
  if (!chartKey.value || !window.confirm('清空当前命盘的 AI 对话记录？')) return
  abort?.abort()
  await clearAIHistory(chartKey.value)
  messages.value = []
}

async function scrollToEnd() {
  await nextTick()
  threadRef.value?.scrollTo({ top: threadRef.value.scrollHeight })
}

/** 发起一轮对话（首轮或追问），流式渲染回复。 */
async function run(userText: string, skillId: number) {
  if (!props.chart || streaming.value) return
  selectedSkillId.value = skillId
  messages.value.push({ role: 'user', content: userText })
  const reply: UIMessage = { role: 'assistant', content: '', reasoning: '' }
  messages.value.push(reply)
  streaming.value = true
  statusText.value = '连接中…'
  abort = new AbortController()
  try {
    await streamChat(
      {
        skill_id: skillId,
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

/** 点击 skill chip：追加一轮该 skill 的分析（不清空线程，历史持久化在服务端）。 */
function runSkill(skill: Skill) {
  void run(`请对此命盘进行「${skill.name}」。`, skill.id)
}

function sendFollowUp() {
  const text = followUp.value.trim()
  if (!text || selectedSkillId.value == null) return
  followUp.value = ''
  void run(text, selectedSkillId.value)
}

function stop() {
  abort?.abort()
}
</script>

<template>
  <div class="ai-panel">
    <div class="session-head">
      <span v-if="chart" class="chart-chip" :title="chart.input.solar_date">
        {{ personName || '未命名' }} · {{ chart.input.solar_date }} · {{ chart.input.gender }}
      </span>
      <span v-else class="chart-chip empty-chip">未选择命盘</span>
      <span class="spacer"></span>
      <button
        v-if="messages.length"
        type="button"
        class="btn"
        title="清空当前命盘的对话记录"
        :disabled="streaming"
        @click="clearThread"
      >
        清空
      </button>
      <button type="button" class="btn btn-icon" title="AI 设置" @click="emit('openSettings')">⚙</button>
    </div>

    <div v-if="skills.length" class="skill-chips" role="group" aria-label="分析 skill">
      <button
        v-for="s in skills"
        :key="s.id"
        type="button"
        class="chip"
        :class="{ active: s.id === selectedSkillId, custom: !s.is_builtin }"
        :disabled="!chart || streaming"
        :title="s.is_builtin ? s.name : `${s.name}（自定义）`"
        @click="runSkill(s)"
      >
        {{ s.name }}
      </button>
    </div>

    <p v-if="!chart" class="empty">请先在「排盘」工作台生成命盘。</p>

    <template v-else>
      <div ref="threadRef" class="thread">
        <div class="thread-inner">
          <p v-if="messages.length === 0" class="empty">
            点击上方 skill 开始分析，命盘 JSON 会自动附加给 AI。
          </p>
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
              <div v-if="m.role === 'assistant'" class="md" v-html="renderMd(m.content)"></div>
              <template v-else>{{ m.content }}</template>
              <span
                v-if="streaming && i === messages.length - 1 && m.role === 'assistant'"
                class="cursor"
              >▍</span>
            </div>
          </div>
        </div>
      </div>

      <div class="composer">
        <textarea
          v-model="followUp"
          rows="2"
          placeholder="追问：如「今年适合换工作吗？」（Enter 发送，Shift+Enter 换行）"
          :disabled="streaming || messages.length === 0"
          @keydown.enter.exact.prevent="sendFollowUp"
        ></textarea>
        <button v-if="streaming" type="button" class="btn" @click="stop">停止</button>
        <button
          v-else
          type="button"
          class="btn btn-primary"
          :disabled="!followUp.trim() || messages.length === 0"
          @click="sendFollowUp"
        >
          发送
        </button>
      </div>
      <span v-if="statusText" class="status">{{ statusText }}</span>
    </template>
  </div>
</template>

<style scoped>
.ai-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: calc(100vh - 32px);
  min-height: 420px;
}

.session-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spacer {
  flex: 1;
}

.chart-chip {
  font-size: 13px;
  color: var(--ink);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 5px 14px;
  white-space: nowrap;
}

.empty-chip {
  color: var(--ink-faint);
}

/* skill chips：比下拉少一次点击，全部可见（ui_design.md §5） */
.skill-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  padding: 5px 14px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--panel);
  color: var(--ink-soft);
  font-size: 13px;
}

.chip:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--hover-bg);
}

.chip.active {
  background: var(--chip-accent-bg);
  color: var(--accent);
  border-color: var(--accent);
  font-weight: 600;
}

.chip.custom {
  border-style: dashed;
}

.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status {
  font-size: 12px;
  color: var(--accent);
  align-self: center;
}

.thread {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
}

/* 对话流 760px 居中，避免长行阅读疲劳（§5-3） */
.thread-inner {
  max-width: 760px;
  margin: 0 auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty {
  margin: 0;
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--ink-faint);
}

.bubble {
  max-width: 92%;
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

/* Markdown 渲染区不保留 pre-wrap，交由标签语义控制换行 */
.bubble-body .md {
  white-space: normal;
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

/* Markdown 内容排版 */
.md :deep(h1),
.md :deep(h2),
.md :deep(h3),
.md :deep(h4) {
  margin: 12px 0 6px;
  font-size: 14px;
  color: var(--ink);
}

.md :deep(p) {
  margin: 6px 0;
}

.md :deep(ul),
.md :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}

.md :deep(li) {
  margin: 3px 0;
}

.md :deep(strong) {
  color: var(--ink);
}

.md :deep(code) {
  font-size: 12px;
  background: var(--hover-bg);
  border-radius: 4px;
  padding: 1px 5px;
}

.md :deep(pre) {
  background: var(--hover-bg);
  border-radius: var(--radius-sm);
  padding: 10px;
  overflow-x: auto;
}

.md :deep(pre code) {
  background: none;
  padding: 0;
}

.md :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
}

.md :deep(th),
.md :deep(td) {
  border: 1px solid var(--line);
  padding: 4px 10px;
  font-size: 12px;
}

.md :deep(hr) {
  border: none;
  border-top: 1px solid var(--line);
  margin: 10px 0;
}

.md :deep(blockquote) {
  margin: 6px 0;
  padding-left: 10px;
  border-left: 2px solid var(--line-strong);
  color: var(--ink-soft);
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
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
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

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Skill } from '../api'
import {
  createSkill,
  deleteSkill,
  fetchModels,
  getAIConfig,
  listSkills,
  putAIConfig,
  updateSkill,
} from '../api'

/** AI 设置对话框：LLM API 配置 + skill 管理（biz_requirement.md §4.4.1）。 */
const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; changed: [] }>()

// ---- LLM 供应商预设（OpenAI 兼容协议；模型仅为常见默认，可拉取或手填） ----
interface ProviderPreset {
  name: string
  base_url: string
  models: string[]
}
const PROVIDERS: ProviderPreset[] = [
  { name: 'DeepSeek', base_url: 'https://api.deepseek.com', models: ['deepseek-v4-flash', 'deepseek-v4-pro'] },
  { name: 'Kimi（月之暗面）', base_url: 'https://api.moonshot.cn/v1', models: ['kimi-k2', 'kimi-latest'] },
  { name: '通义千问（阿里）', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: ['qwen-plus', 'qwen-max', 'qwen-turbo'] },
  { name: '智谱 GLM', base_url: 'https://open.bigmodel.cn/api/paas/v4', models: ['glm-4-plus', 'glm-4-flash'] },
  { name: 'OpenAI', base_url: 'https://api.openai.com/v1', models: ['gpt-4o-mini', 'gpt-4o'] },
  { name: 'Ollama（本地）', base_url: 'http://127.0.0.1:11434/v1', models: [] },
  { name: '自定义', base_url: '', models: [] },
]

const provider = ref('DeepSeek')
const baseUrl = ref('')
const model = ref('')
const apiKey = ref('')
const configHint = ref('')
const hasKey = ref(false)
const modelOptions = ref<string[]>([])
const pulling = ref(false)

// 选择供应商：自动填 Base URL 与默认模型；用户只输 Key
watch(provider, (name) => {
  const p = PROVIDERS.find((x) => x.name === name)
  if (!p) return
  if (p.base_url) baseUrl.value = p.base_url
  modelOptions.value = p.models
  if (p.models.length && !p.models.includes(model.value)) model.value = p.models[0]
})
// 手改 Base URL 时若不再匹配任何预设，归为自定义
watch(baseUrl, (v) => {
  const p = PROVIDERS.find((x) => x.base_url === v.replace(/\/$/, ''))
  provider.value = p ? p.name : '自定义'
})

async function pullModels() {
  pulling.value = true
  configHint.value = ''
  try {
    const { models } = await fetchModels({ base_url: baseUrl.value, api_key: apiKey.value || undefined })
    modelOptions.value = models
    if (models.length && !models.includes(model.value)) model.value = models[0]
    configHint.value = `已拉取 ${models.length} 个模型`
  } catch (e) {
    configHint.value = e instanceof Error ? e.message : String(e)
  } finally {
    pulling.value = false
  }
}

// ---- skill 管理 ----
const skills = ref<Skill[]>([])
const editing = ref<Skill | null>(null) // 正在编辑的 skill（null = 不在编辑）
const creating = ref(false)
const formName = ref('')
const formContent = ref('')
const skillError = ref('')

const formReadonly = computed(() => !!editing.value?.is_builtin)

async function reload() {
  const [cfg, list] = await Promise.all([getAIConfig(), listSkills()])
  baseUrl.value = cfg.base_url
  model.value = cfg.model
  hasKey.value = cfg.has_api_key
  skills.value = list
  // 依据已存 base_url 反查供应商；datalist 先给预设，拉取后覆盖
  const p = PROVIDERS.find((x) => x.base_url === cfg.base_url.replace(/\/$/, ''))
  provider.value = p ? p.name : '自定义'
  modelOptions.value = p ? p.models : []
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      apiKey.value = ''
      configHint.value = ''
      skillError.value = ''
      cancelEdit()
      void reload()
    }
  },
)

async function saveConfig() {
  try {
    // 留空 = 保持原 key；已填 = 更新
    await putAIConfig({ base_url: baseUrl.value, model: model.value, api_key: apiKey.value })
    hasKey.value = hasKey.value || !!apiKey.value
    apiKey.value = ''
    configHint.value = '已保存'
  } catch (e) {
    configHint.value = e instanceof Error ? e.message : String(e)
  }
}

function startEdit(s: Skill) {
  editing.value = s
  creating.value = false
  formName.value = s.name
  formContent.value = s.content
  skillError.value = ''
}

function startCreate() {
  editing.value = null
  creating.value = true
  formName.value = ''
  formContent.value = ''
  skillError.value = ''
}

function cancelEdit() {
  editing.value = null
  creating.value = false
}

async function saveSkill() {
  if (!formName.value.trim() || !formContent.value.trim()) {
    skillError.value = '名称与内容不能为空'
    return
  }
  try {
    if (creating.value) {
      await createSkill({ name: formName.value.trim(), content: formContent.value })
    } else if (editing.value) {
      await updateSkill(editing.value.id, {
        name: formName.value.trim(),
        content: formContent.value,
      })
    }
    cancelEdit()
    await reload()
    emit('changed') // 通知 AI 页签刷新 skill 列表
  } catch (e) {
    skillError.value = e instanceof Error ? e.message : String(e)
  }
}

async function removeSkill(s: Skill) {
  if (!window.confirm(`确定删除 skill「${s.name}」吗？`)) return
  try {
    await deleteSkill(s.id)
    if (editing.value?.id === s.id) cancelEdit()
    await reload()
    emit('changed')
  } catch (e) {
    skillError.value = e instanceof Error ? e.message : String(e)
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="dialog-mask" @click.self="emit('close')">
      <div class="dialog" role="dialog" aria-label="AI 设置">
        <div class="dialog-head">
          <h2 class="dialog-title">AI 设置</h2>
          <button type="button" class="close-btn" title="关闭" @click="emit('close')">✕</button>
        </div>

        <section class="section">
          <h3 class="section-title">LLM API</h3>
          <label class="field">
            <span>供应商</span>
            <select v-model="provider">
              <option v-for="p in PROVIDERS" :key="p.name" :value="p.name">{{ p.name }}</option>
            </select>
          </label>
          <label class="field">
            <span>Base URL</span>
            <input v-model="baseUrl" type="text" placeholder="https://api.openai.com/v1" :readonly="provider !== '自定义'" />
          </label>
          <label class="field">
            <span>API Key</span>
            <input
              v-model="apiKey"
              type="password"
              :placeholder="hasKey ? '已保存（留空保持不变）' : 'sk-...'"
            />
          </label>
          <label class="field">
            <span>模型</span>
            <input v-model="model" type="text" list="model-options" placeholder="选择或输入模型名" />
            <datalist id="model-options">
              <option v-for="m in modelOptions" :key="m" :value="m" />
            </datalist>
            <button type="button" class="row-btn" :disabled="pulling || !baseUrl" @click="pullModels">
              {{ pulling ? '拉取中…' : '拉取模型' }}
            </button>
          </label>
          <div class="row-actions">
            <button type="button" class="primary-btn" :disabled="!baseUrl || !model" @click="saveConfig">
              保存配置
            </button>
            <span class="hint">{{ configHint }}</span>
          </div>
        </section>

        <section class="section">
          <div class="section-head">
            <h3 class="section-title">Skill（提示词）</h3>
            <button type="button" class="row-btn" title="新建 skill" @click="startCreate">＋ 新建</button>
          </div>
          <ul class="skill-list">
            <li v-for="s in skills" :key="s.id" class="skill-row">
              <span class="skill-name">
                {{ s.name }}
                <em v-if="s.is_builtin" class="tag">内置</em>
              </span>
              <button type="button" class="row-btn" title="查看 / 编辑内容" @click="startEdit(s)">✎</button>
              <button
                v-if="!s.is_builtin"
                type="button"
                class="row-btn"
                title="删除"
                @click="removeSkill(s)"
              >
                ✕
              </button>
            </li>
          </ul>

          <div v-if="editing || creating" class="skill-form">
            <input
              v-model="formName"
              type="text"
              placeholder="skill 名称"
              :disabled="formReadonly"
            />
            <textarea v-model="formContent" rows="8" placeholder="提示词内容" :disabled="formReadonly"></textarea>
            <div class="row-actions">
              <button v-if="!formReadonly" type="button" class="primary-btn" @click="saveSkill">保存</button>
              <span v-else class="hint">内置 skill 为只读，可复制内容后「＋ 新建」自定义版本</span>
              <button type="button" class="row-btn" @click="cancelEdit">{{ formReadonly ? '关闭' : '取消' }}</button>
              <span class="hint error">{{ skillError }}</span>
            </div>
          </div>
        </section>
      </div>
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
  width: min(560px, calc(100vw - 48px));
  max-height: calc(100vh - 64px);
  overflow-y: auto;
  scrollbar-width: thin;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  padding: 2px 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink-faint);
  font-size: 13px;
}

.close-btn:hover {
  background: var(--hover-bg);
  border-color: var(--line);
  color: var(--accent);
}

.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  margin: 0;
  font-size: 13px;
  color: var(--ink-soft);
  font-weight: 600;
}

.field {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ink-soft);
}

.field span {
  width: 72px;
  flex-shrink: 0;
}

.field input,
.field select,
.skill-form input,
.skill-form textarea {
  flex: 1;
  padding: 7px 10px;
  font-size: 13px;
  background: var(--input-bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  color: var(--ink);
  font-family: inherit;
}

.field input[readonly] {
  opacity: 0.7;
}

.field .row-btn {
  flex-shrink: 0;
}

.skill-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skill-form textarea {
  resize: vertical;
  line-height: 1.6;
}

.field input:focus-visible,
.field select:focus-visible,
.skill-form input:focus-visible,
.skill-form textarea:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--ring);
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 10px;
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
  padding: 4px 10px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--ink-soft);
  font-size: 12px;
}

.row-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--hover-bg);
}

.row-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.skill-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.skill-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}

.skill-name {
  flex: 1;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tag {
  font-size: 11px;
  font-style: normal;
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 999px;
  padding: 0 8px;
}

.hint {
  font-size: 12px;
  color: var(--ink-faint);
}

.hint.error {
  color: var(--bad, #c0564f);
}
</style>

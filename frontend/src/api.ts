/** 与后端 GET/POST /api/charts* 对齐的类型与请求封装。 */

export type Mutagen = '禄' | '权' | '科' | '忌'

export interface Star {
  name: string
  type: string
  mutagen?: Mutagen | string
  brightness?: string
}

export interface Palace {
  branch: string
  stem: string
  name: string
  is_body_palace: boolean
  is_original_palace: boolean
  changsheng12: string
  boshi12: string
  suiqian12: string
  jiangqian12: string
  ages: number[]
  /** 本宫流年虚岁（10 个）；旧快照可能缺失，回退用 ages */
  yearly_ages?: number[]
  decadal_range: [number, number]
  major_stars: Star[]
  minor_stars: Star[]
  adjective_stars: Star[]
}

export interface ChartResult {
  engine_version: string
  input: {
    solar_date: string
    hour_index: number
    gender: '男' | '女'
  }
  calendar: {
    lunar_year: number
    lunar_month: number
    lunar_day: number
    is_leap: boolean
    zodiac: string
    ganzhi: { year: string; month: string; day: string; hour: string }
  }
  meta: {
    soul_palace_branch: string
    body_palace_branch: string
    five_elements_class: string
    class_number: number
    soul: string
    body: string
  }
  palaces: Palace[]
  display: Record<string, unknown>
  horoscope?: Horoscope
  analysis?: { patterns: PatternMatch[]; stars?: PalaceStarAnalysis[]; soul_body?: SoulBody }
}
/** 格局分析命中（biz_requirement.md §4.3.1）。 */
export interface PatternMatch {
  name: string
  strength: '强' | '中' | '弱' | string
  evidence: string[]
  condition: string
  domain: string
  explain: string
}

/** 单星解读条目（biz_requirement.md §4.3.2）。 */
export interface StarItem {
  name: string
  category: '主星' | '辅星' | '杂曜'
  brightness: string
  mutagen: string
  element: string
  trait: string
  character: string
  strength: string
  risk: string
  brightness_note: string
  mutagen_note: string
  palace_note: string
}

/** 命身四星条目：同一星曜兼具多个身份（命宫主星/命主/身宫主星/身主）时合并为一卡。 */
export interface SoulBodyStar {
  name: string
  /** 角色（与 notes 一一对应）：命宫主星 / 命主 / 身宫主星 / 身主 */
  roles: string[]
  notes: string[]
  /** 空宫借对宫主星 */
  borrowed: boolean
  brightness: string
  mutagen: string
}

/** 命身四星解析（命宫主星/命主/身宫主星/身主 + 命身关系总述）。 */
export interface SoulBody {
  stars: SoulBodyStar[]
  overview: string
}

/** 单宫星曜分析。 */
export interface PalaceStarAnalysis {
  palace: string
  branch: string
  is_soul: boolean
  is_body: boolean
  items: StarItem[]
  pair_note: string
}

export interface HoroscopeDecadal {
  index: number
  branch: string
  age_start: number
  age_end: number
  /** 运限十二宫 {地支: 宫名}（命宫起地支递减） */
  palace_names?: Record<string, string>
}

/** 运限定位结果（POST /api/charts/calculate 的 horoscope 区块）。 */
export interface Horoscope {
  target_date: string
  lunar_year: number
  nominal_age: number
  decadal: HoroscopeDecadal | null // null = 未上运
  yearly: {
    gan: string
    zhi: string
    mutagens: Record<string, Mutagen | string>
    palace_names?: Record<string, string>
  }
  xiaoxian_branch: string
  xiaoxian_palace_names?: Record<string, string>
}

export interface ChartSummary {
  chart_id: number
  person: string
  solar_datetime: string
  hour_index?: number | null // 旧数据回填前可能缺失
  gender: string
  engine_version: string
}

export interface BirthPayload {
  solar_date: string // YYYY-MM-DD
  hour_index: number // 0=早子时 … 11=亥时 12=晚子时
  gender: '男' | '女'
  target_date?: string // 运限定位目标日，缺省今天
}

// 开发环境走 vite proxy（/api → 127.0.0.1:8765）；
// Tauri 生产 webview 加载 tauri:// 自定义协议，必须用绝对地址访问本地 sidecar。
const API_BASE = import.meta.env.DEV ? '' : 'http://127.0.0.1:8765'

/** 是否运行在 Tauri 桌面 webview（WebKitGTK 不支持 <a download> 与 navigator.clipboard，需走插件）。 */
function inTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`请求失败 ${res.status}: ${await res.text()}`)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/** 排盘（不落库）。 */
export function calculate(payload: BirthPayload): Promise<ChartResult> {
  return request('/charts/calculate', { method: 'POST', body: JSON.stringify(payload) })
}

/** 排盘并保存。 */
export function saveChart(
  payload: BirthPayload & { person_name?: string },
): Promise<{ chart_id: number; person: string }> {
  return request('/charts', { method: 'POST', body: JSON.stringify(payload) })
}

/** 编辑已保存命盘：出生参数 + 姓名（整体重排覆盖，历史快照保留）。 */
export function updateChart(
  chartId: number,
  payload: BirthPayload & { person_name: string },
): Promise<{ chart_id: number; person: string }> {
  return request(`/charts/${chartId}`, { method: 'PUT', body: JSON.stringify(payload) })
}

/** 删除已保存命盘。 */
export function deleteChart(chartId: number): Promise<void> {
  return request(`/charts/${chartId}`, { method: 'DELETE' })
}

/** 已保存命盘列表。 */
export function listCharts(): Promise<ChartSummary[]> {
  return request('/charts')
}

/** 读取已保存命盘快照。 */
export function getChart(chartId: number): Promise<ChartResult> {
  return request(`/charts/${chartId}`)
}
/** 下载 JSON 文本为文件：Tauri 走原生保存对话框，浏览器走 <a download>。 */
async function downloadJson(text: string, filename: string): Promise<void> {
  if (inTauri()) {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const { writeTextFile } = await import('@tauri-apps/plugin-fs')
    const path = await save({
      defaultPath: filename,
      filters: [{ name: 'JSON', extensions: ['json'] }],
    })
    if (!path) return // 用户取消
    await writeTextFile(path, text)
  } else {
    const blob = new Blob([text], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
  }
}

/** 从响应头解析导出文件名，失败回退 fallback。 */
function exportFilename(res: Response, fallback: string): string {
  const m = (res.headers.get('content-disposition') ?? '').match(/filename\*=UTF-8''([^;]+)/)
  return m ? decodeURIComponent(m[1]) : fallback
}

/** 导出命盘 JSON 快照文件。 */
export async function exportChart(chartId: number, fallbackName: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/charts/${chartId}/export`)
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)
  await downloadJson(await res.text(), exportFilename(res, `ziwei_${fallbackName}.json`))
}

/** 导出全部命盘为单个 JSON 文件（备份/迁移）。 */
export async function exportAllCharts(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/charts/export-all`)
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)
  await downloadJson(await res.text(), exportFilename(res, 'ziwei_all.json'))
}

/** 将命盘 JSON 数据复制到剪贴板（Tauri 走剪贴板插件，浏览器走 navigator.clipboard）。 */
export async function copyChartJson(chart: ChartResult): Promise<void> {
  const text = JSON.stringify(chart, null, 2)
  if (inTauri()) {
    const { writeText } = await import('@tauri-apps/plugin-clipboard-manager')
    await writeText(text)
  } else {
    await navigator.clipboard.writeText(text)
  }
}

/** 导入命盘 JSON 文件内容（服务端重排后落库）。 */
export function importChart(
  snapshot: unknown,
  personName?: string,
): Promise<{ chart_id: number; person: string }> {
  return request('/charts/import', {
    method: 'POST',
    body: JSON.stringify({ snapshot, person_name: personName || '导入命盘' }),
  })
}

// ---------- AI 分析（biz_requirement.md §4.4） ----------

export interface Skill {
  id: number
  name: string
  category: string | null
  content: string
  is_builtin: boolean
}

export interface AIConfig {
  base_url: string
  model: string
  api_key_masked: string
  has_api_key: boolean
}

export function listSkills(): Promise<Skill[]> {
  return request('/ai/skills')
}

export function createSkill(payload: {
  name: string
  content: string
  category?: string
}): Promise<Skill> {
  return request('/ai/skills', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateSkill(
  id: number,
  payload: { name: string; content: string; category?: string },
): Promise<Skill> {
  return request(`/ai/skills/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export function deleteSkill(id: number): Promise<void> {
  return request(`/ai/skills/${id}`, { method: 'DELETE' })
}

export function getAIConfig(): Promise<AIConfig> {
  return request('/ai/config')
}

export function putAIConfig(payload: {
  base_url: string
  model: string
  api_key?: string | null
}): Promise<{ ok: boolean }> {
  return request('/ai/config', { method: 'PUT', body: JSON.stringify(payload) })
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** 拉取上游可用模型列表（可带未保存的 base_url/key 试连）。 */
export function fetchModels(payload: {
  base_url?: string
  api_key?: string
}): Promise<{ models: string[] }> {
  return request('/ai/models', { method: 'POST', body: JSON.stringify(payload) })
}

/**
 * 流式对话：POST /api/ai/chat，逐段回调增量文本。
 * onDelta(text, kind)：kind 为 content（正文）或 reasoning（模型思考过程）。
 * signal 用于中途停止。
 */
export async function streamChat(
  payload: { skill_id: number; chart: unknown; messages: ChatMessage[] },
  onDelta: (text: string, kind: 'content' | 'reasoning') => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) {
    throw new Error(`请求失败 ${res.status}: ${await res.text()}`)
  }
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // SSE 事件以空行分隔
    const events = buffer.split('\n\n')
    buffer = events.pop()!
    for (const evt of events) {
      const line = evt.split('\n').find((l) => l.startsWith('data:'))
      if (!line) continue
      const data = line.slice(5).trim()
      if (data === '[DONE]') return
      const parsed = JSON.parse(data)
      if (parsed.error) throw new Error(parsed.error)
      if (parsed.delta) onDelta(parsed.delta, 'content')
      if (parsed.reasoning) onDelta(parsed.reasoning, 'reasoning')
    }
  }
}

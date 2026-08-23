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
}

export interface ChartSummary {
  chart_id: number
  person: string
  solar_datetime: string
  gender: string
  engine_version: string
}

export interface BirthPayload {
  solar_date: string // YYYY-MM-DD
  hour_index: number // 0=早子时 … 11=亥时 12=晚子时
  gender: '男' | '女'
}

// 开发环境走 vite proxy（/api → 127.0.0.1:8765）；
// Tauri 生产 webview 加载 tauri:// 自定义协议，必须用绝对地址访问本地 sidecar。
const API_BASE = import.meta.env.DEV ? '' : 'http://127.0.0.1:8765'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`请求失败 ${res.status}: ${await res.text()}`)
  }
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

/** 已保存命盘列表。 */
export function listCharts(): Promise<ChartSummary[]> {
  return request('/charts')
}

/** 读取已保存命盘快照。 */
export function getChart(chartId: number): Promise<ChartResult> {
  return request(`/charts/${chartId}`)
}

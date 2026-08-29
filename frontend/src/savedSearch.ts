import type { ChartSummary } from './api'
import { shortHourLabel } from './hours'

/**
 * 命盘检索匹配：姓名包含关键字，或出生日期数字匹配。
 * 日期查询支持 YYYYMMDD 全量或其连续片段（如 1984、8406、0620），至少 4 位数字。
 */
export function matchChart(item: ChartSummary, query: string): boolean {
  const q = query.trim()
  if (!q) return true
  if (item.person.toLowerCase().includes(q.toLowerCase())) return true
  const digits = q.replace(/\D/g, '')
  if (digits.length >= 4) {
    const dateDigits = (item.solar_datetime ?? '').slice(0, 10).replace(/\D/g, '')
    if (dateDigits.includes(digits)) return true
  }
  return false
}

/** 结果行摘要：出生年月日 · 时辰 · 性别。 */
export function chartMeta(item: ChartSummary): string {
  const date = (item.solar_datetime ?? '').slice(0, 10)
  const hour = item.hour_index != null ? ` · ${shortHourLabel(item.hour_index)}` : ''
  return `${date}${hour} · ${item.gender}`
}

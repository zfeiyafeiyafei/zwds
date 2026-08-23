import type { ChartResult } from './api'

const HOUR_NAMES = ['早子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '晚子']

/** hour_index → 「午时」/「晚子时」等展示文本。 */
export function hourLabel(hourIndex: number): string {
  return `${HOUR_NAMES[hourIndex] ?? ''}时`
}

/** 农历日期展示文本（含闰月标记）。 */
export function lunarLabel(calendar: ChartResult['calendar']): string {
  return `${calendar.lunar_year}年${calendar.is_leap ? '闰' : ''}${calendar.lunar_month}月${calendar.lunar_day}日`
}

const BRANCH_ORDER = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

/**
 * 三方四正连线：与宫名无关，仅按地支索引。
 * 三方 = (b±4)%12（三合局），对宫 = (b+6)%12。
 * 返回 4 条连线端点对：三角 3 边（三方两两相连）+ 对宫 1 条。
 */
export function relationEdges(branch: string): Array<[string, string]> {
  const i = BRANCH_ORDER.indexOf(branch)
  const t1 = BRANCH_ORDER[(i + 4) % 12]
  const t2 = BRANCH_ORDER[(i + 8) % 12] // 同 (i-4)%12
  const opposite = BRANCH_ORDER[(i + 6) % 12]
  return [
    [branch, t1],
    [branch, t2],
    [t1, t2],
    [branch, opposite],
  ]
}

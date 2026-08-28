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

export type PeriodKind = 'decadal' | 'yearly' | 'xiaoxian'

export interface PeriodTag {
  label: string
  kind: PeriodKind
  /** 实心彩色徽标（运限十二宫标注 大命/流兄/小官…） */
  filled?: boolean
}

/** 运限十二宫短名：与引擎 DERIVED_PALACE_NAMES 一一对应。 */
const DERIVED_FULL = ['命宫', '兄弟', '夫妻', '子女', '财帛', '疾厄', '迁移', '交友', '官禄', '田宅', '福德', '父母']
const DERIVED_SHORT = ['命', '兄', '夫', '子', '财', '疾', '迁', '友', '官', '田', '福', '父']

function shortOf(name: string): string {
  const i = DERIVED_FULL.indexOf(name)
  return i >= 0 ? DERIVED_SHORT[i] : ''
}

/**
 * 运限标注：每宫三系徽标（大限/流年/小限），随目标日期整体重排。
 * - 十二宫各得一枚实心徽标：大命/大兄…、流命/流兄…、小命/小兄…
 * - 命宫位徽标合并原信息：大命 45~54、流命 丙午年
 * 无 horoscope（旧快照）时返回空表。
 */
export function periodTags(
  horoscope: ChartResult['horoscope'] | undefined | null,
): Record<string, PeriodTag[]> {
  const out: Record<string, PeriodTag[]> = {}
  const push = (branch: string, tag: PeriodTag) => {
    ;(out[branch] ??= []).push(tag)
  }
  if (!horoscope) return out

  const emit = (
    names: Record<string, string> | undefined,
    prefix: string,
    kind: PeriodKind,
    baseText?: (branch: string) => string | null,
  ) => {
    if (!names) return
    for (const [branch, name] of Object.entries(names)) {
      const s = shortOf(name)
      if (!s) continue
      const merged = baseText?.(branch) ?? null
      push(branch, {
        label: merged ?? `${prefix}${s}`,
        kind,
        filled: true,
      })
    }
  }

  if (horoscope.decadal?.palace_names) {
    emit(
      horoscope.decadal.palace_names,
      '大',
      'decadal',
      (b) =>
        b === horoscope.decadal!.branch
          ? `大命 ${horoscope.decadal!.age_start}~${horoscope.decadal!.age_end}`
          : null,
    )
  }
  emit(
    horoscope.yearly.palace_names,
    '流',
    'yearly',
    (b) => (b === horoscope.yearly.zhi ? `流命 ${horoscope.yearly.gan}${horoscope.yearly.zhi}年` : null),
  )
  emit(horoscope.xiaoxian_palace_names, '小', 'xiaoxian')
  return out
}

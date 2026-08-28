/** 时辰选项：与引擎 hour_index 约定一致（0=早子时 … 12=晚子时）。 */
export interface HourOption {
  index: number
  label: string
}

export const HOURS: HourOption[] = [
  { index: 0, label: '早子时 00:00-01:00' },
  { index: 1, label: '丑时 01:00-03:00' },
  { index: 2, label: '寅时 03:00-05:00' },
  { index: 3, label: '卯时 05:00-07:00' },
  { index: 4, label: '辰时 07:00-09:00' },
  { index: 5, label: '巳时 09:00-11:00' },
  { index: 6, label: '午时 11:00-13:00' },
  { index: 7, label: '未时 13:00-15:00' },
  { index: 8, label: '申时 15:00-17:00' },
  { index: 9, label: '酉时 17:00-19:00' },
  { index: 10, label: '戌时 19:00-21:00' },
  { index: 11, label: '亥时 21:00-23:00' },
  { index: 12, label: '晚子时 23:00-24:00' },
]

/** 短标签（去掉时间范围）：0→早子时，6→午时，12→晚子时。 */
export function shortHourLabel(index: number): string {
  const h = HOURS.find((x) => x.index === index)
  return h ? h.label.split(' ')[0] : ''
}

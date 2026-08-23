// 生成 iztro 运限参照 JSON（大限/流年/小限），用于交叉验证
// 用法: node gen_ref_horoscope.mjs <solarDate> <hourIndex> <gender> <targetSolarDate> <outputPath>
import { writeFileSync } from 'node:fs';
import { astro } from 'iztro';

const [date, hour, gender, target, out] = process.argv.slice(2);
if (!date || hour === undefined || !gender || !target || !out) {
  console.error('usage: node gen_ref_horoscope.mjs <YYYY-M-D> <hourIndex> <男|女> <targetYYYY-M-D> <out.json>');
  process.exit(1);
}
const a = astro.bySolar(date, Number(hour), gender, true, 'zh-CN');
writeFileSync(out, JSON.stringify(a.horoscope(target), null, 2));
console.log(`written: ${out}`);

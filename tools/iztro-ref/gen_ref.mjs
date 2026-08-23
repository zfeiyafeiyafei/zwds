// 生成 iztro 参照命盘 JSON，用于交叉验证
// 用法: node gen_ref.mjs <solarDate YYYY-M-D> <hourIndex 0-12> <gender 男|女> <outputPath>
import { writeFileSync } from 'node:fs';
import { astro } from 'iztro';

const [date, hour, gender, out] = process.argv.slice(2);
if (!date || hour === undefined || !gender || !out) {
  console.error('usage: node gen_ref.mjs <YYYY-M-D> <hourIndex> <男|女> <out.json>');
  process.exit(1);
}
const a = astro.bySolar(date, Number(hour), gender, true, 'zh-CN');
writeFileSync(out, JSON.stringify(a, null, 2));
console.log(`written: ${out}`);

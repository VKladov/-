// Usage: node dwg2json.mjs plan.dwg build/db.json
// Reads a DWG with LibreDWG (WebAssembly build) and writes its database as JSON.
import { Dwg_File_Type, LibreDwg } from '@mlightcad/libredwg-web';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const [src, dst] = process.argv.slice(2);
if (!src || !dst) {
  console.error('usage: node dwg2json.mjs plan.dwg out.json');
  process.exit(2);
}
const here = path.dirname(fileURLToPath(import.meta.url));
const libredwg = await LibreDwg.create(path.join(here, 'node_modules/@mlightcad/libredwg-web/wasm/'));
const dwg = libredwg.dwg_read_data(fs.readFileSync(src), Dwg_File_Type.DWG);
if (!dwg) {
  console.error('cannot read', src);
  process.exit(1);
}
const db = libredwg.convert(dwg);
const replacer = (k, v) => (v instanceof Uint8Array ? `<bytes ${v.length}>` : (typeof v === 'bigint' ? v.toString() : v));
fs.mkdirSync(path.dirname(dst), { recursive: true });
fs.writeFileSync(dst, JSON.stringify(db, replacer));
const byType = {};
for (const e of db.entities) byType[e.type] = (byType[e.type] || 0) + 1;
console.log(src, '->', dst, byType);
libredwg.dwg_free(dwg);

import { readFile, writeFile, rename } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const base = new URL('../models/', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('manifest.json', base), 'utf8'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
let bytes;
try { bytes = await readFile(new URL(manifest.file, base)); } catch {}
if (bytes && hash(bytes) === manifest.sha256) console.log('手部模型已就绪，SHA-256 一致。');
else {
  console.log('从 Google 官方来源下载固定版本手部模型（约 7.5 MB）…');
  const response = await fetch(manifest.url, { signal: AbortSignal.timeout(60000) });
  if (!response.ok) throw Error(`模型下载失败：${response.status}`);
  bytes = Buffer.from(await response.arrayBuffer());
  if (hash(bytes) !== manifest.sha256) throw Error('模型校验不一致，未采用下载内容。');
  const pending = new URL(manifest.file + '.download', base);
  await writeFile(pending, bytes);
  await rename(pending, new URL(manifest.file, base));
  console.log('手部模型下载完成，SHA-256 一致。');
}

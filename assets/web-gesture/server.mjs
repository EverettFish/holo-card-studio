import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 4186);
const types = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.mjs':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8', '.json':'application/json; charset=utf-8', '.png':'image/png', '.glb':'model/gltf-binary', '.wasm':'application/wasm', '.task':'application/octet-stream' };
const server = http.createServer(async (req, res) => {
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Permissions-Policy', 'camera=(self), microphone=(), geolocation=()');
  res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; worker-src 'self'; connect-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'self'; base-uri 'self'");
  if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405); res.end('Read only'); return; }
  try {
    const url = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (url.split('/').some(segment => segment.startsWith('.'))) { res.writeHead(403); res.end('Forbidden'); return; }
    let filename = path.resolve(root, '.' + url);
    if (filename !== root && !filename.startsWith(root + path.sep)) { res.writeHead(403); res.end('Forbidden'); return; }
    if ((await stat(filename)).isDirectory()) filename = path.join(filename, 'index.html');
    const data = await readFile(filename);
    res.writeHead(200, { 'Content-Type': types[path.extname(filename)] || 'application/octet-stream' });
    res.end(req.method === 'HEAD' ? undefined : data);
  } catch { res.writeHead(404); res.end('Not found'); }
});
server.on('error', error => {
  console.error(error.code === 'EADDRINUSE' ? `端口 ${port} 已被占用。请关闭本原型旧进程，或用 PORT 指定另一个空闲端口。` : error.message);
  process.exitCode = 1;
});
server.listen(port, '127.0.0.1', () => console.log(`Holo Card Studio · 手势赏卡：http://127.0.0.1:${port}/`));

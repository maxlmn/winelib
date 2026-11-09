// The built site served as GitHub Pages serves it, to check it before publishing: dist/ at BASE_PATH (/winelib),
// a folder's index.html, and the site's 404.html (with its status) for anything missing.
//
//     npm run build && npm run serve      # http://localhost:4321/winelib/ (and on the local network)
import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { dirname, extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const base = (process.env.BASE_PATH || '/winelib').replace(/\/$/, '');
const port = +(process.env.PORT || 4321);
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript','.css': 'text/css', '.json': 'application/json',
	'.png': 'image/png', '.gif': 'image/gif', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json',
	'.xml': 'application/xml', '.txt': 'text/plain', '.woff2': 'font/woff2', '.wasm': 'application/wasm' };

function send(res, file, status = 200) {
	res.writeHead(status, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream' });
	createReadStream(file).pipe(res);
}

createServer((req, res) => {
	const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
	if (!path.startsWith(base + '/') && path !== base) return send(res, join(dist, '404.html'), 404);
	let file = normalize(join(dist, path.slice(base.length)));
	if (!file.startsWith(dist)) return send(res, join(dist, '404.html'), 404);
	if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
	if (existsSync(file)) return send(res, file);
	send(res, join(dist, '404.html'), 404);
}).listen(port, '0.0.0.0', () => console.log(`http://localhost:${port}${base}/`));

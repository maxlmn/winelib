/**
 * The installed app's service worker. The app itself (its code, styles, icons) is kept on the device, one copy per
 * version, so it opens at once; the data always comes from the server (/api is never cached here). Offline, the app
 * still opens (its pages then can't load their data).
 */
import { version } from '$app/env';
import { assets, immutable } from '$app/manifest';
import { self as sw } from '$app/service-worker';

const CACHE = `winelib-${version}`;
// The build's files and static/, by absolute path (the app is served at the root); and the app's one page
// (index.html, served at / for every address), for opening offline
const SHELL = [...immutable, ...assets].map((f) => (f.path.startsWith('/') ? f.path : `/${f.path}`)).concat('/');

sw.addEventListener('install', (event) => {
	event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => sw.skipWaiting()));
});

// A new version replaces the old copies
sw.addEventListener('activate', (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
			.then(() => sw.clients.claim())
	);
});

sw.addEventListener('fetch', (event) => {
	const req = event.request;
	const url = new URL(req.url);
	if (req.method !== 'GET' || url.origin !== sw.location.origin || url.pathname.startsWith('/api/')) return;
	// The app's own files: from the device
	if (SHELL.includes(url.pathname) && url.pathname !== '/') {
		event.respondWith(caches.match(url.pathname).then((hit) => hit ?? fetch(req)));
		return;
	}
	// A page: the server's; offline, the copy on the device
	if (req.mode === 'navigate') {
		event.respondWith(fetch(req).catch(async () => (await caches.match('/')) ?? Response.error()));
	}
});

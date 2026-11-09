import { sveltekit } from '@sveltejs/kit/vite';
import adapter from '@sveltejs/adapter-static';
import { defineConfig } from 'vite';

// BASE_PATH: the app under a sub-path (/winelib/demo); VITE_DEMO=1: the static demo (src/lib/demo.ts), read-only,
// its API answers saved as files, served by GitHub Pages (404.html: its fallback for the app's routes)
const base = (process.env.BASE_PATH ?? '').replace(/\/$/, '') as '' | `/${string}`;
const demo = process.env.VITE_DEMO === '1';

export default defineConfig({
	// SPA: FastAPI serves build/index.html for every non-API route
	plugins: [
		sveltekit({
			// BUILD_DIR: another folder than build/ (the demo's, built beside the app's)
			adapter: adapter({ pages: process.env.BUILD_DIR || 'build', assets: process.env.BUILD_DIR || 'build', fallback: demo ? '404.html' : 'index.html' }),
			paths: { base },
			...(demo ? { serviceWorker: { register: false as const } } : {})
		})
	],
	server: {
		proxy: { '/api': process.env.API_URL ?? 'http://localhost:8000' }
	}
});

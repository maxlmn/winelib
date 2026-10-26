import { sveltekit } from '@sveltejs/kit/vite';
import adapter from '@sveltejs/adapter-static';
import { defineConfig } from 'vite';

export default defineConfig({
	// SPA: FastAPI serves build/index.html for every non-API route
	plugins: [sveltekit({ adapter: adapter({ fallback: 'index.html' }) })],
	server: {
		proxy: { '/api': process.env.API_URL ?? 'http://localhost:8000' }
	}
});

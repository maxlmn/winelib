/**
 * The browser smoke tests (e2e/): WineLib as it runs (python run.py, the built web app) on an empty data folder,
 * seeded through its own API (e2e/setup.ts), clicked through in Chromium. Not the map's tiles: the pages around it.
 *
 *     npm run build && npm run e2e          # PYTHON=path/to/python when it isn't `python`
 */
import { defineConfig, devices } from '@playwright/test';
import { rmSync } from 'node:fs';
import { resolve } from 'node:path';

const PORT = 8123;
const DATA = resolve('e2e/.data');
// A new installation each run (in the runner only: a worker loads this file again, the server running)
if (!process.env.TEST_WORKER_INDEX) rmSync(DATA, { recursive: true, force: true });

export default defineConfig({
	testDir: 'e2e',
	globalSetup: './e2e/setup.ts',
	fullyParallel: false,
	workers: 1, // one database for every test
	retries: process.env.CI ? 1 : 0,
	reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
	use: { baseURL: `http://127.0.0.1:${PORT}`, trace: 'retain-on-failure' },
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
	webServer: {
		command: `${process.env.PYTHON ?? 'python'} ../../run.py --port ${PORT} --no-browser --data "${DATA}"`,
		url: `http://127.0.0.1:${PORT}/api/settings`,
		timeout: 120_000,
		reuseExistingServer: false,
		stdout: 'ignore',
		stderr: 'pipe'
	}
});

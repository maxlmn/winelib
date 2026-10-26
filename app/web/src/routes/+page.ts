import { loadDashboard } from '#lib/api/dashboard.ts';

export const load = async ({ fetch }) => ({ dashboard: await loadDashboard(fetch) });

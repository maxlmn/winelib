/** Help: the guides (GET /api/help, /api/help/{slug}), Markdown from app/api/data/docs/help/. */
type Fetch = typeof fetch;

export interface GuideRef {
	slug: string;
	title: string;
}

export interface GuideSummary extends GuideRef {
	summary: string;
}

export interface Guide extends GuideSummary {
	body: string;
	prev: GuideRef | null;
	next: GuideRef | null;
}

export const getGuides = (fetch: Fetch) => fetch('/api/help').then((r) => r.json() as Promise<GuideSummary[]>);

export async function getGuide(fetch: Fetch, slug: string) {
	const r = await fetch(`/api/help/${encodeURIComponent(slug)}`);
	return r.ok ? ((await r.json()) as Guide) : null;
}

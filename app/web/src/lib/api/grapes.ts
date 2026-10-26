/** The grapes directory (GET /api/grapes). */
type Fetch = typeof fetch;

export interface GrapeRow {
	id: number;
	name: string;
	aliases: string | null;
	/** its berries (VIVC): White, Red, Pink, Grey */
	color: string | null;
	origin: string | null;
	parents: string[];
	/** each parent's id, when it's in the list */
	parent_ids: (number | null)[];
	/** how many grapes name it as a parent */
	offspring: number;
	/** wines it's in (main grape or not), their bottles in the cellar, their tastings */
	wines: number;
	bottles: number;
	tastings: number;
	/** has a tasting profile (climate, acidity, tannin...) */
	profile: boolean;
}

export const getGrapes = (fetch: Fetch) => fetch('/api/grapes').then((r) => r.json() as Promise<GrapeRow[]>);

/** A berry colour's swatch */
export const BERRY_COLORS: Record<string, string> = { Red: '#5b1a2e', White: '#d9c25c', Pink: '#d58aa0', Grey: '#9a8f99' };

export interface FamilyNode {
	name: string;
	/** its page, when the grape is in the list */
	id: number | null;
}

export interface Family {
	parents: (FamilyNode & { parents: FamilyNode[] })[];
	offspring: FamilyNode[];
}

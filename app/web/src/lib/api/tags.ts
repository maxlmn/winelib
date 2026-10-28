/** Style tags ("fresh", "mineral"): set on a wine by hand or picked in a tasting, gathered when shown (style_tags.py). */

export interface WineTag {
	tag: string;
	/** set on the wine by hand */
	set: boolean;
	/** how many of its tastings found it */
	tastings: number;
}

export interface TagsInfo {
	/** the shared words to pick from */
	vocabulary: string[];
	/** every tag in use, with how many wines carry it */
	used: { tag: string; wines: number }[];
}

let kept: Promise<TagsInfo> | null = null;

/** The vocabulary and the tags in use (asked once a page load; `fresh` asks again, after a save) */
function loadTags(fresh = false): Promise<TagsInfo> {
	if (!kept || fresh)
		kept = fetch('/api/tags')
			.then((r) => (r.ok ? r.json() : { vocabulary: [], used: [] }))
			.catch(() => ({ vocabulary: [], used: [] }));
	return kept;
}

/** The words to offer: the vocabulary, then the others in use (most used first), then these extra ones */
export async function suggestions(...extra: string[][]): Promise<string[]> {
	const t = await loadTags();
	return [...new Set([...t.vocabulary, ...t.used.map((u) => u.tag), ...extra.flat()])];
}

export async function setWineTags(wineId: number, tags: string[]): Promise<WineTag[]> {
	const r = await fetch(`/api/wines/${wineId}/tags`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ tags })
	});
	if (!r.ok) throw new Error(`Couldn’t save the tags (${r.status})`);
	loadTags(true);
	return (await r.json()).tags;
}

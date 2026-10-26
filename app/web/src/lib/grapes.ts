/** A wine's grapes as text: "Merlot 70%, Cabernet Franc 30%" (the main one first). */
export type WineGrape = { id: number; name: string; share: number | null };

export const grapesText = (grapes: WineGrape[] | undefined, fallback?: string | null): string | null =>
	grapes?.length ? grapes.map((g) => (g.share ? `${g.name} ${+g.share.toFixed(1)}%` : g.name)).join(', ') : (fallback ?? null);

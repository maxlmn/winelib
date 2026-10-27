/** The wishlist (see app/api/routers/wishlist.py). */
import { send } from './forms.ts';

type Fetch = typeof fetch;

export interface WishItem {
	id: number;
	wine_id: number;
	producer: string;
	producer_id: number;
	cuvee: string;
	vintage: string;
	color: string | null;
	region: string | null;
	appellation: string | null;
	lwin: string | null;
	/** "RP 95 · VI 94" */
	scores: string | null;
	/** any vintage of the cuvée will do */
	any_vintage: boolean;
	bottle_size: string;
	/** its market price's */
	currency: string;
	note: string | null;
	url: string | null;
	added: string | null;
	market: { price: number; date: string | null; source: string | null } | null;
	market_base: number | null;
	/** bottles of it (or of the cuvée, any vintage) in the cellar */
	owned: number;
	/** why a price fetch found none */
	log?: string[];
}

export interface WishIn {
	wine_id?: number;
	any_vintage: boolean;
	bottle_size: string | null;
	note: string | null;
	url: string | null;
}

export const toWishIn = (i: WishItem): WishIn => ({ any_vintage: i.any_vintage, bottle_size: i.bottle_size, note: i.note, url: i.url });

/** A new entry for a wine: nothing set yet */
export const blankWish = (wine_id?: number): WishIn => ({ wine_id, any_vintage: false, bottle_size: null, note: null, url: null });

export async function loadWishlist(fetch: Fetch): Promise<WishItem[]> {
	const r = await fetch('/api/wishlist');
	if (!r.ok) throw new Error('Couldn’t load the wishlist');
	return (await r.json()).items;
}

export const addWish = (body: WishIn) => send<WishItem>('POST', '/api/wishlist', body);
export const editWish = (id: number, body: WishIn) => send<WishItem>('PUT', `/api/wishlist/${id}`, body);
export const removeWish = (id: number) => send<{ deleted: number }>('DELETE', `/api/wishlist/${id}`);
export const priceWish = (id: number) => send<WishItem>('POST', `/api/wishlist/${id}/price`);

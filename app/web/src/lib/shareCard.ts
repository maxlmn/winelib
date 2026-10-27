/**
 * Share stickers, Strava-style: a transparent PNG to lay over a photo in an Instagram story (or a solid card). One
 * tasting (the wine, its score, when and where) or a tasting session (the evening's wines). Drawn on a canvas in the
 * browser, 1080 px wide (a story's width), its height as the content needs.
 */
import { FALLBACK_REGION, typeColor } from './colors.ts';
import { regionColor } from './regions.svelte.ts';

export type Style = 'light' | 'dark' | 'card';

export interface StickerWine {
	producer: string;
	cuvee: string;
	vintage: string;
	color: string | null;
	region: string | null;
	appellation: string | null;
	rating: number | null;
}

const W = 1080;
const PAD = 72;
const FONT = '"Inter", "Segoe UI", system-ui, -apple-system, Roboto, sans-serif';

function palette(style: Style) {
	return style === 'dark'
		? { ink: '#1b1716', soft: 'rgba(27,23,22,0.62)', shadow: 'rgba(255,255,255,0.35)', card: null, rule: 'rgba(27,23,22,0.25)' }
		: style === 'card'
			? { ink: '#f6f1ee', soft: 'rgba(246,241,238,0.68)', shadow: null, card: '#1d1a20', rule: 'rgba(246,241,238,0.18)' }
			: { ink: '#ffffff', soft: 'rgba(255,255,255,0.78)', shadow: 'rgba(0,0,0,0.45)', card: null, rule: 'rgba(255,255,255,0.4)' };
}

/** Lines of text no wider than max (words kept whole; a word too long is let through) */
function wrap(ctx: CanvasRenderingContext2D, text: string, max: number): string[] {
	const lines: string[] = [];
	let line = '';
	for (const word of text.split(/\s+/).filter(Boolean)) {
		const next = line ? `${line} ${word}` : word;
		if (ctx.measureText(next).width > max && line) {
			lines.push(line);
			line = word;
		} else line = next;
	}
	if (line) lines.push(line);
	return lines;
}

/** A bottle seen end-on, as everywhere in WineLib: its region's colour, the wine's colour as the cork */
function bottleEnd(ctx: CanvasRenderingContext2D, x: number, y: number, r: number, w: Pick<StickerWine, 'region' | 'color'>) {
	ctx.save();
	ctx.shadowColor = 'rgba(0,0,0,0.25)';
	ctx.shadowBlur = r * 0.3;
	ctx.beginPath();
	ctx.arc(x, y, r, 0, Math.PI * 2);
	ctx.fillStyle = regionColor(w.region) ?? FALLBACK_REGION;
	ctx.fill();
	ctx.restore();
	ctx.beginPath();
	ctx.arc(x, y, r * 0.36, 0, Math.PI * 2);
	ctx.fillStyle = w.color ? typeColor(w.color) : 'rgba(0,0,0,0.15)';
	ctx.fill();
}

type Op = (ctx: CanvasRenderingContext2D, y: number) => number; // draws at y, returns the next y

/** Measures, then draws: the ops run twice, on a scratch canvas for the height, then for real */
function render(style: Style, ops: Op[]): HTMLCanvasElement {
	const scratch = document.createElement('canvas').getContext('2d')!;
	let height = PAD;
	for (const op of ops) height = op(scratch, height);
	height += PAD;
	const canvas = document.createElement('canvas');
	canvas.width = W;
	canvas.height = Math.ceil(height);
	const ctx = canvas.getContext('2d')!;
	const p = palette(style);
	if (p.card) {
		ctx.fillStyle = p.card;
		ctx.beginPath();
		ctx.roundRect(0, 0, W, canvas.height, 48);
		ctx.fill();
	}
	let y = PAD;
	for (const op of ops) y = op(ctx, y);
	return canvas;
}

function text(ctx: CanvasRenderingContext2D, style: Style, s: string, x: number, y: number, font: string, color: 'ink' | 'soft', spacing = 0) {
	const p = palette(style);
	ctx.font = font;
	ctx.fillStyle = p[color];
	ctx.textBaseline = 'alphabetic';
	(ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = `${spacing}px`;
	if (p.shadow) {
		ctx.shadowColor = p.shadow;
		ctx.shadowBlur = 12;
	}
	ctx.fillText(s, x, y);
	ctx.shadowColor = 'transparent';
	ctx.shadowBlur = 0;
	(ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = '0px';
}

/** The small WineLib mark at the bottom, and a line above it */
function footer(style: Style, label: string): Op {
	return (ctx, y) => {
		y += 34;
		ctx.fillStyle = palette(style).rule;
		ctx.fillRect(PAD, y, W - 2 * PAD, 2);
		y += 58;
		text(ctx, style, label, PAD, y, `500 30px ${FONT}`, 'soft');
		ctx.font = `700 30px ${FONT}`;
		const mark = 'WINELIB';
		(ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = '6px';
		const wMark = ctx.measureText(mark).width;
		(ctx as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = '0px';
		text(ctx, style, mark, W - PAD - wMark, y, `700 30px ${FONT}`, 'soft', 6);
		return y + 8;
	};
}

/** One tasting: the wine large, its score, when and where */
export function tastingSticker(w: StickerWine, when: string, where: string, style: Style): HTMLCanvasElement {
	const left = PAD + 150; // after the bottle end
	const width = W - left - PAD;
	const ops: Op[] = [
		(ctx, y) => {
			bottleEnd(ctx, PAD + 58, y + 62, 58, w);
			ctx.font = `600 34px ${FONT}`;
			let yy = y + 30;
			for (const line of wrap(ctx, w.producer.toUpperCase(), width)) {
				text(ctx, style, line, left, yy, `600 34px ${FONT}`, 'soft', 4);
				yy += 44;
			}
			ctx.font = `800 76px ${FONT}`;
			yy += 34;
			for (const line of wrap(ctx, w.cuvee || w.appellation || w.producer, width)) {
				text(ctx, style, line, left, yy, `800 76px ${FONT}`, 'ink');
				yy += 84;
			}
			text(ctx, style, w.vintage, left, yy, `300 76px ${FONT}`, 'ink');
			yy += 54;
			if (w.cuvee && w.appellation) {
				ctx.font = `500 36px ${FONT}`;
				for (const line of wrap(ctx, w.appellation, width)) {
					text(ctx, style, line, left, yy, `500 36px ${FONT}`, 'soft');
					yy += 46;
				}
			}
			return Math.max(yy, y + 130);
		},
		(ctx, y) => {
			if (!w.rating) return y;
			y += 120;
			text(ctx, style, String(w.rating), left, y, `800 140px ${FONT}`, 'ink');
			ctx.font = `800 140px ${FONT}`;
			const wr = ctx.measureText(String(w.rating)).width;
			text(ctx, style, '/100', left + wr + 14, y, `500 44px ${FONT}`, 'soft');
			return y + 10;
		},
		footer(style, [when, where].filter(Boolean).join(' · '))
	];
	return render(style, ops);
}

/** A tasting session: the evening's wines, in order, each with its score */
export function sessionSticker(wines: StickerWine[], when: string, where: string, style: Style): HTMLCanvasElement {
	const ops: Op[] = [
		(ctx, y) => {
			ctx.font = `800 64px ${FONT}`;
			let yy = y + 56;
			for (const line of wrap(ctx, where || when, W - 2 * PAD)) {
				text(ctx, style, line, PAD, yy, `800 64px ${FONT}`, 'ink');
				yy += 72;
			}
			if (where) text(ctx, style, when, PAD, yy - 10, `500 36px ${FONT}`, 'soft');
			yy += where ? 40 : 0;
			// the evening as a row of bottle ends
			wines.forEach((w, i) => bottleEnd(ctx, PAD + 26 + i * 64, yy + 26, 24, w));
			return yy + 86;
		},
		...wines.map(
			(w): Op =>
				(ctx, y) => {
					const right = W - PAD;
					const scoreW = w.rating ? 120 : 0;
					const left = PAD + 70;
					bottleEnd(ctx, PAD + 22, y + 28, 22, w);
					ctx.font = `700 40px ${FONT}`;
					let yy = y + 40;
					const name = [w.producer, w.cuvee].filter(Boolean).join(' · ');
					for (const line of wrap(ctx, name, right - left - scoreW - 20)) {
						text(ctx, style, line, left, yy, `700 40px ${FONT}`, 'ink');
						yy += 48;
					}
					text(ctx, style, [w.vintage, w.appellation].filter(Boolean).join(' · '), left, yy - 4, `500 32px ${FONT}`, 'soft');
					if (w.rating) {
						ctx.font = `800 56px ${FONT}`;
						const ws = ctx.measureText(String(w.rating)).width;
						text(ctx, style, String(w.rating), right - ws, y + 52, `800 56px ${FONT}`, 'ink');
					}
					return yy + 30;
				}
		),
		footer(style, `${wines.length} wine${wines.length === 1 ? '' : 's'}`)
	];
	return render(style, ops);
}

export const toBlob = (canvas: HTMLCanvasElement) =>
	new Promise<Blob>((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('No image'))), 'image/png'));

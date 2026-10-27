/**
 * Share stickers, Strava-style: a PNG to lay over a photo in an Instagram story. One tasting (the wine and your note)
 * or a tasting session (the evening's wines, each with its note). Framed like the app's tasting cards: the evening's
 * palette along the top (a segment per wine in its region's colour), the place and date, then the wines. Transparent
 * with white or dark text, or a solid card. Drawn on a canvas in the browser, 1080 px wide (a story's width).
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
	/** your tasting note */
	notes: string;
}

const W = 1080;
const PAD = 64;
const FONT = '"Inter", "Segoe UI", system-ui, -apple-system, Roboto, sans-serif';
type Ctx = CanvasRenderingContext2D & { letterSpacing?: string };

function palette(style: Style) {
	return style === 'dark'
		? { ink: '#1b1716', soft: 'rgba(27,23,22,0.66)', shadow: 'rgba(255,255,255,0.35)', card: null, band: null, rule: 'rgba(27,23,22,0.28)', edge: null }
		: style === 'card'
			? { ink: '#f6f1ee', soft: 'rgba(246,241,238,0.66)', shadow: null, card: '#1f1c22', band: '#28252c', rule: 'rgba(246,241,238,0.14)', edge: 'rgba(246,241,238,0.16)' }
			: { ink: '#ffffff', soft: 'rgba(255,255,255,0.8)', shadow: 'rgba(0,0,0,0.5)', card: null, band: null, rule: 'rgba(255,255,255,0.42)', edge: null };
}

/** Lines of text no wider than max (words kept whole); past `most` lines, the last ends with … */
function wrap(ctx: Ctx, text: string, max: number, most = Infinity): string[] {
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
	if (lines.length > most) {
		const kept = lines.slice(0, most);
		let last = kept[most - 1];
		while (last && ctx.measureText(`${last}…`).width > max) last = last.replace(/\s*\S+$/, '');
		kept[most - 1] = `${last}…`;
		return kept;
	}
	return lines;
}

/** A bottle seen end-on, as everywhere in WineLib: its region's colour, the wine's colour as the cork */
function bottleEnd(ctx: Ctx, x: number, y: number, r: number, w: Pick<StickerWine, 'region' | 'color'>) {
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

function text(ctx: Ctx, style: Style, s: string, x: number, y: number, font: string, color: 'ink' | 'soft', spacing = 0) {
	const p = palette(style);
	ctx.font = font;
	ctx.fillStyle = p[color];
	ctx.textBaseline = 'alphabetic';
	ctx.letterSpacing = `${spacing}px`;
	if (p.shadow) {
		ctx.shadowColor = p.shadow;
		ctx.shadowBlur = 12;
	}
	ctx.fillText(s, x, y);
	ctx.shadowColor = 'transparent';
	ctx.shadowBlur = 0;
	ctx.letterSpacing = '0px';
}

function textWidth(ctx: Ctx, s: string, font: string, spacing = 0) {
	ctx.font = font;
	ctx.letterSpacing = `${spacing}px`;
	const w = ctx.measureText(s).width;
	ctx.letterSpacing = '0px';
	return w;
}

type Op = (ctx: Ctx, y: number) => number; // draws at y, returns the next y

const STRIP = 14; // the palette along the top
const BAND = 104; // the place and date

/** The frame of the app's tasting cards, then the body's ops, then the WineLib mark: measured, then drawn */
function render(style: Style, wines: StickerWine[], when: string, where: string, body: Op[], count: string): HTMLCanvasElement {
	const scratch = document.createElement('canvas').getContext('2d') as Ctx;
	let height = STRIP + BAND + 40;
	for (const op of body) height = op(scratch, height);
	height += 150;
	const canvas = document.createElement('canvas');
	canvas.width = W;
	canvas.height = Math.ceil(height);
	const ctx = canvas.getContext('2d') as Ctx;
	const p = palette(style);
	const R = 40;

	// The card (solid style): its body, its band, its edge; the others are transparent
	ctx.save();
	ctx.beginPath();
	ctx.roundRect(0, 0, W, canvas.height, R);
	ctx.clip();
	if (p.card) {
		ctx.fillStyle = p.card;
		ctx.fillRect(0, 0, W, canvas.height);
		ctx.fillStyle = p.band!;
		ctx.fillRect(0, STRIP, W, BAND);
		ctx.fillStyle = p.rule;
		ctx.fillRect(0, STRIP + BAND, W, 2);
	}
	// The evening's palette: a segment per wine, in its region's colour, in the order poured
	const seg = W / wines.length;
	wines.forEach((w, i) => {
		ctx.fillStyle = regionColor(w.region) ?? FALLBACK_REGION;
		ctx.fillRect(i * seg + (i ? 2 : 0), 0, seg - (i ? 2 : 0), STRIP);
	});
	ctx.restore();
	if (p.edge) {
		ctx.strokeStyle = p.edge;
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.roundRect(1, 1, W - 2, canvas.height - 2, R);
		ctx.stroke();
	}

	// The band: the place, the date
	const bandY = STRIP + BAND / 2 + 14;
	const dateFont = `500 34px ${FONT}`;
	const dw = textWidth(ctx, when, dateFont);
	ctx.font = `700 40px ${FONT}`;
	const placeLine = wrap(ctx, where || ' ', W - 2 * PAD - dw - 30, 1)[0];
	text(ctx, style, placeLine, PAD, bandY, `700 40px ${FONT}`, 'ink');
	text(ctx, style, when, W - PAD - dw, bandY, dateFont, 'soft');
	if (!p.card) {
		ctx.fillStyle = p.rule;
		ctx.fillRect(PAD, STRIP + BAND, W - 2 * PAD, 2);
	}

	let y = STRIP + BAND + 40;
	for (const op of body) y = op(ctx, y);

	// The foot: how many, and the small WineLib mark
	y += 40;
	ctx.fillStyle = p.rule;
	ctx.fillRect(PAD, y, W - 2 * PAD, 2);
	y += 62;
	if (count) text(ctx, style, count, PAD, y, `500 30px ${FONT}`, 'soft');
	const markFont = `700 30px ${FONT}`;
	text(ctx, style, 'WINELIB', W - PAD - textWidth(ctx, 'WINELIB', markFont, 6), y, markFont, 'soft', 6);
	return canvas;
}

const quoteFont = (size: number) => `italic 400 ${size}px Georgia, "Iowan Old Style", "Times New Roman", serif`;

/** One tasting: the wine large, then your note */
export function tastingSticker(w: StickerWine, when: string, where: string, style: Style): HTMLCanvasElement {
	const left = PAD + 150;
	const width = W - left - PAD;
	const body: Op[] = [
		(ctx, y) => {
			bottleEnd(ctx, PAD + 58, y + 62, 58, w);
			ctx.font = `600 32px ${FONT}`;
			let yy = y + 30;
			for (const line of wrap(ctx, w.producer.toUpperCase(), width, 2)) {
				text(ctx, style, line, left, yy, `600 32px ${FONT}`, 'soft', 4);
				yy += 42;
			}
			ctx.font = `800 70px ${FONT}`;
			yy += 32;
			for (const line of wrap(ctx, w.cuvee || w.appellation || w.producer, width, 3)) {
				text(ctx, style, line, left, yy, `800 70px ${FONT}`, 'ink');
				yy += 78;
			}
			text(ctx, style, w.vintage, left, yy, `300 70px ${FONT}`, 'ink');
			yy += 52;
			if (w.cuvee && w.appellation) {
				text(ctx, style, w.appellation, left, yy, `500 34px ${FONT}`, 'soft');
				yy += 44;
			}
			return Math.max(yy, y + 130);
		},
		(ctx, y) => {
			if (!w.notes) return y;
			ctx.font = quoteFont(40);
			let yy = y + 40;
			for (const line of wrap(ctx, `“${w.notes.replace(/\s+/g, ' ').trim()}”`, W - 2 * PAD, 9)) {
				yy += 52;
				text(ctx, style, line, PAD, yy, quoteFont(40), 'ink');
			}
			return yy;
		}
	];
	return render(style, [w], when, where, body, '');
}

/** A tasting session: the evening's wines in the order poured, each with its note (shortened) */
export function sessionSticker(wines: StickerWine[], when: string, where: string, style: Style): HTMLCanvasElement {
	const left = PAD + 70;
	const width = W - left - PAD;
	const body: Op[] = wines.map(
		(w, i): Op =>
			(ctx, y) => {
				if (i) y += 24;
				bottleEnd(ctx, PAD + 22, y + 28, 22, w);
				ctx.font = `700 40px ${FONT}`;
				let yy = y + 40;
				for (const line of wrap(ctx, [w.producer, w.cuvee].filter(Boolean).join(' · '), width, 2)) {
					text(ctx, style, line, left, yy, `700 40px ${FONT}`, 'ink');
					yy += 48;
				}
				text(ctx, style, [w.vintage, w.appellation].filter(Boolean).join(' · '), left, yy - 4, `500 32px ${FONT}`, 'soft');
				yy += 4;
				if (w.notes) {
					ctx.font = quoteFont(32);
					for (const line of wrap(ctx, `“${w.notes.replace(/\s+/g, ' ').trim()}”`, width, 2)) {
						yy += 42;
						text(ctx, style, line, left, yy, quoteFont(32), 'soft');
					}
				}
				return yy + 12;
			}
	);
	return render(style, wines, when, where, body, `${wines.length} wine${wines.length === 1 ? '' : 's'}`);
}

export const toBlob = (canvas: HTMLCanvasElement) =>
	new Promise<Blob>((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('No image'))), 'image/png'));

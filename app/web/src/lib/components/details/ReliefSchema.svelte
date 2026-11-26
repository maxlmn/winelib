<script lang="ts">
	/** A vineyard's lie of the land (routers/relief.py), drawn small: a compass with the way it faces, and its hillside
	 * side on at its true slope, between its lowest and highest points; the same in words beside them. Asked for once
	 * shown (worked out from the outline the first time, then kept); nothing shown without an outline, or when the
	 * terrain tiles can't be reached. */
	import { quietly, request } from '#lib/api/http.ts';
	import { reliefWorkedOut } from '#lib/contours.svelte.ts';
	import { links } from '#lib/links.ts';

	type Relief = { elevation: { min: number; mean: number; max: number }; slope: { median: number; steep: number }; aspect: number | null; facing: string | null };

	let { vineyardId, name = null, color = null, rev = 0 }: { vineyardId: number; name?: string | null; color?: string | null; rev?: number } = $props();

	let relief = $state<Relief | null>(null);
	$effect(() => {
		const id = vineyardId;
		void rev;
		relief = null;
		const abort = new AbortController(); // an answer for an earlier vineyard or outline never lands
		request<Relief | null>(`/api/vineyards/${id}/relief`, { signal: abort.signal })
			.then((r) => {
				relief = r;
				if (r) reliefWorkedOut(id); // the maps showing it ask for its contours (now there) again
			})
			.catch(quietly);
		return () => abort.abort();
	});

	const WORDS: Record<string, string> = { N: 'north', E: 'east', S: 'south', W: 'west' };
	// "NNE": north-north-east (a three-letter point is one 22.5° step from its two-letter neighbour)
	const spelled = (p: string) => p.split('').map((c) => WORDS[c]).join('-');
	const facing = (r: Relief) => (r.facing ? `Faces ${r.facing}` : r.slope.median < 2 ? 'Flat' : 'Faces several ways');

	// The compass: a wedge 45° wide on the way it faces (0 north, clockwise), in SVG's y-down coordinates
	const R = 19;
	const C = 24;
	const at = (deg: number, r: number) => [C + r * Math.sin((deg * Math.PI) / 180), C - r * Math.cos((deg * Math.PI) / 180)];
	const wedge = (deg: number) => {
		const [x1, y1] = at(deg - 22.5, R);
		const [x2, y2] = at(deg + 22.5, R);
		return `M${C},${C} L${x1.toFixed(1)},${y1.toFixed(1)} A${R},${R} 0 0 1 ${x2.toFixed(1)},${y2.toFixed(1)} Z`;
	};

	// The hillside, side on: its true slope (the median), the base shortened when steep so it fits
	const W = 70;
	const H = 34;
	const side = (deg: number) => {
		const t = Math.tan((Math.max(deg, 0.5) * Math.PI) / 180);
		const base = Math.min(W, H / t);
		return { base, rise: base * t };
	};
</script>

{#if relief}
	{@const s = side(relief.slope.median)}
	{@const tint = color ?? 'var(--accent)'}
	<div class="relief" title="Worked out from its outline over Mapterhorn's open terrain tiles">
		<svg class="compass" viewBox="0 0 48 48" width="48" height="48" role="img"
			aria-label={relief.facing ? `Faces ${spelled(relief.facing)}` : 'No single aspect'}>
			<circle cx={C} cy={C} r={R} class="ring" class:flat={relief.aspect === null} />
			{#if relief.aspect !== null}<path d={wedge(relief.aspect)} fill={tint} fill-opacity="0.75" />{/if}
			<line x1={C} y1={C - R} x2={C} y2={C - R + 4} class="tick" />
			<text x={C} y="4.5" class="n">N</text>
			<circle cx={C} cy={C} r="1.6" class="dot" />
		</svg>
		<svg class="slope" viewBox="0 0 {W + 36} 56" width={W + 36} height="56" role="img"
			aria-label={`${Math.round(relief.slope.median)}° slope, from ${relief.elevation.min} to ${relief.elevation.max} m`}>
			<!-- the hillside: up from its lowest point (bottom left) to its highest, the ground under it -->
			<path d={`M2,44 L${2 + s.base},${44 - s.rise} L${2 + s.base},44 Z`} fill={tint} fill-opacity="0.25" />
			<line x1="2" y1="44" x2={2 + s.base} y2={44 - s.rise} stroke={tint} stroke-width="2" stroke-linecap="round" />
			<line x1="0" y1="44" x2={W + 4} y2="44" class="ground" />
			<text x={5 + s.base} y={Math.max(44 - s.rise + 1, 9)} class="lbl">{relief.elevation.max} m</text>
			<text x="0" y="54" class="lbl muted">{relief.elevation.min} m</text>
		</svg>
		<div class="words">
			{#if name}<a href={links.vineyard(vineyardId)}>{name}</a>{/if}
			<div>{facing(relief)} · <span class="num">{relief.elevation.min}–{relief.elevation.max} m</span></div>
			<div><span class="num">{Math.round(relief.slope.median)}°</span> slope<span class="muted">, {Math.round(relief.slope.steep)}° at its steepest</span></div>
		</div>
	</div>
{/if}

<style>
	.relief {
		display: flex;
		align-items: center;
		gap: 10px;
		margin-top: 10px;
		font-size: 13px;
	}
	svg {
		flex: none;
		overflow: visible;
	}
	.ring {
		fill: none;
		stroke: var(--border);
		stroke-width: 1.5;
	}
	.ring.flat {
		stroke-dasharray: 3 2;
	}
	.tick,
	.ground {
		stroke: var(--muted);
		stroke-width: 1;
	}
	.dot {
		fill: var(--muted);
	}
	text {
		fill: var(--text);
		font-size: 9px;
		font-variant-numeric: tabular-nums;
	}
	.n {
		text-anchor: middle;
		fill: var(--muted);
		font-size: 7px;
		font-weight: 600;
	}
	.lbl.muted {
		fill: var(--muted);
	}
	.words {
		display: flex;
		flex-direction: column;
		gap: 1px;
		line-height: 1.35;
	}
	.words a {
		color: var(--link);
		font-weight: 600;
	}
</style>

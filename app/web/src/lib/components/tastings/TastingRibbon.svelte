<script lang="ts">
	import RegionStrip from '#lib/components/RegionStrip.svelte';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { labelThumb } from '#lib/pips.ts';
	import { links } from '#lib/links.ts';
	import { barWidth } from '#lib/format.ts';
	import { fmtDay, wineName } from './journal.ts';
	import type { Tasting } from '#lib/api/tastings.ts';

	/** onwine: a wine pointed at along the line (hovered, dragged over, or reached by the replay), e.g. for a map to
	 * show it; `shown`: the wine shown there, raised in the line */
	let {
		tastings,
		label = 'Every wine, oldest on the left: its region’s color, its own color below',
		onwine,
		shown = null
	}: { tastings: Tasting[]; label?: string; onwine?: (t: Tasting, now: boolean) => void; shown?: number | null } = $props();

	const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
	const GAP = 2; // RegionStrip's gap between bars

	// Every wine tasted in one line, oldest on the left, as poured within a day: a bar each in its region's color,
	// its own color on the track below
	const sorted = $derived([...tastings].sort((a, b) => a.date.localeCompare(b.date) || (a.seq ?? 0) - (b.seq ?? 0)));
	const pips = $derived(
		sorted.map((t) => ({
			region: t.region,
			color: t.color,
			format: t.format,
			label: wineName(t),
			sub: `${fmtDay(t.date)} · ${t.location}`,
			href: links.tasting(t.id),
			image: t.label ? labelThumb(t.label.url) : null,
			key: t.id
		}))
	);
	const byId = $derived(new Map(sorted.map((t) => [t.id, t])));

	// The replay: the year's wines one after another, oldest first (from the one shown when it's in the line), a few
	// seconds each, the map following; stopped by its button, the end, or the pointer on the line
	const STEP_MS = 2200;
	let playing = $state(false);
	let timer: ReturnType<typeof setInterval> | undefined;
	function step(i: number) {
		const t = sorted[i];
		if (!t) return stop();
		onwine?.(t, true);
		// kept in view in the line
		const el = scroller?.querySelectorAll<HTMLElement>('.pip')[i];
		if (el && scroller) {
			const r = el.getBoundingClientRect(), s = scroller.getBoundingClientRect();
			if (r.left < s.left + 20 || r.right > s.right - 20) scroller.scrollBy({ left: r.left - s.left - s.width / 2, behavior: 'smooth' });
		}
	}
	function play() {
		if (playing) return stop();
		playing = true;
		const at = sorted.findIndex((t) => t.id === shown);
		let i = at >= 0 && at < sorted.length - 1 ? at + 1 : 0;
		step(i);
		timer = setInterval(() => {
			i += 1;
			if (i >= sorted.length) stop();
			else step(i);
		}, STEP_MS);
	}
	function stop() {
		playing = false;
		clearInterval(timer);
	}
	$effect(() => () => clearInterval(timer));

	// Dragged along (a finger, or a mouse button held): the wine under the pointer, the line not scrolled meanwhile
	let dragging = false;
	function under(e: PointerEvent) {
		const el = (document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null)?.closest<HTMLElement>('.pip');
		if (!el || !scroller?.contains(el)) return;
		const i = [...scroller.querySelectorAll('.pip')].indexOf(el);
		if (sorted[i]) onwine?.(sorted[i], false);
	}

	// Under the line: each year, and each month where there's room for it
	const marks = $derived.by(() => {
		const out: { x: number; text: string; year: boolean }[] = [];
		let x = 0;
		let last = '';
		let lastLabel = -Infinity;
		for (const t of sorted) {
			const month = t.date.slice(0, 7);
			if (month !== last) {
				const year = month.slice(0, 4) !== last.slice(0, 4);
				if (year || x - lastLabel >= 30) {
					// a new year too close to the label before it (a year's last days at the start): it takes that place
					if (year && out.length && x - lastLabel < 30) out.pop();
					out.push({ x, text: year ? month.slice(0, 4) : MONTHS[Number(month.slice(5)) - 1], year });
					lastLabel = x;
				}
				last = month;
			}
			x += 5 * Math.min(2, barWidth(t.format) / 4) + GAP; // a bar's width (RegionStrip's tracks)
		}
		return out;
	});

	// Opens on the latest wines: scroll left for older ones
	let scroller = $state<HTMLDivElement>();
	$effect(() => {
		void pips;
		if (scroller) scroller.scrollLeft = scroller.scrollWidth;
	});
</script>

{#if pips.length > 1}
	<div class="ribbon card">
		<div class="head">
			<div class="label">{label}</div>
			{#if onwine}
				<button class="play" class:on={playing} onclick={play} title={playing ? 'Stop the replay' : 'Replay the year on the map, wine by wine'}>
					{playing ? '■ Stop' : '▶ Replay'}
				</button>
			{/if}
		</div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="scroller"
			class:drag={!!onwine}
			bind:this={scroller}
			onpointerdown={(e) => {
				if (!onwine) return;
				stop();
				dragging = true;
				under(e);
			}}
			onpointermove={(e) => dragging && under(e)}
			onpointerup={() => (dragging = false)}
			onpointercancel={() => (dragging = false)}
			onpointerleave={() => (dragging = false)}
		>
			<div class="line">
				<RegionStrip
					{pips}
					height={18}
					active={shown}
					onhover={(k) => {
						const t = k == null ? null : byId.get(Number(k));
						if (t && !playing && appSettings.map_follow === 'hover') onwine?.(t, false);
					}}
				/>
				<div class="marks">
					{#each marks as m (m.x)}<span class="mark num" class:year={m.year} style:left="{m.x}px">{m.text}</span>{/each}
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.ribbon {
		padding: 12px 16px 8px;
		margin-bottom: 14px;
	}
	.head {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		margin-bottom: 8px;
	}
	.label {
		flex: 1;
		font-size: 12px;
		color: var(--muted);
	}
	.play {
		flex: none;
		padding: 2px 9px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--surface);
		color: var(--text);
		font: inherit;
		font-size: 12px;
		cursor: pointer;
	}
	.play.on {
		background: var(--accent);
		border-color: var(--accent);
		color: var(--on-accent);
	}
	/* dragged along on a phone: the finger follows the wines, it doesn't scroll the line */
	.scroller.drag :global(.strip) {
		touch-action: none;
	}
	.scroller {
		overflow-x: auto;
		padding-bottom: 6px;
	}
	.line {
		width: max-content;
		min-width: 100%;
	}
	.line :global(.strip) {
		flex-wrap: nowrap;
	}
	.marks {
		position: relative;
		height: 18px;
		margin-top: 4px;
		border-top: 1px solid var(--border);
	}
	.mark {
		position: absolute;
		top: 0;
		padding: 3px 0 0 3px;
		border-left: 1px solid var(--border);
		font-size: 11px;
		color: var(--muted);
		white-space: nowrap;
	}
	.mark.year {
		color: var(--text);
		font-weight: 600;
		border-left-color: var(--muted);
	}
</style>

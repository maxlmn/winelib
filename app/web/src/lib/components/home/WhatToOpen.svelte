<script lang="ts">
	import { labelTip } from '#lib/labelTip.svelte.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { appSettings, groupOrder } from '#lib/settings.svelte.ts';
	/** "What should I open?" (and what to drink soon): a few bottles from the cellar for the evening: first those a
	 * list asks you to taste (an entry not ticked yet), then those past their window, then the ready ones whose window
	 * closes soonest. Under them, the cellar's bottles by maturity. */
	import { onMount } from 'svelte';
	import { FALLBACK_REGION, typeColor } from '#lib/colors.ts';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { links } from '#lib/links.ts';
	import { money } from '#lib/format.ts';
	import MaturityBadge from '#lib/components/MaturityBadge.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { plural } from '#lib/format.ts';
	import { windowLabel } from '#lib/maturity.ts';
	import type { Bottle } from '#lib/types.ts';

	/** onwine: a bottle pointed at (hovered, or tapped outside its links), e.g. for a map to show its wine; `shown`
	 * marks the bottle shown there */
	/** compact: the home page's "Tonight, why not": one bottle (Another for the next), the colours to pick from and
	 * the lie of its vineyard; the other filters are the cellar's */
	let {
		bottles,
		totals = null,
		onwine,
		shown = null,
		compact = false
	}: {
		bottles: Bottle[];
		totals?: { ready: number; young: number; past: number; unknown: number } | null;
		onwine?: (b: Bottle) => void;
		shown?: number | null;
		compact?: boolean;
	} = $props();

	const SHOWN = 6;
	const MOSAIC = 24;
	// Per wine in the cellar, the lists still waiting for it
	let onLists = $state<Record<string, { list_id: number; list: string; note: string | null; waiting: boolean }[]>>({});
	let listsOnly = $state(false);
	let color = $state('');
	let region = $state('');
	let style = $state(''); // "something fresh tonight"
	let maxPrice = $state<number | null>(null);
	let includeYoung = $state(false);
	let seed = $state(0); // "Another idea" reshuffles the ties
	let step = $state(0); // compact: "Another" steps to the next bottle of the order (all of them in turn)

	// Where to pick from: a storage group (the first in Settings' order by default, usually home) or anywhere ('*');
	// remembered on this device
	const STORAGE_KEY = 'winelib-open-storage';
	let storage = $state('');
	const groups = $derived(groupOrder().filter((g) => bottles.some((b) => b.location_group === g)));
	const from = $derived(storage === '*' || groups.includes(storage) ? storage : (groups[0] ?? '*'));
	function pickStorage(value: string) {
		storage = value;
		region = ''; // its regions differ
		try {
			localStorage.setItem(STORAGE_KEY, value);
		} catch {
			// not remembered, still applied
		}
	}

	onMount(async () => {
		try {
			storage = localStorage.getItem(STORAGE_KEY) ?? '';
		} catch {
			// private mode: the default
		}
		const r = await fetch('/api/lists/in-cellar');
		if (r.ok) onLists = await r.json();
	});

	const here = $derived(from === '*' ? bottles : bottles.filter((b) => b.location_group === from));
	const colors = $derived([...new Set(here.map((b) => b.color).filter(Boolean))].sort() as string[]);
	const regions = $derived([...new Set(here.map((b) => b.region))].sort((a, b) => a.localeCompare(b)));
	const styles = $derived([...new Set(here.flatMap((b) => b.tags ?? []))].sort((a, b) => a.localeCompare(b)));

	// A stable pseudo-random order per bottle and seed, to vary the picks among equals
	const jitter = (id: number) => Math.abs(Math.sin(id * 12.9898 + seed * 78.233)) % 1;
	// Past its window first (open it before it fades), then ready with the window closing soonest, then unknown
	const rank = (b: Bottle) =>
		b.maturity === 'past' ? 0 : b.maturity === 'ready' ? 1 + Math.min((b.drink_to ?? 9999) - new Date().getFullYear(), 50) / 100 : b.maturity === null ? 2 : 3;

	// The lists naming it; those still waiting for it (an entry not ticked) first, and they're what's suggested
	const lists = (b: Bottle) => onLists[b.wine_id] ?? [];
	const waiting = (b: Bottle) => lists(b).some((l) => l.waiting);
	// The preferred critic's score (Settings) as a pill: "RP 95"
	const preferred = (b: Bottle) => (b.score ? ((b.scores ?? '').split(' · ').find((p) => p.endsWith(` ${b.score}`)) ?? b.score) : null);
	const anyListed = $derived(here.some(waiting));
	const ordered = $derived(
		here
			.filter((b) => !listsOnly || waiting(b))
			.filter((b) => (!color || b.color === color) && (!region || b.region === region))
			.filter((b) => !style || (b.tags ?? []).includes(style))
			.filter((b) => !maxPrice || b.market_base <= maxPrice)
			.filter((b) => includeYoung || b.maturity !== 'young')
			.map((b) => ({ b, score: rank(b) + jitter(b.bottle_id) * 0.6 - (waiting(b) ? 4 : 0) }))
			.sort((x, y) => x.score - y.score)
			.map((x) => x.b)
	);
	// The one bottle (compact), stepping through them all; else the first few, reshuffled among equals
	const picks = $derived(compact ? (ordered.length ? [ordered[step % ordered.length]] : []) : ordered.slice(0, SHOWN));
	const label = (b: Bottle) => b.cuvee || [b.appellation, b.varietal].filter(Boolean).join(' · ');

	// compact: the lie of the land of the bottle suggested (its vineyard's relief, when it has an outline worked out)
	type Lie = { elevation: { min: number; max: number }; slope: { median: number }; facing: string | null };
	let lie = $state<Lie | null>(null);
	const lieOf = new Map<number, Promise<Lie | null>>();
	async function lieFor(wineId: number): Promise<Lie | null> {
		try {
			const shapes = await (await fetch(`/api/wines/${wineId}/shapes`)).json();
			const vineyard = shapes?.vineyards?.features?.[0]?.properties?.id;
			if (!vineyard) return null;
			const r = await fetch(`/api/vineyards/${vineyard}/relief`);
			return r.ok ? ((await r.json()) as Lie | null) : null;
		} catch {
			return null;
		}
	}
	$effect(() => {
		const b = compact ? picks[0] : undefined;
		lie = null;
		if (!b) return;
		let stale = false;
		if (!lieOf.has(b.wine_id)) lieOf.set(b.wine_id, lieFor(b.wine_id));
		lieOf.get(b.wine_id)!.then((l) => !stale && (lie = l));
		return () => (stale = true);
	});
	const lieLabel = (l: Lie) =>
		[l.facing ? `Faces ${l.facing}` : null, `${Math.round(l.elevation.min)}–${Math.round(l.elevation.max)} m`, `${Math.round(l.slope.median)}°`]
			.filter(Boolean)
			.join(' · ');
</script>

<section class="card open" class:compact>
	<div class="sec-head">
		<h2>{compact ? 'Tonight, why not' : 'What should I open?'}</h2>
		{#if !compact}<a class="cellar-link" href={links.cellar({ view: 'list' })}>The cellar →</a>{/if}
		<button class="link" onclick={() => (compact ? (step += 1) : (seed += 1))}>{compact ? 'Another ↻' : 'Another idea ↻'}</button>
	</div>
	<div class="filters">
		<div class="chips">
			{#if anyListed}
				<button class="chip" class:on={listsOnly} onclick={() => (listsOnly = !listsOnly)} title="Bottles a list asks you to taste">
					<Icon name="bookmark" size={11} />On a list
				</button>
			{/if}
			<button class="chip" class:on={!color} onclick={() => ((color = ''), (step = 0))}>Any</button>
			{#each colors as c (c)}
				<button class="chip" class:on={color === c} onclick={() => ((color = c), (step = 0))}>
					<span class="dot" style:background={typeColor(c)}></span>{c}
				</button>
			{/each}
		</div>
		{#if !compact}<div class="row">
			<select value={from} onchange={(e) => pickStorage(e.currentTarget.value)} aria-label="Storage">
				{#each groups as g (g)}<option value={g}>{g}</option>{/each}
				<option value="*">Anywhere</option>
			</select>
			<select bind:value={region} aria-label="Region">
				<option value="">Any region</option>
				{#each regions as r (r)}<option value={r}>{regionLabel(r)}</option>{/each}
			</select>
			{#if styles.length}
				<select bind:value={style} aria-label="Style">
					<option value="">Any style</option>
					{#each styles as s (s)}<option value={s}>{s}</option>{/each}
				</select>
			{/if}
			<label class="price">
				up to
				<input type="number" min="0" step="10" placeholder="any" value={maxPrice ?? ''}
					oninput={(e) => (maxPrice = e.currentTarget.value ? +e.currentTarget.value : null)} aria-label="Maximum market price ({appSettings.currency})" />
				{appSettings.currency}
			</label>
			<label class="young"><input type="checkbox" bind:checked={includeYoung} /> include too young</label>
		</div>{/if}
	</div>
	{#if picks.length}
		<ul>
			{#each picks as b (b.bottle_id)}
				<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
				<li
					class:points={!!onwine}
					class:shown={onwine && shown === b.bottle_id}
					onpointerenter={(e) => e.pointerType === 'mouse' && appSettings.map_follow === 'hover' && onwine?.(b)}
					onclick={(e) => !(e.target as HTMLElement).closest('a, button, input, select') && onwine?.(b)}
				>
					<span class="end" use:labelTip={b.label}>
						<BottleEnd region={regionColor(b.region) ?? FALLBACK_REGION} color={b.color} format={b.format} size={11} title={b.label ? undefined : `${regionLabel(b.region)} · ${b.color ?? ''}`} />
					</span>
					<div class="main">
						<a href={links.bottle(b.bottle_id)}>{b.producer}{label(b) ? ` – ${label(b)}` : ''}</a>
						<span class="muted num">{b.vintage}</span>
						{#if preferred(b)}<span class="critic num" title="Critic’s score">{preferred(b)}</span>{/if}
						<div class="muted small">
							{regionLabel(b.region)} · <span class="loc">{b.location}</span>{!compact && (b.drink_from || b.drink_to) ? ` · drink ${windowLabel(b.drink_from, b.drink_to)}` : ''}{b.market_base ? ` · ${money(b.market_base)}` : ''}
							<span class="mosaic" title={plural(b.qty, 'bottle')}>
								{#each { length: Math.min(b.qty, MOSAIC) } as _, i (i)}<BottleEnd region={regionColor(b.region) ?? FALLBACK_REGION} color={b.color} format={b.format} size={8} />{/each}
							</span>
						</div>
						{#if compact && lie}<div class="muted small lie">{lieLabel(lie)}</div>{/if}
						{#if lists(b).length}
							<div class="on-lists small">
								<Icon name="bookmark" size={11} />
								{#each lists(b) as l, i (l.list_id)}{i ? ', ' : ''}<a href={links.list(l.list_id)} class:done={!l.waiting} title={l.waiting ? 'Not ticked on this list yet' : 'Already ticked on this list'}>{l.list}</a>{#if l.note}<span class="muted">&nbsp;({l.note})</span>{/if}{/each}
							</div>
						{/if}
					</div>
					{#if b.maturity && !compact}
						<MaturityBadge maturity={b.maturity} from={b.drink_from} to={b.drink_to} />
					{/if}
				</li>
			{/each}
		</ul>
	{:else if bottles.length === 0}
		<p class="muted">Your cellar is empty: <a href={links.newBottle()}>add a bottle</a></p>
	{:else}
		<p class="muted">Nothing in the cellar matches: loosen the filters.</p>
	{/if}
	{#if compact}<a class="more-link small" href={links.cellar({ view: 'list' })}>More to choose from in the cellar →</a>{/if}
	{#if totals}
		<p class="muted small totals">
			{totals.ready} bottles ready · {totals.young} too young · {totals.past} past{#if totals.unknown} · {totals.unknown} without a window{/if}
		</p>
	{/if}
</section>

<style>
	.open {
		padding: 16px 18px;
	}
	.cellar-link {
		margin-left: auto;
		font-size: 13px;
		color: var(--link);
	}
	.more-link {
		display: inline-block;
		margin-top: 8px;
		color: var(--link);
	}
	.compact .sec-head h2 {
		margin-right: auto;
	}
	.totals {
		margin: 8px 0 0;
	}
	.mosaic {
		display: inline-flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 2px;
		vertical-align: middle;
		margin-left: 4px;
	}
	.on-lists {
		color: var(--accent);
	}
	.on-lists :global(svg) {
		vertical-align: -1px;
		margin-right: 3px;
	}
	.on-lists a {
		color: var(--accent);
	}
	.on-lists a.done {
		color: var(--muted);
	}
	.critic {
		display: inline-block;
		font-size: 11px;
		font-weight: 600;
		line-height: 16px;
		color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
		border-radius: 8px;
		padding: 0 6px;
		margin-left: 4px;
		white-space: nowrap;
		vertical-align: 1px;
	}
	.sec-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 10px;
	}
	h2 {
		margin: 0 0 10px;
		font-size: 15px;
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		color: var(--accent);
		cursor: pointer;
		font-size: 13px;
	}
	.filters {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-bottom: 10px;
	}
	.chips,
	.row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 10px;
		font-size: 13px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 3px 10px;
		border: 1px solid var(--border);
		border-radius: 12px;
		background: var(--surface);
		font-size: 12px;
		cursor: pointer;
	}
	.chip.on {
		border-color: var(--accent);
		background: var(--accent-soft);
		color: var(--accent);
	}
	select,
	.price input {
		padding: 4px 8px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface-2);
		font-size: 13px;
	}
	select {
		max-width: 180px;
	}
	.price input {
		width: 80px;
	}
	.price,
	.young {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		color: var(--muted);
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 0;
		border-top: 1px solid var(--border);
		font-size: 13px;
	}
	.main {
		flex: 1;
		min-width: 0;
	}
	.main a:hover {
		color: var(--accent);
	}
	.small {
		font-size: 12px;
	}
	.end {
		display: flex;
		flex: none;
		align-self: center;
	}
	.dot {
		width: 9px;
		height: 9px;
		border-radius: 50%;
		flex: none;
		display: inline-block;
	}
	/* a wine that shows itself on a map when pointed at (the home page's); the one shown on a soft tint */
	li.points {
		margin-inline: -8px;
		padding-inline: 8px;
		border-radius: 6px;
		cursor: pointer;
		transition: background 0.15s;
	}
	li.points:hover {
		background: color-mix(in srgb, var(--accent) 5%, transparent);
	}
	li.shown,
	li.shown:hover {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
	}
</style>

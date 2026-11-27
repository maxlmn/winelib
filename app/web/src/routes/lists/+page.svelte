<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import ListDots from '#lib/components/ListDots.svelte';
	import HomeMap from '#lib/components/home/HomeMap.svelte';
	import { createList, DOT_ORDERS, emptyCriteria, hasCriteria, matches, sortDots, type DotOrder } from '#lib/api/lists.ts';
	import CriteriaBuilder from '#lib/components/CriteriaBuilder.svelte';
	import { links } from '#lib/links.ts';

	let { data } = $props();

	// The lists' order (remembered on this device), the wishlist always first: the closest to done, by name, the most
	// entries, the most bottles in the cellar; then the most tasted, by name
	const LIST_ORDERS = [
		['done', 'Completion'],
		['name', 'Name'],
		['entries', 'Entries'],
		['owned', 'In the cellar']
	] as const;
	type ListOrder = (typeof LIST_ORDERS)[number][0];
	let listOrder = $state<ListOrder>('done');
	type L = (typeof data.lists)[number];
	const rate = (l: L) => (l.entries ? l.tasted / l.entries : 0);
	const by: Record<ListOrder, (a: L, b: L) => number> = {
		done: (a, b) => rate(b) - rate(a),
		name: (a, b) => a.name.localeCompare(b.name),
		entries: (a, b) => b.entries - a.entries,
		owned: (a, b) => b.owned - a.owned
	};
	const lists = $derived(
		[...data.lists].sort(
			(a, b) =>
				Number(b.is_wishlist) - Number(a.is_wishlist) || by[listOrder](a, b) || b.tasted - a.tasted || a.name.localeCompare(b.name)
		)
	);
	// Every mosaic in one order: the lists' own, by note, tasted first... (remembered on this device)
	let order = $state<DotOrder>('list');
	onMount(() => {
		try {
			const saved = localStorage.getItem('winelib-dots-order');
			if (DOT_ORDERS.some(([k]) => k === saved)) order = saved as DotOrder;
			const savedLists = localStorage.getItem('winelib-lists-order');
			if (LIST_ORDERS.some(([k]) => k === savedLists)) listOrder = savedLists as ListOrder;
		} catch {
			/* no storage: not remembered */
		}
	});
	function setListOrder(o: ListOrder) {
		listOrder = o;
		try {
			localStorage.setItem('winelib-lists-order', o);
		} catch {
			/* no storage */
		}
	}
	function setOrder(o: DotOrder) {
		order = o;
		try {
			localStorage.setItem('winelib-dots-order', o);
		} catch {
			/* no storage */
		}
	}
	// Find a list by its name or source, or by an entry (a wine, a producer, a note): the matching bottle ends stay
	// bright, the others fade
	let find = $state('');
	const named = (l: (typeof data.lists)[number]) => matches(find, l.name, l.source);
	const hits = (l: (typeof data.lists)[number]) => l.dots.filter((d) => matches(find, d.label, d.note)).length;
	const found = $derived(find.trim() ? lists.filter((l) => named(l) || hits(l)) : lists);
	const dotsOf = (l: (typeof data.lists)[number]) =>
		sortDots(find.trim() && !named(l) ? l.dots.map((d) => ({ ...d, faded: !matches(find, d.label, d.note) })) : l.dots, order);
	// Columns that each stack their own cards (no gap under a short one beside a tall one): each card, in order, to
	// the shortest column, so the order still reads across; the cards' heights measured once drawn
	const GAP = 14;
	let gridWidth = $state(0);
	let heights = $state<Record<number, number>>({});
	const cols = $derived(Math.max(1, Math.floor((gridWidth + GAP) / (360 + GAP))));
	const columns = $derived.by(() => {
		const out = Array.from({ length: cols }, () => ({ items: [] as L[], h: 0 }));
		for (const l of found) {
			const c = out.reduce((a, b) => (b.h < a.h ? b : a));
			c.items.push(l);
			c.h += (heights[l.id] ?? 220) + GAP;
		}
		return out.map((c) => c.items);
	});
	const pct = (l: { tasted: number; entries: number }) => (l.entries ? Math.round((100 * l.tasted) / l.entries) : 0);
	const milestone = (l: { tasted: number; entries: number }) =>
		!l.entries ? '' : l.tasted === l.entries ? 'Complete' : l.tasted * 2 >= l.entries ? 'Past halfway' : l.tasted ? '' : 'Not started';

	let adding = $state(false);
	let name = $state('');
	let source = $state('');
	let error = $state('');
	// Filled from criteria (tags, colour, region...): once, or live
	let fromCriteria = $state(false);
	let criteria = $state(emptyCriteria());
	let live = $state(false);
	async function create() {
		error = '';
		const filled = fromCriteria && hasCriteria(criteria);
		try {
			const { id } = await createList({
				name, source: source || null, description: null, url: null,
				criteria: filled ? criteria : null, live: filled && live
			});
			goto(links.list(id));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Couldn’t create it';
		}
	}

	// The figures over every list (not only those found)
	const totals = $derived({
		entries: data.lists.reduce((n, l) => n + l.entries, 0),
		tasted: data.lists.reduce((n, l) => n + l.tasted, 0),
		complete: data.lists.filter((l) => l.entries && l.tasted === l.entries).length
	});

	// The map behind: the regions of the lists' entries (every list, or the one hovered), by how many each has
	let hovered = $state<(typeof data.lists)[number] | null>(null);
	const counts = $derived.by(() => {
		const out: Record<string, number> = {};
		for (const l of hovered ? [hovered] : data.lists) for (const d of l.dots) if (d.region) out[d.region] = (out[d.region] ?? 0) + 1;
		return out;
	});
</script>

<svelte:head><title>Lists · WineLib</title></svelte:head>

<!-- Over the map: every list's regions coloured, by how many entries each has; a list's card hovered colours its own -->
<HomeMap full {counts} />

<!-- The title and its figures, the new list button beside; under them the find box and the two orders -->
<div class="page-head lists-head">
	<div class="title-row">
		<div>
			<h1>Lists</h1>
			{#if data.lists.length}
				<p class="stats">
					<span><b class="num">{data.lists.length}</b> {data.lists.length === 1 ? 'list' : 'lists'}</span>
					<span><b class="num">{totals.tasted}</b> of {totals.entries} entries tasted</span>
					{#if totals.complete}<span><b class="num">{totals.complete}</b> complete</span>{/if}
				</p>
			{/if}
		</div>
		<button class="btn icon primary" onclick={() => (adding = !adding)} title={adding ? 'Cancel' : 'New list'} aria-label={adding ? 'Cancel' : 'New list'}>{#if adding}✕{:else}<span class="plus">+</span><Icon name="list" size={15} />{/if}</button>
	</div>
	{#if lists.length || find}
		<input class="find" type="search" bind:value={find} placeholder="Find a list, a wine, a note…" aria-label="Find in the lists" />
		<div class="orders">
			<label class="order">
				<span class="muted">Lists by</span>
				<select value={listOrder} onchange={(e) => setListOrder(e.currentTarget.value as ListOrder)}>
					{#each LIST_ORDERS as [k, label] (k)}<option value={k}>{label}</option>{/each}
				</select>
			</label>
			<label class="order">
				<span class="muted">Mosaics by</span>
				<select value={order} onchange={(e) => setOrder(e.currentTarget.value as DotOrder)}>
					{#each DOT_ORDERS as [k, label] (k)}<option value={k}>{label}</option>{/each}
				</select>
			</label>
		</div>
	{/if}
</div>

{#if adding}
	<form class="new card" onsubmit={(e) => { e.preventDefault(); create(); }}>
		<label><span class="label">Name</span><input bind:value={name} required placeholder="Noble Rot’s wines of the decade" /></label>
		<label><span class="label">Made by</span><input bind:value={source} placeholder="Noble Rot, a critic, you…" /></label>
		<button class="btn primary" disabled={!name.trim()}>Create</button>
		<label class="from"><input type="checkbox" bind:checked={fromCriteria} /> Fill it from criteria: tags, colour, region, grape, vintages…</label>
		{#if fromCriteria}
			<div class="criteria-box">
				<CriteriaBuilder bind:criteria />
				<div class="seg kind" role="group" aria-label="Made once or live">
					<button type="button" class:on={!live} onclick={() => (live = false)}>Made once</button>
					<button type="button" class:on={live} onclick={() => (live = true)}>Live</button>
				</div>
				<p class="muted small">{live ? 'A live list keeps these criteria and shows whatever matches today: a wine tagged tomorrow joins it.' : 'The matching wines become its entries now; edit it like any list afterwards.'}</p>
			</div>
		{/if}
		{#if error}<p class="error">{error}</p>{/if}
	</form>
{/if}

{#if !lists.length}
	<div class="empty card">
		<p>No lists yet.</p>
		<p class="muted">
			A list is wines to find and taste: a critic’s top 100, every cuvée of a producer, the grands crus of Chablis. Each
			entry is a wine (that vintage), a cuvée (any vintage) or a producer (any of its wines), and ticks itself once you’ve
			tasted it.
		</p>
	</div>
{:else}
	<div class="grid" bind:clientWidth={gridWidth} style:--cols={cols}>
		{#each columns as col, i (i)}
		<div class="col">
		{#each col as l (l.id)}
			<a
				class="list card"
				href={links.list(l.id)}
				bind:offsetHeight={heights[l.id]}
				onpointerenter={(e) => e.pointerType === 'mouse' && (hovered = l)}
				onpointerleave={() => (hovered = null)}
			>
				<div class="head">
					<h2>{#if l.is_wishlist}<span class="star" aria-hidden="true">★</span> {/if}{l.name}</h2>
					{#if l.live}<span class="badge live" title="Live: {l.live}">Live</span>{/if}
					{#if milestone(l)}<span class="badge" class:done={l.tasted === l.entries}>{milestone(l)}</span>{/if}
				</div>
				{#if l.source}<div class="muted source">{l.source}</div>{/if}
				<ListDots dots={dotsOf(l)} />
				{#if find.trim() && !named(l)}<div class="hits muted">{hits(l)} {hits(l) === 1 ? 'entry matches' : 'entries match'}</div>{/if}
				{#if l.entries}
					<div class="progress">
						<span class="bar" aria-hidden="true"><span style:width="{pct(l)}%"></span></span>
						<span class="num"><b>{l.tasted}</b> of {l.entries} tasted</span>
						{#if l.owned}<span class="muted num">· {l.owned} in the cellar</span>{/if}
					</div>
				{:else}
					<div class="muted">No entries yet</div>
				{/if}
			</a>
		{/each}
		</div>
		{/each}
	</div>
	{#if !found.length}<p class="muted">No list, wine or note matches “{find.trim()}”.</p>{/if}
{/if}

<style>
	/* the head as a column: the title row, the find box, the orders (also over the map, app.css's map-full) */
	.lists-head {
		flex-direction: column;
		align-items: stretch;
		gap: 10px;
	}
	.title-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px;
	}
	.title-row h1 {
		margin: 0;
	}
	.stats {
		display: flex;
		flex-wrap: wrap;
		gap: 2px 14px;
		margin: 4px 0 0;
		font-size: 13px;
		color: var(--muted);
	}
	.stats b {
		color: var(--text);
		font-weight: 600;
	}
	.orders {
		display: flex;
		flex-wrap: wrap;
		gap: 6px 16px;
	}
	.find {
		width: 100%;
		box-sizing: border-box;
		padding: 6px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
		font: inherit;
		font-size: 13px;
		color: inherit;
	}
	.from {
		flex-basis: 100%;
		display: flex !important;
		flex-direction: row !important;
		align-items: center;
		gap: 6px;
		font-size: 13px;
	}
	.criteria-box {
		flex-basis: 100%;
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 12px;
		border: 1px solid var(--border);
		border-radius: 10px;
	}
	.kind {
		align-self: flex-start;
	}
	.seg {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.seg button {
		border: none;
		background: none;
		padding: 6px 12px;
		font: inherit;
		font-size: 13px;
		color: var(--muted);
		cursor: pointer;
	}
	.seg button.on {
		background: var(--accent);
		color: var(--on-accent);
	}
	.small {
		margin: 0;
		font-size: 12px;
	}
	.badge.live {
		background: none;
		border: 1px solid var(--accent);
		color: var(--accent);
	}
	.hits {
		font-size: 12px;
	}
	.order {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
	}
	.order select {
		padding: 3px 6px;
		font-size: 13px;
	}
	.new {
		display: flex;
		flex-wrap: wrap;
		gap: 10px 14px;
		align-items: flex-end;
		padding: 14px 16px;
		margin-bottom: 16px;
	}
	.new label {
		display: flex;
		flex-direction: column;
		gap: 4px;
		flex: 1 1 220px;
	}
	.label {
		font-size: 12px;
		color: var(--muted);
	}
	.error {
		width: 100%;
		margin: 0;
		color: var(--down);
		font-size: 13px;
	}
	.empty {
		padding: 20px;
	}
	.empty p {
		margin: 0 0 6px;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(var(--cols, 1), minmax(0, 1fr));
		gap: 14px;
		align-items: start;
	}
	.col {
		display: flex;
		flex-direction: column;
		gap: 14px;
		min-width: 0;
	}
	.list {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 16px 18px;
		color: var(--text);
		text-decoration: none;
	}
	.list:hover {
		border-color: var(--accent);
	}
	.head {
		display: flex;
		align-items: baseline;
		gap: 10px;
	}
	h2 {
		margin: 0;
		font-size: 17px;
	}
	.star {
		color: var(--accent);
		margin-right: 4px;
	}
	.source {
		margin-top: -6px;
		font-size: 13px;
	}
	.badge {
		margin-left: auto;
		flex: none;
		font-size: 11px;
		padding: 1px 8px;
		border-radius: 10px;
		background: var(--accent-soft);
		color: var(--accent);
		white-space: nowrap;
	}
	.badge.done {
		background: color-mix(in srgb, var(--up) 16%, transparent);
		color: var(--up);
		font-weight: 600;
	}
	.progress {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
	}
	.bar {
		flex: 0 0 90px;
		height: 6px;
		border-radius: 3px;
		background: var(--surface-2);
		overflow: hidden;
	}
	.bar span {
		display: block;
		height: 100%;
		background: var(--accent);
	}
</style>

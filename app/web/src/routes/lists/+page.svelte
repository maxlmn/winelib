<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import ListDots from '#lib/components/ListDots.svelte';
	import { createList, DOT_ORDERS, matches, sortDots, type DotOrder } from '#lib/api/lists.ts';
	import { links } from '#lib/links.ts';

	let { data } = $props();

	// The wishlist first, then the closest to done, the most tasted, by name
	const lists = $derived(
		[...data.lists].sort(
			(a, b) =>
				Number(b.is_wishlist) - Number(a.is_wishlist) ||
				(b.entries ? b.tasted / b.entries : 0) - (a.entries ? a.tasted / a.entries : 0) ||
				b.tasted - a.tasted ||
				a.name.localeCompare(b.name)
		)
	);
	// Every mosaic in one order: the lists' own, by note, tasted first... (remembered on this device)
	let order = $state<DotOrder>('list');
	onMount(() => {
		try {
			const saved = localStorage.getItem('winelib-dots-order');
			if (DOT_ORDERS.some(([k]) => k === saved)) order = saved as DotOrder;
		} catch {
			/* no storage: not remembered */
		}
	});
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
	const pct = (l: { tasted: number; entries: number }) => (l.entries ? Math.round((100 * l.tasted) / l.entries) : 0);
	const milestone = (l: { tasted: number; entries: number }) =>
		!l.entries ? '' : l.tasted === l.entries ? 'Complete' : l.tasted * 2 >= l.entries ? 'Past halfway' : l.tasted ? '' : 'Not started';

	let adding = $state(false);
	let name = $state('');
	let source = $state('');
	let error = $state('');
	async function create() {
		error = '';
		try {
			const { id } = await createList({ name, source: source || null, description: null, url: null });
			goto(links.list(id));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Couldn’t create it';
		}
	}
</script>

<svelte:head><title>Lists · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Lists</h1>
	{#if lists.length}
		<input class="find" type="search" bind:value={find} placeholder="Find a list, a wine, a note…" aria-label="Find in the lists" />
		<label class="order">
			<span class="muted">Sort the mosaics</span>
			<select value={order} onchange={(e) => setOrder(e.currentTarget.value as DotOrder)}>
				{#each DOT_ORDERS as [k, label] (k)}<option value={k}>{label}</option>{/each}
			</select>
		</label>
	{/if}
	<button class="btn primary" onclick={() => (adding = !adding)}>{adding ? 'Cancel' : '＋ New list'}</button>
</div>

{#if adding}
	<form class="new card" onsubmit={(e) => { e.preventDefault(); create(); }}>
		<label><span class="label">Name</span><input bind:value={name} required placeholder="Noble Rot’s wines of the decade" /></label>
		<label><span class="label">Made by</span><input bind:value={source} placeholder="Noble Rot, a critic, you…" /></label>
		<button class="btn primary" disabled={!name.trim()}>Create</button>
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
	<div class="grid">
		{#each found as l (l.id)}
			<a class="list card" href={links.list(l.id)}>
				<div class="head">
					<h2>{#if l.is_wishlist}<span class="star" aria-hidden="true">★</span> {/if}{l.name}</h2>
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
	{#if !found.length}<p class="muted">No list, wine or note matches “{find.trim()}”.</p>{/if}
{/if}

<style>
	.find {
		margin-left: auto;
		width: min(260px, 100%);
		padding: 6px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
		font: inherit;
		font-size: 13px;
		color: inherit;
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
		grid-template-columns: repeat(auto-fill, minmax(min(360px, 100%), 1fr));
		gap: 14px;
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

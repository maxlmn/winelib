<script lang="ts">
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import CriticPills from '#lib/components/CriticPills.svelte';
	import { addWish, editWish, priceWish, removeWish, toWishIn, type WishIn, type WishItem } from '#lib/api/wishlist.ts';
	import { symbol } from '#lib/format.ts';
	import { links } from '#lib/links.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { formatName } from '#lib/wineList.ts';

	let { data } = $props();

	let items = $state<WishItem[]>([]);
	$effect.pre(() => {
		items = data.items;
	});
	let only = $state<'all' | 'below' | 'owned'>('all');
	const below = $derived(items.filter((i) => i.below_target));
	const owned = $derived(items.filter((i) => i.owned));
	const shown = $derived(only === 'below' ? below : only === 'owned' ? owned : items);

	const price = (n: number, currency: string) => `${symbol(currency)}${Math.round(n).toLocaleString()}`;
	const when = (d: string | null) =>
		d ? new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '';
	const replace = (item: WishItem) => (items = items.map((i) => (i.id === item.id ? item : i)));
	const blankWish = (wine_id?: number): WishIn => ({
		wine_id, any_vintage: false, bottle_size: null, target_price: null, currency: null, note: null, url: null
	});

	// --- Adding: a wine found by search ---
	let q = $state('');
	let results = $state<{ id: number; title: string; sub: string; region?: string }[]>([]);
	let searchTimer: ReturnType<typeof setTimeout>;
	function search(text: string) {
		q = text;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(async () => {
			if (text.trim().length < 2) return (results = []);
			const r = await fetch(`/api/search?q=${encodeURIComponent(text)}&limit=8`).then((r) => r.json());
			results = r.results.filter((x: { kind: string }) => x.kind === 'wine');
		}, 150);
	}
	async function add(wineId: number) {
		const item = await addWish(blankWish(wineId));
		items = [item, ...items.filter((i) => i.id !== item.id)];
		q = '';
		results = [];
		only = 'all';
		edit(item);
	}

	// --- Editing one entry in place ---
	let editing = $state<number | null>(null);
	let draft = $state<WishIn>(blankWish());
	let error = $state('');
	function edit(item: WishItem) {
		editing = item.id;
		draft = toWishIn(item);
		error = '';
	}
	async function save(item: WishItem) {
		const target = draft.target_price as number | string | null;
		try {
			replace(await editWish(item.id, { ...draft, target_price: target === null || target === '' ? null : Number(target) }));
			editing = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Couldn’t save';
		}
	}
	async function remove(item: WishItem) {
		await removeWish(item.id);
		items = items.filter((i) => i.id !== item.id);
	}

	// --- Its market price now ---
	let pricing = $state<number | null>(null);
	let priceNote = $state<Record<number, string>>({});
	async function fetchPrice(item: WishItem) {
		pricing = item.id;
		try {
			const r = await priceWish(item.id);
			replace(r);
			const why = (r.log ?? []).filter((l) => /WARN|SKIP|ERROR/.test(l)).map((l) => l.replace(/^\s*\[\w+\]\s*/, '')).join(' ');
			priceNote[item.id] = r.market ? '' : why || 'No market price found';
		} catch (e) {
			priceNote[item.id] = e instanceof Error ? e.message : 'Couldn’t fetch it';
		} finally {
			pricing = null;
		}
	}
	const currencies = $derived([...new Set([appSettings.currency, ...data.options.currencies])]);
</script>

<svelte:head><title>Wishlist · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Wishlist</h1>
	{#if items.length}
		<div class="views" role="group" aria-label="Show">
			<button class:on={only === 'all'} onclick={() => (only = 'all')}>All <span class="num">{items.length}</span></button>
			<button class:on={only === 'below'} onclick={() => (only = 'below')} disabled={!below.length}>Below your price <span class="num">{below.length}</span></button>
			<button class:on={only === 'owned'} onclick={() => (only = 'owned')} disabled={!owned.length}>In your cellar <span class="num">{owned.length}</span></button>
		</div>
	{/if}
</div>

<div class="add card">
	<input type="search" placeholder="Add a wine: producer, cuvée, vintage…" value={q} oninput={(e) => search(e.currentTarget.value)} />
	{#if results.length}
		<ul class="results">
			{#each results as r (r.id)}
				<li>
					<button onclick={() => add(r.id)}>
						<span class="dot" style:background={regionColor(r.region)}></span>
						<span>{r.title}</span> <span class="muted">{r.sub}</span>
						{#if items.some((i) => i.wine_id === r.id)}<span class="muted already">on the list</span>{/if}
					</button>
				</li>
			{/each}
		</ul>
	{:else if q.trim().length >= 2}
		<p class="muted hint">No wine by that name. <a href={links.newWine()}>Add it as a new wine</a>, then ☆ Wishlist on its page.</p>
	{/if}
</div>

{#if !items.length}
	<div class="empty card">
		<p>Nothing on your wishlist yet.</p>
		<p class="muted">
			Search for a wine above, or use <b>☆ Wishlist</b> on any wine’s page. Give it the price you’d pay: with an LWIN,
			its market price comes with the cellar’s (Settings › Maintenance › Market prices), and the list says when it’s
			below yours.
		</p>
	</div>
{:else}
	<div class="list card">
		{#each shown as item (item.id)}
			<article class="item">
				<span class="end"><BottleEnd region={regionColor(item.region)} color={item.color} format={item.bottle_size} size={16} /></span>
				<div class="what">
					<div class="name">
						<a class="producer" href={links.producer(item.producer_id)}>{item.producer}</a>
						<a href={links.wine(item.wine_id)}>{item.cuvee} <span class="muted num">{item.any_vintage ? 'any vintage' : item.vintage}</span></a>
						{#if formatName(item.bottle_size)}<span class="format">{formatName(item.bottle_size)}</span>{/if}
						<CriticPills scores={item.scores} />
					</div>
					<div class="muted sub">{[item.appellation, regionLabel(item.region)].filter(Boolean).join(' · ')}</div>
					{#if item.note || item.url || item.owned}
						<div class="extra">
							{#if item.owned}<span class="owned">In your cellar: {item.owned}</span>{/if}
							{#if item.note}<span class="note">{item.note}</span>{/if}
							{#if item.url}<a href={item.url} target="_blank" rel="noopener noreferrer">Where to find it ↗</a>{/if}
						</div>
					{/if}
				</div>
				<div class="prices num">
					<div title={item.market ? `${item.market.source} · ${when(item.market.date)}` : ''}>
						<span class="label">Market</span>{item.market ? price(item.market.price, item.currency) : '–'}
					</div>
					<div><span class="label">Your price</span>{item.target_price ? price(item.target_price, item.currency) : '–'}</div>
					{#if item.below_target}<div class="badge">↓ Below your price</div>{/if}
					{#if priceNote[item.id]}<div class="muted why">{priceNote[item.id]}</div>{/if}
				</div>
				<div class="actions">
					<button class="link" onclick={() => (editing === item.id ? (editing = null) : edit(item))}>{editing === item.id ? 'Close' : 'Edit'}</button>
					{#if item.lwin}
						<button class="link" onclick={() => fetchPrice(item)} disabled={pricing === item.id}>{pricing === item.id ? 'Fetching…' : 'Market price'}</button>
					{/if}
					<button class="link" onclick={() => remove(item)} title="Take it off the wishlist">Remove</button>
				</div>
				{#if editing === item.id}
					<form class="edit" onsubmit={(e) => { e.preventDefault(); save(item); }}>
						<label><span class="label">Your price (a bottle)</span>
							<input type="number" min="0" step="any" bind:value={draft.target_price} placeholder="What you’d pay" /></label>
						<label><span class="label">Currency</span>
							<select bind:value={draft.currency}>
								{#each currencies as c (c)}<option value={c}>{c}</option>{/each}
							</select></label>
						<label><span class="label">Size</span>
							<select bind:value={draft.bottle_size}>
								{#each data.options.bottle_sizes as s (s)}<option value={s}>{s}</option>{/each}
							</select></label>
						<label class="check"><input type="checkbox" bind:checked={draft.any_vintage} /> Any vintage</label>
						<label class="wide"><span class="label">Note</span>
							<input bind:value={draft.note} placeholder="For a 2030 birthday, a friend’s tip…" /></label>
						<label class="wide"><span class="label">Where to find it</span>
							<input type="url" bind:value={draft.url} placeholder="https://…" /></label>
						<div class="wide buttons">
							{#if error}<span class="error">{error}</span>{/if}
							<button type="button" class="btn" onclick={() => (editing = null)}>Cancel</button>
							<button class="btn primary">Save</button>
						</div>
					</form>
				{/if}
			</article>
		{/each}
	</div>
	{#if !items.some((i) => i.lwin)}
		<p class="muted foot">Market prices need a wine’s LWIN (the wine form’s Suggest finds it).</p>
	{/if}
{/if}

<style>
	.views {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.views button {
		border: none;
		background: none;
		padding: 5px 10px;
		font-size: 12px;
		cursor: pointer;
		color: var(--muted);
	}
	.views button.on {
		background: var(--accent);
		color: #fff;
	}
	.views button:disabled {
		opacity: 0.45;
		cursor: default;
	}
	.add {
		padding: 12px;
		margin-bottom: 14px;
	}
	.add input {
		width: 100%;
		padding: 9px 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
		outline: none;
	}
	.add input:focus {
		border-color: var(--accent);
	}
	.results {
		list-style: none;
		margin: 6px 0 0;
		padding: 0;
	}
	.results button {
		display: flex;
		align-items: baseline;
		gap: 6px;
		width: 100%;
		text-align: left;
		border: none;
		background: none;
		padding: 7px 8px;
		border-radius: 6px;
		cursor: pointer;
		color: var(--text);
	}
	.results button:hover {
		background: var(--accent-soft);
	}
	.dot {
		flex: none;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		align-self: center;
	}
	.already {
		margin-left: auto;
		font-size: 12px;
	}
	.hint {
		margin: 8px 2px 0;
		font-size: 13px;
	}
	.empty {
		padding: 20px;
	}
	.empty p {
		margin: 0 0 6px;
	}
	.list {
		padding: 4px 0;
	}
	.item {
		display: grid;
		grid-template-columns: auto 1fr auto;
		grid-template-areas: 'end what prices' '. actions actions' 'edit edit edit';
		gap: 2px 12px;
		padding: 12px 16px;
	}
	.item + .item {
		border-top: 1px solid var(--border);
	}
	/* one width for every size (a magnum's end is larger): the names stay aligned */
	.end {
		grid-area: end;
		width: 24px;
		display: flex;
		justify-content: center;
		padding-top: 2px;
	}
	.what {
		grid-area: what;
		min-width: 0;
	}
	.name {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 8px;
	}
	.producer {
		font-weight: 600;
	}
	.format {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--muted);
	}
	.sub {
		font-size: 12px;
	}
	.extra {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 12px;
		margin-top: 4px;
		font-size: 13px;
	}
	.note {
		font-style: italic;
	}
	.owned {
		color: var(--up);
		font-weight: 600;
	}
	.prices {
		grid-area: prices;
		text-align: right;
		font-size: 14px;
		white-space: nowrap;
	}
	.label {
		font-size: 11px;
		color: var(--muted);
		margin-right: 6px;
	}
	.badge {
		display: inline-block;
		margin-top: 4px;
		padding: 1px 8px;
		border-radius: 10px;
		font-size: 12px;
		font-weight: 600;
		color: var(--up);
		background: color-mix(in srgb, var(--up) 14%, transparent);
	}
	.why {
		max-width: 240px;
		white-space: normal;
		font-size: 12px;
	}
	.actions {
		grid-area: actions;
		display: flex;
		gap: 14px;
		font-size: 12px;
	}
	button.link {
		border: none;
		background: none;
		padding: 0;
		color: var(--link);
		cursor: pointer;
		font: inherit;
	}
	button.link:disabled {
		color: var(--muted);
	}
	.edit {
		grid-area: edit;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(150px, 100%), 1fr));
		gap: 10px 12px;
		margin-top: 10px;
		padding: 12px;
		border-radius: 8px;
		background: var(--surface-2);
		align-items: end;
	}
	.edit label {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}
	.edit label.check {
		flex-direction: row;
		align-items: center;
		gap: 6px;
		padding-bottom: 7px;
	}
	.edit input:not([type='checkbox']),
	.edit select {
		padding: 6px 9px;
		border: 1px solid var(--border);
		border-radius: 7px;
		background: var(--surface);
	}
	.wide {
		grid-column: 1 / -1;
	}
	.buttons {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: 8px;
	}
	.error {
		color: var(--down);
		font-size: 12px;
		margin-right: auto;
	}
	.foot {
		font-size: 12px;
		margin-top: 10px;
	}
	@media (max-width: 760px) {
		.item {
			grid-template-columns: auto 1fr;
			grid-template-areas: 'end what' '. prices' '. actions' 'edit edit';
			padding: 12px;
		}
		.prices {
			text-align: left;
			display: flex;
			flex-wrap: wrap;
			gap: 2px 14px;
			margin-top: 4px;
		}
	}
</style>

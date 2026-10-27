<script lang="ts">
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import CriticPills from '#lib/components/CriticPills.svelte';
	import WinePicker from '#lib/components/forms/WinePicker.svelte';
	import { check, FormError, save as saveForm, toWineIn, wineErrors } from '#lib/api/forms.ts';
	import type { WineDraft, WineSummary } from '#lib/api/forms.ts';
	import { addWish, blankWish, editWish, priceWish, removeWish, toWishIn, type WishIn, type WishItem } from '#lib/api/wishlist.ts';
	import { symbol } from '#lib/format.ts';
	import { links } from '#lib/links.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { formatName } from '#lib/wineList.ts';

	let { data } = $props();

	let items = $state<WishItem[]>([]);
	$effect.pre(() => {
		items = data.items;
	});
	let only = $state<'all' | 'owned'>('all');
	const owned = $derived(items.filter((i) => i.owned));
	const shown = $derived(only === 'owned' ? owned : items);

	const price = (n: number, currency: string) => `${symbol(currency)}${Math.round(n).toLocaleString()}`;
	const when = (d: string | null) =>
		d ? new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '';
	const replace = (item: WishItem) => (items = items.map((i) => (i.id === item.id ? item : i)));

	// --- Adding: a wine picked, a new vintage of one, or a wine not in WineLib yet (created first) ---
	let wine = $state<WineSummary | null>(null);
	let draft = $state<WineDraft | null>(null);
	let addErrors = $state<Record<string, string>>({});
	let addError = $state('');
	let adding = $state(false);
	async function add() {
		addErrors = {};
		addError = '';
		adding = true;
		try {
			let wineId = wine?.id;
			if (!wineId && draft) {
				check(wineErrors(draft));
				wineId = (await saveForm('wines', null, toWineIn(draft))).id;
			}
			if (!wineId) return;
			const item = await addWish(blankWish(wineId));
			items = [item, ...items.filter((i) => i.id !== item.id)];
			wine = draft = null;
			only = 'all';
		} catch (e) {
			addError = e instanceof Error ? e.message : 'Couldn’t add it';
			if (e instanceof FormError) addErrors = e.fields;
		} finally {
			adding = false;
		}
	}

	// --- Editing one entry in place ---
	let editing = $state<number | null>(null);
	let change = $state<WishIn>(blankWish());
	let error = $state('');
	function edit(item: WishItem) {
		editing = item.id;
		change = toWishIn(item);
		error = '';
	}
	async function save(item: WishItem) {
		try {
			replace(await editWish(item.id, change));
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
</script>

<svelte:head><title>Wishlist · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Wishlist</h1>
	{#if items.length}
		<div class="views" role="group" aria-label="Show">
			<button class:on={only === 'all'} onclick={() => (only = 'all')}>All <span class="num">{items.length}</span></button>
			<button class:on={only === 'owned'} onclick={() => (only = 'owned')} disabled={!owned.length}>In your cellar <span class="num">{owned.length}</span></button>
		</div>
	{/if}
</div>

<div class="add card">
	<WinePicker bind:wine bind:draft options={data.options} prefix="wish" errors={addErrors} />
	{#if wine || draft}
		<div class="add-row">
			{#if addError}<span class="error">{addError}</span>{/if}
			<button class="btn primary" onclick={add} disabled={adding}>{draft ? 'Create the wine and add it' : 'Add to the wishlist'}</button>
		</div>
	{/if}
</div>

{#if !items.length}
	<div class="empty card">
		<p>Nothing on your wishlist yet.</p>
		<p class="muted">
			Find a wine above (or <b>＋ New wine…</b> when it isn’t in WineLib yet), or use <b>☆ Wishlist</b> on any wine’s
			page. With an LWIN, its market price comes with the cellar’s (Settings › Maintenance › Market prices).
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
					{#if item.market}
						<div><span class="label">Market</span>{price(item.market.price, item.currency)}</div>
						<div class="muted when">{item.market.source} · {when(item.market.date)}</div>
					{/if}
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
						<label><span class="label">Size</span>
							<select bind:value={change.bottle_size}>
								{#each data.options.bottle_sizes as s (s)}<option value={s}>{s}</option>{/each}
							</select></label>
						<label class="check"><input type="checkbox" bind:checked={change.any_vintage} /> Any vintage</label>
						<label class="wide"><span class="label">Note</span>
							<input bind:value={change.note} placeholder="For a 2030 birthday, a friend’s tip…" /></label>
						<label class="wide"><span class="label">Where to find it</span>
							<input type="url" bind:value={change.url} placeholder="https://…" /></label>
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
	.add-row {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: 10px;
		margin-top: 10px;
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
	.when {
		font-size: 11px;
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

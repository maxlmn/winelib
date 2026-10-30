<script lang="ts">
	import { appSettings, integrations } from '#lib/settings.svelte.ts';
	import { messageOf, request } from '#lib/api/http.ts';
	import { invalidateAll } from '$app/navigation';
	import ActionMenu from '#lib/components/ActionMenu.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import WineContent from '#lib/components/details/WineContent.svelte';
	import { fmtDate } from '#lib/components/details/wine.ts';
	import { links } from '#lib/links.ts';
	import Change from '#lib/components/Change.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import BottleShelf from '#lib/components/details/BottleShelf.svelte';
	import { formatName } from '#lib/wineList.ts';
	import { amount, pct, money, today } from '#lib/format.ts';
	import type { OutKind } from '#lib/api/details.ts';

	let { data } = $props();
	const b = $derived(data.bottle);
	const wine = $derived(data.detail);
	// The title in words: "1 bottle", "3 half bottles", "2 magnums", "4 50 cl bottles"; "2 bottles, finished" once none are left
	const what = $derived.by(() => {
		const name = formatName(b.bottle_size).toLowerCase();
		const noun = !name ? 'bottle' : name.endsWith(' cl') ? `${name} bottle` : name;
		const n = b.qty || gone || 1; // finished: how many there were
		return `${n} ${noun}${n === 1 ? '' : 's'}${b.qty ? '' : ', finished'}`;
	});

	const purchase = $derived(
		b.price ? `${amount(b.price, b.currency)}${b.currency !== appSettings.currency && b.price_base ? ` · ${money(b.price_base)}` : ''}` : 'N/A'
	);

	// The market price sources set up (Settings › Integrations), named on the button while it asks
	const priceSources = $derived(integrations.list.filter((i) => i.configured && ['bordeaux_index', 'winelabs'].includes(i.id)).map((i) => i.name).join(' / '));
	// Market price by the wine's LWIN: Bordeaux Index when your BI portfolio holds it, else WineLabs.ai (see app/api/tasks/update_market_prices.py).
	// Asked for this bottle and every other one of the wine in the cellar, shown for a look, saved on Save.
	type Proposal = {
		bottle_id: number;
		this: boolean;
		location: string | null;
		bottle_size: string | null;
		qty: number;
		currency: string | null;
		old: number | null;
		old_date: string | null;
		old_source: string | null;
		new: number | null;
		source: string | null;
	};
	let fetching = $state(false);
	let saving = $state(false);
	let priceMessage = $state('');
	let proposals = $state<Proposal[] | null>(null);
	const toSave = $derived((proposals ?? []).filter((p) => p.new !== null));
	const change = (p: Proposal) => (p.old && p.new !== null ? pct(p.old, p.new) : null);

	async function fetchPrice() {
		fetching = true;
		priceMessage = '';
		proposals = null;
		try {
			const body = await request<{ message?: string; found?: boolean; prices: Proposal[] }>(`/api/bottles/${b.id}/market-price`, { method: 'POST' });
			if (body.message) priceMessage = body.message;
			if (body.found) proposals = body.prices;
		} catch (e) {
			priceMessage = messageOf(e);
		} finally {
			fetching = false;
		}
	}

	// Bottles that left other than by being drunk: gifted, sold, broken...; taken off the count, put back if undone
	const KINDS: { id: OutKind; label: string; past: string; note: string }[] = [
		{ id: 'gifted', label: 'Gifted', past: 'Gifted', note: 'To whom?' },
		{ id: 'sold', label: 'Sold', past: 'Sold', note: 'To whom, where?' },
		{ id: 'broken', label: 'Broken', past: 'Broken', note: 'What happened?' },
		{ id: 'other', label: 'Other', past: 'Gone', note: 'What happened to it?' }
	];
	const kindOf = (id: OutKind) => KINDS.find((k) => k.id === id) ?? KINDS[3];
	let out = $state<{ kind: OutKind; qty: number; date: string; note: string; price: number | null } | null>(null);
	let outError = $state('');
	function startOut() {
		outError = '';
		out = { kind: 'gifted', qty: 1, date: today(), note: '', price: null };
	}
	async function saveOut() {
		if (!out) return;
		outError = '';
		try {
			await request(`/api/bottles/${b.id}/out`, { method: 'POST', body: { ...out, price: out.kind === 'sold' ? out.price : null } });
			out = null;
			await invalidateAll();
		} catch (e) {
			outError = messageOf(e);
		}
	}
	async function undoOut(id: number) {
		outError = '';
		try {
			await request(`/api/bottles/${b.id}/out/${id}`, { method: 'DELETE' });
			await invalidateAll();
		} catch (e) {
			outError = messageOf(e);
		}
	}
	// The bottles' story, newest first: drunk (its tastings) and the rest
	const story = $derived(
		[
			...b.drunk.map((t) => ({ key: `t${t.id}`, date: t.date, tasting: t, event: null })),
			...b.events.map((e) => ({ key: `e${e.id}`, date: e.date, tasting: null, event: e }))
		].sort((x, y) => (y.date ?? '').localeCompare(x.date ?? ''))
	);
	const gone = $derived(b.drunk.length + b.events.reduce((n, e) => n + e.qty, 0));

	async function savePrices() {
		saving = true;
		try {
			const prices = toSave.map((p) => ({ bottle_id: p.bottle_id, price: p.new, source: p.source }));
			await request(`/api/bottles/${b.id}/market-price/save`, { method: 'POST', body: { prices } });
			proposals = null;
			priceMessage = '';
			await invalidateAll();
		} catch (e) {
			priceMessage = messageOf(e);
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head><title>Bottle · {wine.producer.name} {wine.cuvee} {wine.vintage} · WineLib</title></svelte:head>

<section class="card bottle">
	<div class="top">
		<div>
			<div class="kind">Bottle</div>
			<div class="title-row">
			<h2>{what}</h2>
			<!-- one bottle end per bottle, beside the title: those in the cellar, then those gone (drunk, gifted...) faded -->
			{#if b.qty || gone}
				<div class="ends" aria-label="{b.qty} in the cellar{gone ? `, ${gone} gone` : ''}">
					{#each { length: b.qty } as _, i (i)}<BottleEnd region={wine.region_color} color={wine.color} format={b.bottle_size} size={16} title="In the cellar" />{/each}
					{#each { length: gone } as _, i (`g${i}`)}<span class="gone"><BottleEnd region={wine.region_color} color={wine.color} format={b.bottle_size} size={16} title="Gone" /></span>{/each}
				</div>
			{/if}
			</div>
			{#if b.location && b.location !== 'Consumed'}<!-- Consumed: a bottle recorded only for a tasting, no place -->
				<a class="where muted" href={links.cellar({ loc: b.location, view: 'shelves' })}>
					{b.qty ? 'In' : 'Was in'} <b>{b.location}</b>{b.location_group !== b.location ? ` · ${b.location_group}` : ''} · see on the shelf map →
				</a>
			{/if}
			{#if b.shelf && b.qty && b.shelf.bins.length > 1}<BottleShelf shelf={b.shelf} />{/if}<!-- a place on its own (Away): no shelf to show -->
		</div>
		<!-- as on the wine page: the one to hand (Drink, while there's one left), the rest in the ⋯ menu -->
		<div class="page-actions">
			<ActionMenu>
				{#if b.qty}<button class="menu-item" role="menuitem" onclick={startOut} disabled={!!out}><Icon name="bottle" size={15} />Take some out (gifted, sold…)</button>{/if}
				<a class="menu-item" role="menuitem" href={links.editBottle(b.id)}><Icon name="edit" size={15} />Edit bottle</a>
			</ActionMenu>
			{#if b.qty}<a class="btn icon primary" href={links.newTasting({ bottle_id: b.id })} title="Drink it: a tasting" aria-label="Drink it"><Icon name="glass" size={15} /></a>{/if}
		</div>
	</div>
	{#if out}
		<form class="out" onsubmit={(e) => { e.preventDefault(); saveOut(); }}>
			<div class="seg" role="group" aria-label="What happened">
				{#each KINDS as k (k.id)}
					<button type="button" class:on={out.kind === k.id} onclick={() => out && (out.kind = k.id)}>{k.label}</button>
				{/each}
			</div>
			<div class="fields">
				{#if b.qty > 1}
					<label><span class="label">How many</span><input type="number" min="1" max={b.qty} bind:value={out.qty} /></label>
				{/if}
				<label><span class="label">When</span><input type="date" bind:value={out.date} /></label>
				{#if out.kind === 'sold'}
					<label><span class="label">For, a bottle ({b.currency ?? appSettings.currency})</span><input type="number" min="0" step="any" bind:value={out.price} placeholder="Optional" /></label>
				{/if}
				<label class="note"><span class="label">Note</span><input bind:value={out.note} placeholder={kindOf(out.kind).note} /></label>
			</div>
			<div class="buttons">
				<button class="btn primary">Take {out.qty > 1 ? `${out.qty} bottles` : 'it'} out</button>
				<button type="button" class="btn" onclick={() => (out = null)}>Cancel</button>
				{#if outError}<span class="msg">{outError}</span>{/if}
			</div>
		</form>
	{:else if outError}
		<p class="msg" role="alert">{outError}</p><!-- an undo that failed -->
	{/if}
	<div class="grid">
		<div class="price">
			<div class="label">Purchase</div>
			<div class="value num">{purchase}</div>
			<!-- when, from whom, through whom: small, under the price -->
			{#if b.purchase_date || b.vendor || b.provenance}
				<div class="sub muted">{[b.purchase_date && fmtDate(b.purchase_date), b.vendor, b.provenance && b.provenance !== b.vendor ? b.provenance : null].filter(Boolean).join(' · ')}</div>
			{/if}
		</div>
		<div class="price">
			<div class="label">Market{b.last_price && b.last_price_source ? ` · ${b.last_price_source}` : ''}</div>
			{#if b.last_price}
				<div class="value num">
					{amount(b.last_price, b.currency)}
					{#if b.change_pct !== null}
						<span class="change"><Change value={b.change_pct} /></span>
					{/if}
				</div>
				{#if b.last_price_date}<div class="sub muted">as of {fmtDate(b.last_price_date)}</div>{/if}
			{:else}
				<div class="value num muted">–</div>
			{/if}
			{#if wine.lwin && priceSources}
				<button class="link fetch" disabled={fetching || saving} onclick={fetchPrice}>
					{fetching ? `Asking ${priceSources}…` : b.last_price ? 'Refresh market price' : 'Fetch market price'}
				</button>
			{:else if !wine.lwin && priceSources}
				<div class="sub muted">No LWIN on this wine: <a href={links.editWine(wine.id)}>add one</a> to fetch a market price</div>
			{/if}
			{#if priceMessage}<div class="sub msg">{priceMessage}</div>{/if}
		</div>
		{#if proposals}
			<div class="proposal">
				<div class="label">New market prices · check before saving</div>
				<div class="table-wrap">
					<table>
						<thead>
							<tr><th>Bottle</th><th class="r">Now</th><th class="r">New</th><th class="r">Change</th><th>Source</th></tr>
						</thead>
						<tbody>
							{#each proposals as p (p.bottle_id)}
								<tr class:this={p.this}>
									<td>
										{#if p.this}<b>This bottle</b>{:else}<a href={links.bottle(p.bottle_id)}>{p.qty}× {p.bottle_size ?? '75cl'} @ {p.location ?? '?'}</a>{/if}
										{#if p.this}<span class="muted"> · {p.qty}× {p.bottle_size ?? '75cl'}</span>{/if}
									</td>
									<td class="r num">
										{p.old ? amount(p.old, p.currency) : '–'}
										{#if p.old_date}<div class="muted small">{fmtDate(p.old_date)}{p.old_source ? ` · ${p.old_source}` : ''}</div>{/if}
									</td>
									<td class="r num">{amount(p.new, p.currency)}</td>
									<td class="r num">
										<Change value={change(p)} />
									</td>
									<td class="muted">{p.source ?? 'not found: kept'}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
				<div class="buttons">
					<button class="btn primary" disabled={saving || !toSave.length} onclick={savePrices}>
						{saving ? 'Saving…' : `Save ${toSave.length} price${toSave.length === 1 ? '' : 's'}`}
					</button>
					<button class="btn" disabled={saving} onclick={() => (proposals = null)}>Cancel</button>
				</div>
			</div>
		{/if}
	</div>
	{#if story.length}
		<div class="story">
			<div class="label">What happened to {gone > 1 ? 'them' : 'it'}</div>
			<ul>
				{#each story as s (s.key)}
					<li>
						<span class="when num">{s.date ? fmtDate(s.date) : 'Undated'}</span>
						{#if s.tasting}
							<span class="what drunk">Drunk</span>
							<a href={links.tasting(s.tasting.id)}>{s.tasting.place ?? 'the tasting'}</a>
						{:else if s.event}
							<span class="what {s.event.kind}">{kindOf(s.event.kind).past}{s.event.qty > 1 ? ` ×${s.event.qty}` : ''}</span>
							{#if s.event.note}<span>{s.event.note}</span>{/if}
							{#if s.event.price}<span class="muted num">{amount(s.event.price, s.event.currency)}</span>{/if}
							<button class="undo" onclick={() => s.event && undoOut(s.event.id)} title="Put {s.event.qty > 1 ? 'them' : 'it'} back in the cellar">Undo</button>
						{/if}
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</section>

{#key wine.id}
	<WineContent {wine} regionColors={data.regionColors} />
{/key}

<style>
	.title-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 12px;
		margin-bottom: 4px;
	}
	.title-row h2 {
		margin: 0;
	}
	.ends {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.ends .gone {
		display: inline-flex;
		opacity: 0.3;
	}
	.bottle {
		padding: 16px 20px;
		margin-bottom: 14px;
	}
	/* the buttons at the top right (the title wraps in its column) */
	.top {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
	}
	.top > div:first-child {
		flex: 1;
		min-width: 0;
	}
	.kind,
	.label {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--muted);
	}
	h2 {
		margin: 2px 0;
		font-size: 20px;
	}
	.where {
		font-size: 12px;
	}
	.where:hover {
		color: var(--accent);
	}

	.out {
		margin-top: 14px;
		padding: 12px 14px;
		border: 1px solid var(--border);
		border-radius: 10px;
		background: var(--surface-2);
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.seg {
		display: inline-flex;
		align-self: flex-start;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.seg button {
		border: none;
		background: var(--surface);
		padding: 6px 12px;
		font: inherit;
		font-size: 13px;
		color: var(--muted);
		cursor: pointer;
	}
	.seg button.on {
		background: var(--accent);
		color: #fff;
	}
	.fields {
		display: flex;
		flex-wrap: wrap;
		gap: 10px 14px;
	}
	.fields label {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.fields .note {
		flex: 1 1 220px;
	}
	.fields input {
		padding: 6px 9px;
		border: 1px solid var(--border);
		border-radius: 7px;
		background: var(--surface);
		font: inherit;
		font-size: 13px;
		color: inherit;
	}
	.fields input[type="number"] {
		width: 110px;
	}
	.out .buttons {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.story {
		margin-top: 16px;
		padding-top: 12px;
		border-top: 1px solid var(--border);
	}
	.story ul {
		list-style: none;
		margin: 6px 0 0;
		padding: 0;
		font-size: 13px;
	}
	.story li {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 10px;
		padding: 4px 0;
	}
	.story .when {
		width: 96px;
		color: var(--muted);
	}
	.what {
		font-weight: 600;
	}
	.what.drunk {
		color: var(--up, #2e7d57);
	}
	.what.broken {
		color: var(--down);
	}
	.undo {
		margin-left: auto;
		border: none;
		background: none;
		padding: 0;
		font-size: 12px;
		color: var(--muted);
		cursor: pointer;
	}
	.undo:hover {
		color: var(--accent);
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
		gap: 16px 24px;
		margin-top: 14px;
		align-items: start;
	}
	.value {
		font-size: 17px;
		font-weight: 600;
	}
	.change {
		font-size: 13px;
		margin-left: 6px;
	}
	.sub {
		font-size: 12px;
	}
	.fetch {
		margin-top: 4px;
		padding: 0;
		border: none;
		background: none;
		color: var(--accent);
		font-size: 12px;
		cursor: pointer;
	}
	.fetch:disabled {
		color: var(--muted);
		cursor: default;
	}
	.msg {
		color: #c0392b;
	}
	.proposal {
		grid-column: 1 / -1;
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 12px;
	}
	.table-wrap {
		overflow-x: auto;
		margin: 8px 0 12px;
	}
	.proposal table {
		width: 100%;
		border-collapse: collapse;
		font-size: 13px;
	}
	.proposal th {
		text-align: left;
		font-weight: 500;
		font-size: 12px;
		color: var(--muted);
		padding: 4px 8px;
		border-bottom: 1px solid var(--border);
	}
	.proposal td {
		padding: 6px 8px;
		border-bottom: 1px solid var(--border);
		vertical-align: top;
		white-space: nowrap;
	}
	.proposal .r {
		text-align: right;
	}
	.proposal .small {
		font-size: 11px;
	}
	.proposal tr.this td {
		background: var(--surface-2);
	}
	.buttons {
		display: flex;
		gap: 8px;
	}
</style>

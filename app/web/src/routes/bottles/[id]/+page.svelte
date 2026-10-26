<script lang="ts">
	import { appSettings, integrations } from '#lib/settings.svelte.ts';
	import { invalidateAll } from '$app/navigation';
	import Facts from '#lib/components/details/Facts.svelte';
	import WineContent from '#lib/components/details/WineContent.svelte';
	import { fmtDate } from '#lib/components/details/wine.ts';
	import { links } from '#lib/links.ts';
	import Change from '#lib/components/Change.svelte';
	import { amount, pct, money } from '#lib/format.ts';

	let { data } = $props();
	const b = $derived(data.bottle);
	const wine = $derived(data.detail);

	const purchase = $derived(
		b.price ? `${amount(b.price, b.currency)}${b.currency !== appSettings.currency && b.price_base ? ` · ${money(b.price_base)}` : ''}` : 'N/A'
	);

	// The market price sources set up (Settings › Integrations), named on the button while it asks
	const priceSources = $derived(integrations.list.filter((i) => i.configured && ['bordeaux_index', 'winelabs'].includes(i.id)).map((i) => i.name).join(' / '));
	// Market price by the wine's LWIN: Bordeaux Index when your BI portfolio holds it, else WineLabs.ai (see winelib_utils/update_market_prices.py).
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
			const res = await fetch(`/api/bottles/${b.id}/market-price`, { method: 'POST' });
			const body = await res.json().catch(() => ({}));
			if (!res.ok) priceMessage = body.detail ?? `Error ${res.status}`;
			else {
				if (body.message) priceMessage = body.message;
				if (body.found) proposals = body.prices;
			}
		} catch {
			priceMessage = 'The app couldn’t be reached';
		} finally {
			fetching = false;
		}
	}

	async function savePrices() {
		saving = true;
		try {
			const prices = toSave.map((p) => ({ bottle_id: p.bottle_id, price: p.new, source: p.source }));
			const res = await fetch(`/api/bottles/${b.id}/market-price/save`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ prices })
			});
			if (!res.ok) priceMessage = `Error ${res.status}`;
			else {
				proposals = null;
				priceMessage = '';
				await invalidateAll();
			}
		} catch {
			priceMessage = 'The app couldn’t be reached';
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head><title>Bottle · {wine.producer.name} {wine.cuvee} {wine.vintage} · WineLib</title></svelte:head>

<section class="card bottle">
	<div class="top">
		<div>
			<div class="kind">Bottle{b.qty ? '' : ' · finished'}</div>
			<h2 class="num">{b.qty}× {b.bottle_size ?? '75cl'} <span class="muted">@</span> {b.location ?? 'Unknown'}</h2>
			<a class="where muted" href={links.cellar({ loc: b.location, view: 'shelves' })}>{b.location_group} · see on the shelf map →</a>
		</div>
		<div class="actions">
			<a class="btn" href={links.editBottle(b.id)}>Edit bottle</a>
			<a class="btn primary" href={links.newTasting({ bottle_id: b.id })}>Drink</a>
		</div>
	</div>
	<div class="grid">
		<div class="price">
			<div class="label">Purchase</div>
			<div class="value num">{purchase}</div>
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
		<Facts
			items={[
				{ label: 'Purchase date', value: b.purchase_date && fmtDate(b.purchase_date) },
				{ label: 'Vendor', value: b.vendor },
				{ label: 'Provenance', value: b.provenance }
			]}
		/>
	</div>
</section>

{#key wine.id}
	<WineContent {wine} regionColors={data.regionColors} />
{/key}

<style>
	.bottle {
		padding: 16px 20px;
		margin-bottom: 14px;
	}
	.top {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		flex-wrap: wrap;
		gap: 12px;
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
	.actions {
		display: flex;
		gap: 8px;
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

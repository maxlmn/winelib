<script lang="ts">
	import Change from '#lib/components/Change.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { amount, gbp, pct } from '#lib/format.ts';
	import { links } from '#lib/links.ts';

	/** Your Bordeaux Index portfolio (GET /api/bordeaux-index), per bottle in GBP, next to the app's own bottles. */
	type AppSide = {
		bottles: number; locations: string[]; value: number; bottle_ids: number[];
		/** the (first) matched wine's region and color: its bottle end */
		region: string | null; color: string | null;
		/** "lwin", or "name" when the app's LWIN differs from BI's: `fix` lists those wines and their LWIN;
		 * "assortment": a mixed case, the app's bottles of each of its wines in `parts` */
		match: 'lwin' | 'name' | 'assortment' | null; fix: [number, string][];
		parts?: { name: string; expected: number; held: number }[];
	};
	type Line = {
		ref: string; name: string; producer: string | null; vintage: string; pack: number; size: string; cases: number;
		bottles: number; location: string | null; duty: string | null; url: string | null; lwin: string | null;
		cost: number | null; bid: number | null; offer: number | null; last: number | null; last_date: string | null;
		value: number | null; app: AppSide;
		/** What the value is from: the last trade, else the best bid, else (neither) the cost */
		basis: 'last' | 'bid' | 'cost' | null;
	};
	type Totals = {
		bottles: number; cost: number; bid: number; last: number; value: number; value_matched: number; app_value: number; app_bottles: number;
		unmatched: number; app_only: number; by_name: number;
	};
	type AppOnly = { bottle_id: number; producer: string; cuvee: string; vintage: string; format: string | null; region: string | null; color: string | null; qty: number; location: string; lwin: string | null; value: number };
	type Reply = {
		available: boolean; error: string | null; fetched?: number; location?: string; lines: Line[]; totals: Totals | null;
		app_only?: AppOnly[];
	};

	let reply = $state<Reply | null>(null);
	let loading = $state(false);

	async function load(refresh = false) {
		loading = true;
		try {
			reply = await fetch(`/api/bordeaux-index${refresh ? '?refresh=true' : ''}`).then((r) => r.json());
		} catch {
			reply = { available: true, error: 'The app couldn’t be reached', lines: [], totals: null };
		} finally {
			loading = false;
		}
	}
	$effect(() => {
		load();
	});

	// A name match: give the app's wine BI's LWIN, so it matches (and is priced from BI) by LWIN from now on
	let fixing = $state<number | null>(null);
	async function useBiLwin(wineId: number, lwin: string) {
		fixing = wineId;
		try {
			const res = await fetch('/api/bordeaux-index/use-lwin', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ wine_id: wineId, lwin })
			});
			if (!res.ok) throw new Error(`Error ${res.status}`);
			await load();
		} catch (e) {
			alert(`Couldn’t update the LWIN: ${e instanceof Error ? e.message : e}`);
		} finally {
			fixing = null;
		}
	}

	// % change of BI's value per bottle against what you paid (BI's cost) and against the app's market value per bottle
	const vsCost = (l: Line) => (l.value != null && l.cost && l.bottles ? pct(l.cost, l.value / l.bottles) : null);
	const vsApp = (l: Line) =>
		l.value != null && l.bottles && l.app.bottles && l.app.value ? pct(l.app.value / l.app.bottles, l.value / l.bottles) : null;

	// BI values as the app's market prices: a preview first, saved on Save
	type Change = { bottle_id: number; wine: string; region: string | null; color: string | null; format: string | null; qty: number; currency: string; old: number | null; new: number; assortment: boolean };
	let changes = $state<Change[] | null>(null);
	let missingRates = $state<string[]>([]);
	let applying = $state(false);
	async function applyValues(commit: boolean) {
		applying = true;
		try {
			const res = await fetch('/api/bordeaux-index/apply-values', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ commit })
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(body.detail ?? `Error ${res.status}`);
			missingRates = body.missing_rates ?? [];
			changes = commit ? null : body.changes;
			if (commit) await load();
		} catch (e) {
			alert(`Couldn’t use BI's values: ${e instanceof Error ? e.message : e}`);
		} finally {
			applying = false;
		}
	}

	// Sortable wines table: click a header, again to reverse
	type Col = { key: string; label: string; num: boolean; get: (l: Line) => string | number | null };
	const COLS: Col[] = [
		{ key: 'wine', label: 'Wine', num: false, get: (l) => `${l.name} ${l.vintage}` },
		{ key: 'bottles', label: 'Btl', num: true, get: (l) => l.bottles },
		{ key: 'cost', label: 'Cost', num: true, get: (l) => l.cost },
		{ key: 'bid', label: 'Bid', num: true, get: (l) => l.bid },
		{ key: 'offer', label: 'Offer', num: true, get: (l) => l.offer },
		{ key: 'last', label: 'Last trade', num: true, get: (l) => l.last },
		{ key: 'value', label: 'BI value', num: true, get: (l) => l.value },
		{ key: 'vs_cost', label: 'vs cost', num: true, get: vsCost },
		{ key: 'app', label: 'In the app', num: false, get: (l) => l.app.bottles },
		{ key: 'app_value', label: 'App value', num: true, get: (l) => (l.app.bottles ? l.app.value : null) },
		{ key: 'vs_app', label: 'vs app', num: true, get: vsApp }
	];
	let sortKey = $state('value');
	let sortDesc = $state(true);
	function sortBy(key: string) {
		if (sortKey === key) sortDesc = !sortDesc;
		else {
			sortKey = key;
			sortDesc = key !== 'wine';
		}
	}
	const sorted = $derived.by(() => {
		const get = COLS.find((c) => c.key === sortKey)!.get;
		const dir = sortDesc ? -1 : 1;
		// empty cells last, whichever the direction
		return [...(reply?.lines ?? [])].sort((a, b) => {
			const x = get(a), y = get(b);
			if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1;
			return (typeof x === 'string' ? x.localeCompare(String(y)) : x - (y as number)) * dir;
		});
	});

	const WHERE: Record<string, string> = { BIRESERVES: 'BI Reserves', UKWAREHOUSE: 'UK warehouse', EUWAREHOUSE: 'EU warehouse', OTHER: 'Other' };
</script>

<div class="bi">
	<div class="bar">
		<p class="muted small">
			Bordeaux Index LiveTrade, per bottle in GBP. BI value: the last trade, else the best bid, else the cost. Reconciled with the app's
			bottles held at {reply?.location || 'your BI location'} (Settings › Bordeaux Index): same LWIN, vintage and size, at their
			market price. vs cost / vs app: BI's value per bottle against BI's cost and against the app's market price.
		</p>
		<div class="bar-buttons">
			{#if reply?.lines.length && !reply.error}
				<button class="btn" disabled={applying || loading} onclick={() => applyValues(false)} title="BI's last trade per bottle as the app's market price, for every line found in the app that has traded">
					{applying && !changes ? 'Checking…' : 'Use BI last trades as market prices'}
				</button>
			{/if}
			<button class="btn" disabled={loading} onclick={() => load(true)}>{loading ? 'Loading…' : 'Refresh'}</button>
		</div>
	</div>

	{#if changes}
		<div class="apply card">
			<div class="label">Market prices from BI's last trades · check before saving</div>
			{#if missingRates.length}<p class="error small">No exchange rate for {missingRates.join(', ')}: those bottles are left out (Settings).</p>{/if}
			{#if changes.length}
				<div class="table-wrap">
					<table>
						<thead><tr><th>Wine</th><th class="num">Btl</th><th class="num">Now</th><th class="num">New</th><th class="num">Change</th><th></th></tr></thead>
						<tbody>
							{#each changes as c (c.bottle_id)}
								<tr>
									<td><span class="end"><BottleEnd region={regionColor(c.region)} color={c.color} format={c.format} size={11} title="{regionLabel(c.region)} · {c.color ?? ''}" /></span><a href={links.bottle(c.bottle_id)}>{c.wine}</a></td>
									<td class="num">{c.qty}</td>
									<td class="num">{amount(c.old, c.currency)}</td>
									<td class="num">{amount(c.new, c.currency)}</td>
									<td class="num"><Change value={c.old ? pct(c.old, c.new) : null} /></td>
									<td class="muted small">
										{c.assortment ? 'mixed case average' : ''}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="muted">No BI line with a last trade is matched to a bottle in the app.</p>
			{/if}
			<div class="apply-buttons">
				<button class="btn primary" disabled={applying || !changes.length} onclick={() => applyValues(true)}>
					{applying ? 'Saving…' : `Save ${changes.length} price${changes.length === 1 ? '' : 's'}`}
				</button>
				<button class="btn" disabled={applying} onclick={() => (changes = null)}>Cancel</button>
			</div>
		</div>
	{/if}

	{#if !reply}
		<p class="muted">Loading your Bordeaux Index portfolio…</p>
	{:else if reply.error}
		<p class="error">{reply.error}</p>
	{:else if !reply.lines.length}
		<p class="muted">Your Bordeaux Index portfolio is empty.</p>
	{:else if reply.totals}
		{@const t = reply.totals}
		<div class="kpis">
			<div class="kpi"><div class="label">Bottles at BI</div><div class="value num">{t.bottles}</div></div>
			<div class="kpi"><div class="label">BI cost</div><div class="value num">{gbp(t.cost)}</div></div>
			<div class="kpi">
				<div class="label">BI value</div><div class="value num">{gbp(t.value)}</div>
				<div class="sub num">
					<Change value={pct(t.cost, t.value)} digits={1} /> <span class="muted">vs cost</span>
					{#if t.app_value}
						· <Change value={pct(t.app_value, t.value_matched)} digits={1} />
						<span class="muted" title="BI's value of the lines found in the app, against their app value">vs app</span>
					{/if}
				</div>
			</div>
			<div class="kpi">
				<div class="label">App value at {reply.location || 'your BI location'}</div><div class="value num">{gbp(t.app_value)}</div>
				<div class="sub muted">
					{t.app_bottles} btl in the app{t.unmatched ? ` · ${t.unmatched} BI lines not found` : ''}{t.app_only ? ` · ${t.app_only} btl not at BI` : ''}{t.by_name ? ` · ${t.by_name} matched by name` : ''}
				</div>
			</div>
		</div>

		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						{#each COLS as c (c.key)}
							<th class:num={c.num} aria-sort={sortKey === c.key ? (sortDesc ? 'descending' : 'ascending') : 'none'}>
								<button class="sort" class:on={sortKey === c.key} onclick={() => sortBy(c.key)}>
									{c.label}{sortKey === c.key ? (sortDesc ? ' ▼' : ' ▲') : ''}
								</button>
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each sorted as l (l.ref)}
						<tr>
							<td>
								{#if l.app.region}<span class="end"><BottleEnd region={regionColor(l.app.region)} color={l.app.color} format={l.size} size={11} title="{regionLabel(l.app.region)} · {l.app.color ?? ''}" /></span>{/if}
								{#if l.url}<a href={l.url} target="_blank" rel="noreferrer">{l.name}</a>{:else}{l.name}{/if}
								<span class="muted num">{l.vintage}</span>
								<div class="muted small">
									{l.cases} × {l.pack}×{l.size}{l.duty ? ` · ${l.duty}` : ''}{l.location ? ` · ${WHERE[l.location] ?? l.location}` : ''}
								</div>
							</td>
							<td class="num">{l.bottles}</td>
							<td class="num">{gbp(l.cost)}</td>
							<td class="num">{gbp(l.bid)}</td>
							<td class="num">{gbp(l.offer)}</td>
							<td class="num" title={l.last_date ?? ''}>{gbp(l.last)}</td>
							<td class="num">
								<b>{gbp(l.value)}</b>
								{#if l.basis === 'bid' || l.basis === 'cost'}<div class="muted small">at {l.basis === 'bid' ? 'best bid' : 'cost'}</div>{/if}
							</td>
							<td class="num"><Change value={vsCost(l)} /></td>
							<td class="small">
								{#if l.app.bottles}
									<a href={links.bottle(l.app.bottle_ids[0])}>{l.app.bottles} btl</a>
									<span class="muted">{l.app.locations.join(', ')}</span>
									{#if l.app.bottles !== l.bottles}<span class="warn" title="Not the same count as at BI">≠</span>{/if}
									{#if l.app.match === 'assortment' && l.app.parts}
										<div class="by-name">
											Mixed case: {l.app.parts.map((p) => `${p.held}/${p.expected} ${p.name}`).join(', ')}
										</div>
									{/if}
									{#if l.app.match === 'name'}
										<div class="by-name">
											Matched by name: the app's LWIN {l.app.fix.map(([, lw]) => lw || 'none').join(', ')} isn't BI's {l.lwin}
											{#each l.app.fix as [wineId] (wineId)}
												{#if l.lwin}
													<button class="link" disabled={fixing === wineId} onclick={() => useBiLwin(wineId, l.lwin!)}>
														{fixing === wineId ? 'Saving…' : 'Use BI’s LWIN'}
													</button>
												{/if}
											{/each}
										</div>
									{/if}
								{:else}<span class="warn">not found</span>{/if}
							</td>
							<td class="num">{l.app.bottles ? gbp(l.app.value) : ''}</td>
							<td class="num"><Change value={vsApp(l)} /></td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		{#if reply.app_only?.length}
			<h3>At {reply.location || 'your BI location'} in the app, not in the BI portfolio</h3>
			<p class="muted small">No BI line with the same LWIN, vintage and size: moved, sold, or a detail to fix on the wine.</p>
			<div class="table-wrap">
				<table>
					<thead><tr><th>Wine</th><th class="num">Btl</th><th>Location</th><th>LWIN</th><th class="num">App value</th></tr></thead>
					<tbody>
						{#each reply.app_only as b (b.bottle_id)}
							<tr>
								<td>
									<span class="end"><BottleEnd region={regionColor(b.region)} color={b.color} format={b.format} size={11} title="{regionLabel(b.region)} · {b.color ?? ''}" /></span>
									<a href={links.bottle(b.bottle_id)}>{b.producer}{b.cuvee ? ` – ${b.cuvee}` : ''}</a>
									<span class="muted num">{b.vintage}</span>
									{#if b.format && b.format !== '75cl'}<span class="muted small">· {b.format}</span>{/if}
								</td>
								<td class="num">{b.qty}</td>
								<td class="small">{b.location}</td>
								<td class="small">{#if b.lwin}<span class="num">{b.lwin}</span>{:else}<span class="warn">none</span>{/if}</td>
								<td class="num">{gbp(b.value)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>

<style>
	.bar {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
		margin-bottom: 12px;
	}
	.bar p {
		margin: 0;
	}
	.bar-buttons {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: 8px;
	}
	.apply {
		padding: 12px;
		margin-bottom: 14px;
	}
	.apply-buttons {
		display: flex;
		gap: 8px;
		margin-top: 10px;
	}
	.small {
		font-size: 12px;
	}
	.error {
		color: var(--down);
	}
	.kpis {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
		gap: 12px;
		margin-bottom: 14px;
	}
	.kpi {
		padding: 10px 12px;
		border: 1px solid var(--border);
		border-radius: 10px;
	}
	.label {
		font-size: 12px;
		color: var(--muted);
	}
	.value {
		font-size: 20px;
		font-weight: 650;
	}
	.sub {
		font-size: 12px;
	}
	.table-wrap {
		overflow-x: auto;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 13px;
	}
	th,
	td {
		padding: 6px 8px;
		border-bottom: 1px solid var(--border);
		text-align: left;
		vertical-align: top;
	}
	th {
		font-size: 12px;
		color: var(--muted);
		font-weight: 600;
		white-space: nowrap;
	}
	.num {
		text-align: right;
		white-space: nowrap;
	}
	.sort {
		border: none;
		background: none;
		padding: 0;
		font: inherit;
		color: inherit;
		cursor: pointer;
		white-space: nowrap;
	}
	.sort.on {
		color: var(--text);
	}
	.warn {
		color: var(--down);
		margin-left: 4px;
	}
	h3 {
		font-size: 14px;
		margin: 20px 0 4px;
	}
	.by-name {
		margin-top: 3px;
		color: var(--muted);
		font-size: 11px;
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		margin-left: 6px;
		color: var(--accent);
		cursor: pointer;
		font-size: 11px;
	}
	.end {
		display: inline-flex;
		margin-right: 7px;
		vertical-align: -1px;
	}
</style>

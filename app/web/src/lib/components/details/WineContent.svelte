<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { messageOf, request } from '#lib/api/http.ts';
	import MaturityBadge from '#lib/components/MaturityBadge.svelte';
	import type { WineDetail } from '#lib/api/details.ts';
	import { shapesUrl } from '#lib/api/details.ts';
	import type { RegionColors } from '#lib/types.ts';
	import { links } from '#lib/links.ts';
	import CellarSection from './CellarSection.svelte';
	import DetailHeader from './DetailHeader.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import DetailMap from './DetailMap.svelte';
	import WineStyle from './WineStyle.svelte';
	import CriticScores from './CriticScores.svelte';
	import Tabs from './Tabs.svelte';
	import TastingHistory from './TastingHistory.svelte';
	import WineActions from './WineActions.svelte';
	import ActionMenu from '#lib/components/ActionMenu.svelte';
	import ListsPanel from './ListsPanel.svelte';
	import WineLabel from './WineLabel.svelte';
	import { appSettings } from '#lib/settings.svelte.ts';
	import Icon from '#lib/components/Icon.svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		wine: WineDetail;
		regionColors: RegionColors;
		/** under the header, part of its card: the bottle a bottle's page is about */
		bottle?: Snippet;
		/** that bottle's id: its line marked in the Cellar tab */
		bottleId?: number | null;
	}

	let { wine, regionColors, bottle, bottleId = null }: Props = $props();

	let allVintages = $state(false);
	// Add a critic's score, add to a list (the header's icons): their card's form, shown even when it has nothing yet
	let addingScore = $state(false);
	let addingToList = $state(false);
	// Style tags (the menu): the picker under the appellation
	let editingStyle = $state(false);
	// The drinking window (the menu): its years set by hand, under the appellation
	let editingDrink = $state(false);
	let drinkStart = $state<number | null>(null);
	let drinkEnd = $state<number | null>(null);
	let drinkError = $state('');
	function openDrink() {
		[drinkStart, drinkEnd] = wine.drink_window;
		drinkError = '';
		editingDrink = true;
	}
	async function saveDrink(start: number | null, end: number | null) {
		drinkError = '';
		try {
			await request(`/api/wines/${wine.id}/drink-window`, { method: 'PUT', body: { start, end } });
			editingDrink = false;
			await invalidateAll();
		} catch (e) {
			drinkError = messageOf(e);
		}
	}
	// a plug-in action's busy text, then its answer (WineActions), beside the menu
	let said = $state<{ text: string; busy: boolean; error?: boolean } | null>(null);
	// Draw vineyard: drawn on the wine's map (DetailMap), created with its outline and linked to the wine
	let drawingVineyard = $state(false);
	// its label (WineLabel): the menu's Upload its label opens its file picker
	let label = $state<ReturnType<typeof WineLabel>>();

	const sum = (xs: { qty: number }[]) => xs.reduce((n, b) => n + b.qty, 0);
	const cellarHere = $derived(wine.cellar.filter((b) => b.wine_id === wine.id));
	const tastingsHere = $derived(wine.tastings.filter((t) => t.wine_id === wine.id));
	const cellar = $derived(allVintages ? wine.cellar : cellarHere);
	const tastings = $derived(allVintages ? wine.tastings : tastingsHere);

	const inCellar = $derived(wine.vintages.filter((v) => v.bottles));
	const tasted = $derived(wine.vintages.filter((v) => v.tastings));
	// The vintages by decade, newest first: a row each, a slot a year (0 to 9, so the years line up from row to row);
	// the rest (NV...) on a line after
	type V = (typeof wine.vintages)[number];
	const decades = $derived.by(() => {
		const rows = new Map<number, V[][]>();
		const other: V[] = [];
		for (const v of wine.vintages) {
			const y = Number(/^(\d{4})/.exec(v.vintage)?.[1]);
			if (!y) {
				other.push(v);
				continue;
			}
			const d = y - (y % 10);
			if (!rows.has(d)) rows.set(d, Array.from({ length: 10 }, () => []));
			rows.get(d)![y % 10].push(v);
		}
		return { rows: [...rows].sort((a, b) => b[0] - a[0]), other };
	});
	const vTitle = (v: V) =>
		[v.vintage, v.bottles && `${v.bottles} in cellar`, v.tastings && `tasted ${v.tastings}×`, v.scores, v.lists?.length && `on ${v.lists.join(', ')}`]
			.filter(Boolean)
			.join(' · ');
	const showVintages = $derived(wine.vintages.length > 1 || inCellar.length > 0 || tasted.length > 0);

	const [drinkFrom, drinkTo] = $derived(wine.drink_window);
	// The header says the producer, cuvée, vintage, colour and region › appellation (the vineyard: on the map); this
	// line the rest:
	// under the appellation: its grapes (each linked), blend and drinking window, whichever it has (a sparkling wine's
	// disgorgement is in the title, smaller, after its vintage: "NV Disg. 24", the full date in its tooltip)
	const grapes = $derived(wine.grapes?.length ? wine.grapes : wine.varietal ? [{ id: 0, name: wine.varietal, share: null }] : []);
	const disgorged = $derived(wine.color?.startsWith('Bubbles') ? wine.disgorgement_date : null);
	const disgYear = $derived(disgorged?.match(/(\d{4})(?!.*\d{4})/)?.[1].slice(2) ?? disgorged);
	const drink = $derived(drinkFrom || drinkTo ? `${drinkFrom ?? '…'}–${drinkTo ?? '…'}` : null);
	// its appellation's or vineyard's map, else its region's (the page keeps its layout, the map behind it)
	const hasMap = $derived(!!(wine.appellation || wine.vineyard || wine.region));

	// A lieu-dit clicked on the map: this wine's vineyard (and its cuvée's other vintages')
	const lieuAction = $derived({
		label: wine.vineyard ? 'Make it this wine’s vineyard instead' : 'Make it this wine’s vineyard',
		run: async (id: string) => {
			const r = await fetch(`/api/wines/${wine.id}/lieu-dit`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ lieu_dit: id })
			});
			if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? `Error ${r.status}`);
			await invalidateAll();
		}
	});
</script>

{#snippet title()}
	<span class="bottle"><BottleEnd region={wine.region_color} color={wine.color} size={20} /></span>
	<a class="producer" href={links.producer(wine.producer.id)}>{wine.producer.name}</a>
	<!-- Without a cuvée name the appellation is the headline -->
	{wine.cuvee || wine.appellation?.name || ''}
	<a class="muted num vintage" href={links.vintage(wine.vintage)}>{disgorged && wine.vintage.startsWith('NV') ? 'NV' : wine.vintage}</a>{#if disgorged}<span class="muted disg" title="Disgorged {disgorged}">Disg. <span class="num">{disgYear}</span></span>{/if}
{/snippet}

{#snippet actions()}
	<!-- the ⋯ menu, the one to hand under it: a tasting -->
	<ActionMenu>
		<a class="menu-item" role="menuitem" href={links.newBottle({ wine_id: wine.id })}><Icon name="bottle" size={15} />Add a bottle</a>
		<button class="menu-item" role="menuitem" onclick={() => (addingScore = true)}><Icon name="medal" size={15} />Add a critic's score</button>
		<WineActions wineId={wine.id} actions={wine.actions} bind:said />
		<button class="menu-item" role="menuitem" onclick={() => (addingToList = true)}><Icon name="list" size={15} />Add to a list</button>
		<button class="menu-item" role="menuitem" onclick={() => (editingStyle = true)}><Icon name="tag" size={15} />{wine.tags?.some((t) => t.set) ? 'Edit its style' : 'Add its style'}</button>
		{#if !bottle && appSettings.wine_labels !== 'off'}
			<button class="menu-item" role="menuitem" onclick={() => label?.pick()}><Icon name="tag" size={15} />{wine.label && !wine.label.from_vintage ? 'Replace its label' : 'Upload its label'}</button>
			{#if wine.label && !wine.label.from_vintage}
				<button class="menu-item" role="menuitem" onclick={() => label?.remove()}><Icon name="tag" size={15} />Remove its label</button>
			{/if}
		{/if}
		<button class="menu-item" role="menuitem" onclick={openDrink}><Icon name="calendar" size={15} />{drink ? 'Edit its drinking window' : 'Add a drinking window'}</button>
		<hr />
		<a class="menu-item" role="menuitem" href={links.editWine(wine.id)}><Icon name="edit" size={15} />Edit wine</a>
		<button class="menu-item" role="menuitem" onclick={() => (drawingVineyard = true)}><Icon name="draw" size={15} />{wine.vineyard ? 'Change its vineyard' : 'Add its vineyard'}</button>
	</ActionMenu>
	<a class="btn icon primary" href={links.newTasting({ wine_id: wine.id })} title="Add a tasting" aria-label="Add a tasting"><span class="plus">+</span><Icon name="glass" size={15} /></a>
	{#if said?.text}<span class="said small" class:muted={!said.error} class:error={said.error} class:busy={said.busy} role="status">{said.text}</span>{/if}
{/snippet}

{#snippet map()}
	<!-- its vineyard in the address: a new one (linked from the map) is drawn at once -->
	<DetailMap src={`${shapesUrl('wines', wine.id)}?vineyard=${wine.vineyard?.id ?? ''}`} height={300}
		frame={wine.vineyard ? { kind: 'vineyard', id: wine.vineyard.id } : null} empty="No map for this wine’s appellation or region yet." {lieuAction}
		draw={drawingVineyard ? { kind: 'vineyards', name: '', wine: wine.id } : null}
		ondrawn={(saved) => {
			drawingVineyard = false;
			if (saved) invalidateAll();
		}} />
{/snippet}

{#snippet under()}
	{#if grapes.length || wine.blend || drink}
		<p class="about">
			{#if grapes.length}<span class="grape-icon" aria-hidden="true"><Icon name="grape" size={13} /></span>{/if}{#each grapes as g, i (g.name)}{#if i}, {/if}<a href={links.grape(g.name)}>{g.name}</a>{#if g.share && g.share < 100}{' '}<span class="muted num">{+g.share.toFixed(1)}%</span>{/if}{/each}
			{#if wine.blend}<span class="item">{wine.blend}</span>{/if}
			{#if drink}<span class="item">Drink <span class="num">{drink}</span>{#if wine.maturity}{' '}<MaturityBadge maturity={wine.maturity} />{/if}</span>{/if}
		</p>
	{/if}
	{#if editingDrink}
		<form class="drink-edit" onsubmit={(e) => { e.preventDefault(); saveDrink(drinkStart, drinkEnd); }}>
			<span class="muted">Drink</span>
			<input type="number" min="1900" max="2200" placeholder="from" aria-label="From" bind:value={drinkStart} />
			<span class="muted">–</span>
			<input type="number" min="1900" max="2200" placeholder="to" aria-label="To" bind:value={drinkEnd} />
			<button class="btn primary">Save</button>
			<button type="button" class="btn" onclick={() => (editingDrink = false)}>Cancel</button>
			{#if drink}<button type="button" class="btn" onclick={() => saveDrink(null, null)}>Clear</button>{/if}
			{#if drinkError}<span class="error">{drinkError}</span>{/if}
		</form>
	{/if}
	<WineStyle wineId={wine.id} tags={wine.tags ?? []} cuvee={wine.cuvee_tags ?? []} bind:editing={editingStyle} />
{/snippet}

<DetailHeader
	kind={['Wine', wine.color].filter(Boolean).join(' · ')}
	{title}
	trail={[
		wine.region,
		wine.appellation && { label: wine.appellation.name, href: links.appellation(wine.appellation.id) }
	]}
	regionColor={wine.region_color}
	regionHref={wine.region ? links.region(wine.region) : null}
	{actions}
	{under}
	aside={hasMap ? map : undefined}
	footer={bottle}
>
	<div class="beside-label">
		<!-- its label, drawn (the wine's page: a bottle's has its own band) -->
		{#if !bottle}
			<WineLabel bind:this={label} wineId={wine.id} producer={wine.producer.name} cuvee={wine.cuvee}
				place={wine.appellation?.name ?? wine.region} vintage={wine.vintage} color={wine.color} shape={wine.label_shape}
				uploaded={wine.label} region={wine.region_color} />
		{/if}
		<!-- the lists naming this vintage, another one, or the cuvée (its producer's: the producer's page) -->
		<div class="lists"><ListsPanel inline wineId={wine.id} bind:adding={addingToList} /></div>
	</div>
</DetailHeader>

<div class="row">
		<CriticScores wineId={wine.id} scores={wine.scores} bind:adding={addingScore} />
		{#if showVintages}
			<section class="card vintages">
				<h2>Vintages <span class="muted num">{wine.vintages.length}</span>
				</h2>
				<div class="decades">
					{#each decades.rows as [d, slots] (d)}
						<span class="decade num">{d}s</span>
						{#each slots as vs, i (i)}
							<span class="slot">
								{#each vs as v (v.id)}
									<a class="cell num" class:current={v.id === wine.id} class:owned={v.bottles > 0} class:tasted={v.tastings > 0} href={links.wine(v.id)} title={vTitle(v)}>
										<span class="yy">’{String(d + i).slice(2)}</span>
										<span class="marks">
											{#if v.bottles}<span class="n">{v.bottles}</span>{/if}{#if v.tastings}<span class="tick">✓</span>{/if}{#if v.lists?.length}<span class="listed"><Icon name="bookmark" size={9} /></span>{/if}
										</span>
										<span class="sc">{v.score ? String(v.score).replace(/[()]/g, '') : ''}</span>
									</a>
								{:else}
									<span class="cell none num" aria-hidden="true">’{String(d + i).slice(2)}</span>
								{/each}
							</span>
						{/each}
					{/each}
				</div>
				{#if decades.other.length}
				<div class="chips other">
					{#each decades.other as v (v.id)}
						<a
							class="chip num"
							class:current={v.id === wine.id}
							class:owned={v.bottles > 0}
							href={links.wine(v.id)}
							title={[v.bottles && `${v.bottles} in cellar`, v.tastings && `tasted ${v.tastings}×`, v.scores, v.lists?.length && `on ${v.lists.join(', ')}`].filter(Boolean).join(' · ') || undefined}
						>
							{v.vintage}{#if v.bottles}<span class="n">{v.bottles}</span>{/if}{#if v.tastings}<span class="tick">✓</span>{/if}{#if v.score}<span class="score">{v.score}</span>{/if}{#if v.lists?.length}<span class="listed"><Icon name="bookmark" size={11} /></span>{/if}
						</a>
					{/each}
				</div>
				{/if}
			</section>
		{/if}
	</div>


<Tabs
	tabs={[
		{ id: 'cellar', label: 'Cellar', count: sum(cellar) },
		{ id: 'history', label: 'History', count: tastings.length }
	]}
	initial={!cellarHere.length && tastingsHere.length ? 'history' : 'cellar'}
>
	{#snippet tools()}
		{#if wine.vintages.length > 1}
			<div class="seg">
				<button class:on={!allVintages} onclick={() => (allVintages = false)}>This vintage</button>
				<button class:on={allVintages} onclick={() => (allVintages = true)}>All vintages</button>
			</div>
		{/if}
	{/snippet}
	{#snippet children(tab)}
		{#if tab === 'cellar'}
			<CellarSection
				plain
				current={bottleId}
				bottles={cellar}
				{regionColors}
				empty={allVintages ? 'No bottles of any vintage in stock.' : 'No bottles of this vintage in stock.'}
			/>
		{:else}
			<TastingHistory
				{tastings}
				{regionColors}
				empty={allVintages ? 'No tasting notes for any vintage.' : 'No tasting notes for this vintage.'}
			/>
		{/if}
	{/snippet}
</Tabs>

<style>
	/* the label centred in the header's column, the lists under it */
	.beside-label {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 14px;
	}
	.beside-label .lists {
		align-self: stretch;
		min-width: 0;
	}
	.beside-label:empty,
	.lists:empty {
		display: none;
	}
	.said {
		max-width: 180px;
		text-align: right;
	}
	.said.error {
		color: var(--down);
	}
	.said.busy {
		animation: pulse 1.2s ease-in-out infinite;
	}
	@keyframes pulse {
		50% {
			opacity: 0.45;
		}
	}
	/* the grapes, blend, drinking window: one line under the appellation */
	.about {
		margin: 2px 0 0;
		font-size: 13px;
		line-height: 1.5;
	}
	/* the drinking window's years, set from the menu */
	.drink-edit {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		margin-top: 8px;
		font-size: 13px;
	}
	.drink-edit input {
		width: 76px;
		padding: 4px 7px;
		border: 1px solid var(--border);
		border-radius: 7px;
		background: var(--surface);
		font: inherit;
		color: inherit;
	}
	.drink-edit .btn {
		padding: 4px 10px;
		font-size: 12px;
	}
	.drink-edit .error {
		color: var(--down);
		font-size: 12px;
	}
	.grape-icon {
		display: inline-flex;
		vertical-align: -2px;
		margin-right: 5px;
		color: var(--muted);
	}
	.about a {
		color: inherit;
	}
	.about a:hover {
		color: var(--accent);
	}
	.about .item::before {
		content: '·';
		margin: 0 8px;
		color: var(--muted);
	}
	.about > .item:first-child::before {
		content: none;
		margin: 0;
	}
	.bottle {
		display: inline-block;
		margin-right: 8px;
		transform: translateY(-2px);
	}
	.producer:hover,
	.vintage:hover {
		color: var(--accent);
	}
	/* a sparkling wine's disgorgement, after its vintage: smaller */
	.disg {
		margin-left: 6px;
		font-size: 0.55em;
		font-weight: 400;
		white-space: nowrap;
	}
	.row {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
		gap: 14px;
		margin-bottom: 14px;
	}
	.row > .card {
		padding: 14px 18px;
	}
	h2 {
		font-size: 14px;
		margin: 0 0 10px;
	}
	/* by decade: the decade, then ten slots, small */
	.decades {
		display: grid;
		grid-template-columns: auto repeat(10, minmax(0, 1fr));
		gap: 4px 3px;
		align-items: stretch;
	}
	.decade {
		align-self: center;
		padding-right: 6px;
		font-size: 11px;
		color: var(--muted);
	}
	.slot {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.cell {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		/* one height for all: the year, the marks, the score, each in its line, empty or not */
		box-sizing: border-box;
		height: 44px;
		padding: 2px 0;
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 12px;
		line-height: 1.15;
		color: var(--muted);
		text-decoration: none;
	}
	.cell.tasted {
		color: var(--text);
		background: var(--surface-2);
	}
	.cell.owned {
		color: var(--text);
		border-color: var(--gold-text);
	}
	a.cell:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
	.cell.current {
		background: var(--accent);
		border-color: var(--accent);
		color: var(--on-accent);
	}
	.cell.current .n,
	.cell.current .tick,
	.cell.current .listed,
	.cell.current .sc {
		color: var(--on-accent);
	}
	/* a year without a vintage: its place kept, faint */
	.cell.none {
		border-style: dashed;
		border-color: color-mix(in srgb, var(--border) 60%, transparent);
		color: color-mix(in srgb, var(--muted) 40%, transparent);
	}
	.marks {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		min-height: 12px;
		font-size: 10px;
	}
	.marks .tick {
		font-size: 10px;
	}
	.marks .listed {
		margin-left: 0;
	}
	.sc {
		min-height: 11px;
		white-space: nowrap;
		font-size: 9.5px;
		font-weight: 600;
		color: var(--accent);
	}
	.other {
		margin-top: 8px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 1px 9px;
		border-radius: 10px;
		border: 1px solid var(--border);
		font-size: 12px;
	}
	.chip:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
	.chip.owned {
		border-color: var(--gold-text);
	}
	.chip.current {
		background: var(--accent);
		border-color: var(--accent);
		color: var(--on-accent);
	}
	.chip.current .n,
	.chip.current .tick,
	.chip.current .listed {
		color: var(--on-accent);
	}
	/* the score's pill on the selected vintage: white, as its other marks */
	.chip.current .score {
		color: var(--on-accent);
		border-color: rgba(255, 255, 255, 0.7);
	}
	.n {
		font-weight: 650;
		color: var(--gold-text);
	}
	.score {
		margin-left: 4px;
		font-size: 10px;
		font-weight: 600;
		line-height: 13px;
		padding: 0 4px;
		border-radius: 6px;
		border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
		color: var(--accent);
	}
	.listed {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		margin-left: 4px;
		color: var(--accent);
	}
	.listed :global(.icon) {
		fill: currentColor;
	}
	.tick {
		color: var(--accent);
		font-size: 11px;
	}
	.seg button {
		padding: 4px 10px;
		font-size: 12px;
	}
</style>

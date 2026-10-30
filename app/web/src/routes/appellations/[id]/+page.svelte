<script lang="ts">
	import ActionMenu from '#lib/components/ActionMenu.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { shapesUrl } from '#lib/api/details.ts';
	import CellarSection from '#lib/components/details/CellarSection.svelte';
	import DetailHeader from '#lib/components/details/DetailHeader.svelte';
	import DetailMap from '#lib/components/details/DetailMap.svelte';
	import Facts from '#lib/components/details/Facts.svelte';
	import Stats from '#lib/components/details/Stats.svelte';
	import Tabs from '#lib/components/details/Tabs.svelte';
	import TastingHistory from '#lib/components/details/TastingHistory.svelte';
	import { fmtDate, splitList } from '#lib/components/details/wine.ts';
	import { links } from '#lib/links.ts';
	import { money } from '#lib/format.ts';
	import { invalidateAll } from '$app/navigation';

	let { data } = $props();
	const a = $derived(data.detail);
	const varieties = $derived(splitList(a.varieties));
	const yields = $derived([a.max_yield_hl && `${a.max_yield_hl} hl/ha`, a.max_yield_kg && `${a.max_yield_kg} kg/ha`].filter(Boolean).join(', '));
	const colors = $derived([...new Set(splitList(a.colors))].join(', '));

	// Its own outline, drawn or imported on its map (DetailMap, OutlineTools): the map reloads once one is saved or removed
	let drawing = $state(false);
	let mapRev = $state(0);
	function outlineClosed(saved: boolean) {
		drawing = false;
		if (saved) {
			mapRev++;
			invalidateAll();
		}
	}
</script>

<svelte:head><title>{a.name} · WineLib</title></svelte:head>

{#snippet actions()}
	<ActionMenu>
		<button class="menu-item" role="menuitem" onclick={() => (drawing = true)}><Icon name="draw" size={15} />Draw its outline</button>
		<hr />
		<a class="menu-item" role="menuitem" href={links.editAppellation(a.id)}><Icon name="edit" size={15} />Edit appellation</a>
	</ActionMenu>
	<a class="btn icon" href={links.map({ region: a.region, ap: a.id, sel: `appellation:${a.id}` })} title="Open on the map" aria-label="Open on the map"><Icon name="map" size={15} /></a>
{/snippet}

{#snippet map()}
	{#key mapRev}
		<DetailMap draw={drawing ? { kind: 'appellations', id: a.id, name: a.name } : null} ondrawn={outlineClosed}
			src={shapesUrl('appellations', a.id)} fullUrl={a.full_outline ? `/api/appellations/${a.id}/outline/full` : null} current={{ kind: 'appellation', id: a.id }} height={320} />
	{/key}
{/snippet}

{#key a.id}
	<DetailHeader
		kind={['Appellation', a.type].filter(Boolean).join(' · ')}
		icon="map"
		title={a.name}
		trail={[a.region ?? 'Unknown', a.subregion]}
		regionColor={a.region_color}
		regionHref={a.region ? links.region(a.region) : null}
		{actions}
		aside={map}
	>
		<Facts
			items={[
				{ label: 'Also known as', value: a.aliases },
				{ label: 'Category', value: a.category },
				{ label: 'Colors', value: colors },
				{ label: 'PDO ID', value: a.pdo_id && `${a.pdo_id}${a.registration_date ? ` (reg. ${fmtDate(a.registration_date)})` : ''}` },
				{ label: 'Max yield', value: yields },
				{ label: 'Official info', value: a.location_link && 'EU register', href: a.location_link }
			]}
		/>
		{#if varieties.length}
			<details class="fold" open>
				<summary>Authorized varieties ({varieties.length})</summary>
				<div class="chips">{#each varieties as v, i (i)}<span class="chip">{v}</span>{/each}</div>
			</details>
		{/if}
		{#if a.details}
			<details class="fold">
				<summary>Details</summary>
				<p>{a.details}</p>
			</details>
		{/if}
		<div class="stats">
			<Stats
				items={[
					{ label: 'Bottles in cellar', value: a.stats.bottles, sub: a.stats.value ? money(a.stats.value) : undefined, gold: a.stats.bottles > 0 },
					{ label: 'Wines tasted', value: a.stats.tastings },
					{ label: 'Producers', value: a.producers.length }
				]}
			/>
		</div>
	</DetailHeader>

	<Tabs
		tabs={[
			{ id: 'history', label: 'History', count: a.tastings.length },
			{ id: 'cellar', label: 'Cellar', count: a.stats.bottles },
			{ id: 'producers', label: 'Producers', count: a.producers.length },
			{ id: 'vineyards', label: 'Vineyards', count: a.vineyards.length }
		]}
		initial={a.tastings.length || !a.stats.bottles ? 'history' : 'cellar'}
	>
		{#snippet children(tab)}
			{#if tab === 'history'}
				<TastingHistory tastings={a.tastings} regionColors={data.regionColors} empty="No tastings for this appellation." />
			{:else if tab === 'cellar'}
				<CellarSection bottles={a.cellar} regionColors={data.regionColors} empty="No bottles in the cellar from this appellation." />
				{#if a.cellar.length}<a class="more" href={links.cellar({ appellation: a.name })}>Open in the cellar →</a>{/if}
			{:else if tab === 'vineyards'}
				{#if a.vineyards.length}
					<ul class="producers">
						{#each a.vineyards as v (v.id)}
							<li>
								<a href={links.vineyard(v.id)}>{v.name}</a>{#if v.village && v.village !== v.name}<span class="muted"> · {v.village}</span>{/if}
								<span class="muted num">{v.wines}</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="muted">No vineyards recorded for this appellation’s wines.</p>
				{/if}
			{:else if a.producers.length}
				<ul class="producers">
					{#each a.producers as pr (pr.id)}
						<li><a href={links.producer(pr.id)}>{pr.name}</a> <span class="muted num">{pr.wines}</span></li>
					{/each}
				</ul>
			{:else}
				<p class="muted">No producers recorded for this appellation.</p>
			{/if}
		{/snippet}
	</Tabs>
{/key}


<style>
	.fold {
		margin-top: 12px;
	}
	.fold summary {
		cursor: pointer;
		color: var(--accent);
		font-size: 13px;
	}
	.fold p {
		margin: 6px 0 0;
		white-space: pre-line;
		max-height: 220px;
		overflow-y: auto;
		font-size: 13px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		margin-top: 8px;
	}
	.chip {
		padding: 1px 9px;
		border-radius: 10px;
		background: var(--surface-2);
		border: 1px solid var(--border);
		font-size: 12px;
	}
	.stats {
		margin-top: 16px;
	}
	.more {
		display: inline-block;
		margin-top: 6px;
		font-size: 13px;
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.more:hover {
		color: var(--accent);
	}
	.producers {
		list-style: none;
		margin: 0;
		padding: 0;
		columns: 3 220px;
		column-gap: 24px;
	}
	.producers li {
		padding: 3px 0;
		break-inside: avoid;
	}
	.producers a:hover {
		color: var(--accent);
	}
</style>

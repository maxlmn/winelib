<script lang="ts">
	import { regionLabel } from '#lib/regions.svelte.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { shapesUrl } from '#lib/api/details.ts';
	import CellarSection from '#lib/components/details/CellarSection.svelte';
	import DetailHeader from '#lib/components/details/DetailHeader.svelte';
	import DetailMap from '#lib/components/details/DetailMap.svelte';
	import OutlineEditor from '#lib/components/details/OutlineEditor.svelte';
	import Facts from '#lib/components/details/Facts.svelte';
	import Stats from '#lib/components/details/Stats.svelte';
	import Tabs from '#lib/components/details/Tabs.svelte';
	import TastingHistory from '#lib/components/details/TastingHistory.svelte';
	import WineCatalog from '#lib/components/details/WineCatalog.svelte';
	import { links } from '#lib/links.ts';
	import { money } from '#lib/format.ts';
	import { invalidateAll } from '$app/navigation';

	let { data } = $props();
	const v = $derived(data.detail);
	const nWines = $derived(v.wines.reduce((n, w) => n + w.vintages.length, 0));
	const location = $derived([regionLabel(v.region), v.subregion, v.village].filter(Boolean).join(' › '));

	// Its own outline, drawn or imported (OutlineEditor): the map reloads once one is saved or removed
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

<svelte:head><title>{v.name} · WineLib</title></svelte:head>

{#snippet actions()}
	<a class="btn" href={links.map({ region: v.region, sel: `vineyard:${v.id}` })}>Open on the map</a>
	<a class="btn" href={links.editVineyard(v.id)}>Edit vineyard</a>
	<button class="btn" onclick={() => (drawing = true)}>Draw outline</button>
{/snippet}

{#snippet map()}
	{#key mapRev}
		<DetailMap
			src={shapesUrl('vineyards', v.id)} fullUrl={v.full_outline ? `/api/vineyards/${v.id}/outline/full` : null}
			current={{ kind: 'vineyard', id: v.id }}
			focusable
			height={320}
			empty="No geographical data available for this vineyard."
		/>
	{/key}
{/snippet}

{#key v.id}
	<DetailHeader kind={v.lieu_dit ? 'Vineyard · lieu-dit' : 'Vineyard'} title={v.name} trail={[v.region, v.subregion, v.village]} regionColor={v.region_color} regionHref={v.region ? links.region(v.region) : null} {actions} aside={map}>
		<Facts items={[{ label: 'Location', value: location, icon: 'globe' }, { label: 'External ID', value: v.vineyard_id }]} />
		{#if v.lieu_dit}
			<div class="lieu">
				<div>
					<span class="muted">Lieu-dit</span> {v.lieu_dit.name}{v.lieu_dit.village ? `, ${v.lieu_dit.village}` : ''}
					{#if v.lieu_dit.vines}<span class="muted"> · {Math.round(v.lieu_dit.vines * 100)}% in AOC vines</span>{/if}
				</div>
				{#if v.lieu_dit.aocs.length}<div><span class="muted">Its land is eligible for</span> {v.lieu_dit.aocs.join(' · ')}</div>{/if}
				<div class="muted note">Outline from the cadastre (Etalab, DGFiP), the appellations from INAO's delimitation: informational, not legally binding.</div>
			</div>
		{/if}
		{#if v.appellations.length}
			<div class="apps">
				<span class="muted"><Icon name="map" size={13} /> Appellations</span>
				{#each v.appellations as ap (ap.id)}<a class="chip" href={links.appellation(ap.id)}>{ap.name}</a>{/each}
			</div>
		{/if}
		<div class="stats">
			<Stats
				items={[
					{ label: 'Bottles in cellar', value: v.stats.bottles, sub: v.stats.value ? money(v.stats.value) : undefined, gold: v.stats.bottles > 0 },
					{ label: 'Wines tasted', value: v.stats.tastings },
					{ label: 'Wines', value: nWines }
				]}
			/>
		</div>
	</DetailHeader>

	<Tabs
		tabs={[
			{ id: 'cellar', label: 'Cellar', count: v.stats.bottles },
			{ id: 'history', label: 'History', count: v.tastings.length },
			{ id: 'wines', label: 'Wines', count: nWines }
		]}
		initial={v.stats.bottles ? 'cellar' : v.tastings.length ? 'history' : 'wines'}
	>
		{#snippet children(tab)}
			{#if tab === 'cellar'}
				<CellarSection bottles={v.cellar} regionColors={data.regionColors} empty="No bottles from this vineyard currently in the cellar." />
			{:else if tab === 'history'}
				<TastingHistory tastings={v.tastings} regionColors={data.regionColors} empty="No tasting history for this vineyard." />
			{:else}
				<WineCatalog wines={v.wines} showProducer />
			{/if}
		{/snippet}
	</Tabs>
{/key}

{#if drawing}<OutlineEditor kind="vineyards" id={v.id} name={v.name} onclose={outlineClosed} />{/if}

<style>
	.apps {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		margin-top: 12px;
	}
	.apps .muted {
		margin-right: 6px;
	}
	.chip {
		padding: 1px 10px;
		border-radius: 10px;
		border: 1px solid var(--border);
		background: var(--surface-2);
		font-size: 12px;
	}
	.chip:hover {
		border-color: var(--accent);
	}
	.stats {
		margin-top: 16px;
	}
	.lieu {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin-top: 10px;
		font-size: 13px;
	}
	.lieu .note {
		font-size: 11px;
	}
</style>

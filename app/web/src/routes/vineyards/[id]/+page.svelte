<script lang="ts">
	import ActionMenu from '#lib/components/ActionMenu.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { shapesUrl } from '#lib/api/details.ts';
	import CellarSection from '#lib/components/details/CellarSection.svelte';
	import DetailHeader from '#lib/components/details/DetailHeader.svelte';
	import DetailMap from '#lib/components/details/DetailMap.svelte';
	import Tabs from '#lib/components/details/Tabs.svelte';
	import TastingHistory from '#lib/components/details/TastingHistory.svelte';
	import WineCatalog from '#lib/components/details/WineCatalog.svelte';
	import { links } from '#lib/links.ts';
	import { money } from '#lib/format.ts';
	import { invalidateAll } from '$app/navigation';
	import { request } from '#lib/api/http.ts';

	let { data } = $props();
	const v = $derived(data.detail);
	const nWines = $derived(v.wines.reduce((n, w) => n + w.vintages.length, 0));

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

	// A lieu-dit clicked on the map: this vineyard's outline (its wines keep it), as a wine's map makes one its vineyard
	const lieuAction = $derived({
		label: v.lieu_dit || v.drawn ? 'Make it this vineyard’s outline instead' : 'Make it this vineyard’s outline',
		run: async (id: string) => {
			if (v.drawn && !confirm(`Replace the outline drawn for ${v.name} with this lieu-dit's?`)) return;
			await request(`/api/vineyards/${v.id}/lieu-dit`, { method: 'POST', body: { lieu_dit: id } });
			mapRev++;
			await invalidateAll();
		}
	});
</script>

<svelte:head><title>{v.name} · WineLib</title></svelte:head>

{#snippet actions()}
	<ActionMenu>
		<button class="menu-item" role="menuitem" onclick={() => (drawing = true)}><Icon name="draw" size={15} />Draw its outline</button>
		<hr />
		<a class="menu-item" role="menuitem" href={links.editVineyard(v.id)}><Icon name="edit" size={15} />Edit vineyard</a>
	</ActionMenu>
	<a class="btn icon" href={links.map({ region: v.region, sel: `vineyard:${v.id}` })} title="Open on the map" aria-label="Open on the map"><Icon name="map" size={15} /></a>
{/snippet}

{#snippet map()}
	{#key mapRev}
		<DetailMap draw={drawing ? { kind: 'vineyards', id: v.id, name: v.name } : null} ondrawn={outlineClosed}
			src={shapesUrl('vineyards', v.id)} fullUrl={v.full_outline ? `/api/vineyards/${v.id}/outline/full` : null}
			current={{ kind: 'vineyard', id: v.id }}
			{lieuAction}
			height={320}
			empty="No geographical data available for this vineyard."
		/>
	{/key}
{/snippet}

{#key v.id}
	<DetailHeader kind={v.lieu_dit ? 'Vineyard · lieu-dit' : 'Vineyard'} title={v.name} trail={[v.region, v.subregion, v.village]} regionColor={v.region_color} regionHref={v.region ? links.region(v.region) : null} {actions} aside={map}>
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
	</DetailHeader>

	<Tabs
		tabs={[
			{ id: 'cellar', label: 'Cellar', count: v.stats.bottles, note: v.stats.value ? money(v.stats.value) : undefined },
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

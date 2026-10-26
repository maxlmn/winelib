<script lang="ts">
	import { appSettings } from '#lib/settings.svelte.ts';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Breakdown from '#lib/components/summary/Breakdown.svelte';
	import Kpi from '#lib/components/summary/Kpi.svelte';
	import Highlights from '#lib/components/summary/Highlights.svelte';
	import Change from '#lib/components/Change.svelte';
	import { money, pct, plural } from '#lib/format.ts';
	import { links } from '#lib/links.ts';

	let { data } = $props();

	const TABS = [
		{ id: 'tastings', label: 'Tasting history' },
		{ id: 'cellar', label: 'Cellar inventory' }
	];

	const tab = $derived(page.url.searchParams.get('tab') === 'cellar' ? 'cellar' : 'tastings');
	const t = $derived(data.tastings);
	const c = $derived(data.cellar);
	const gain = $derived(pct(c.value, c.market));

	function setTab(id: string) {
		const p = new URLSearchParams(page.url.searchParams.toString());
		if (id === 'tastings') p.delete('tab');
		else p.set('tab', id);
		goto(`?${p}`, { replace: true, reset: false });
	}

	// Cellar charts open the cellar filtered on what was clicked; "NV" spans several disgorgements there, so no link
	const cellarHref = (key: 'color' | 'region' | 'vintage', value: string) =>
		key === 'vintage' && !/^\d+$/.test(value) ? undefined : links.cellar({ [key]: value });
</script>

<svelte:head><title>Summary · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Summary</h1>
	<div class="seg">
		{#each TABS as x}
			<button class:on={tab === x.id} onclick={() => setTab(x.id)}>{x.label}</button>
		{/each}
	</div>
</div>

{#if tab === 'tastings'}
	<div class="kpis">
		<Kpi label="Tasting notes" value={t.total} />
		<Kpi label="Unique wines" value={t.wines} />
		{#if t.avg_rating !== null}
			<Kpi label="Your average score" value={t.avg_rating} help="Over the tastings you scored">
				{#snippet sub()}{plural(t.rated, 'tasting')} scored{/snippet}
			</Kpi>
		{/if}
		<Kpi label="Unique Michelin stars" value={t.michelin.unique_stars} help="Sum of the stars of the distinct restaurants visited">
			{#snippet sub()}
				{#each t.michelin.restaurants as r, i}{i ? ' · ' : ''}<span class="gold">{'★'.repeat(r.stars)}</span> {r.count}{/each}
			{/snippet}
		</Kpi>
		<Kpi label="Total stars experience" value={t.michelin.total_stars} help="Stars summed over every visit day, with or without wine" />
	</div>
	{#if t.total}
		<Highlights tastings={t.highlights} />
		<Breakdown data={t} unit="tastings" />
	{:else}
		<p class="card empty muted">No tasting notes yet.</p>
	{/if}
{:else}
	<div class="kpis">
		<Kpi label="Bottles" value={c.total} />
		<Kpi label="Unique wines" value={c.wines} />
		<Kpi label="Estimated value" value={c.value ? money(c.value) : '–'} help={`What the bottles in stock cost, in ${appSettings.currency}`}>
			{#snippet sub()}
				{#if c.market}Market {money(c.market)} <Change value={gain} digits={1} />{:else}No market prices yet{/if}
			{/snippet}
		</Kpi>
	</div>
	{#if c.total}
		<Highlights cellar={c.highlights} />
		<Breakdown data={c} unit="bottles" filterHref={cellarHref} />
	{:else}
		<p class="card empty muted">No bottles in the cellar.</p>
	{/if}
{/if}

<style>
	.kpis {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
		gap: 12px;
		margin-bottom: 14px;
	}
	.gold {
		color: var(--gold);
	}
	.empty {
		padding: 16px;
	}
</style>

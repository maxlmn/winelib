<script lang="ts">
	import CriticPills from '#lib/components/CriticPills.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { FALLBACK_REGION, typeColor } from '#lib/colors.ts';
	import CellarSection from '#lib/components/details/CellarSection.svelte';
	import DetailHeader from '#lib/components/details/DetailHeader.svelte';
	import Stats from '#lib/components/details/Stats.svelte';
	import Tabs from '#lib/components/details/Tabs.svelte';
	import TastingHistory from '#lib/components/details/TastingHistory.svelte';
	import WineCatalog from '#lib/components/details/WineCatalog.svelte';
	import BarList from '#lib/components/summary/BarList.svelte';
	import { links } from '#lib/links.ts';
	import { plural, money } from '#lib/format.ts';

	let { data } = $props();
	const v = $derived(data.detail);

	// Where the vintage's wines come from: your bottles and tastings first, else the wines recorded
	const mine = $derived(v.regions.some((r) => r.bottles + r.tastings > 0));
	const regionBars = $derived(
		v.regions
			.map((r) => ({
				key: r.name,
				label: regionLabel(r.name),
				count: mine ? r.bottles + r.tastings : r.wines,
				color: r.color ?? FALLBACK_REGION,
				href: r.name === 'Unknown' ? undefined : links.region(r.name)
			}))
			.filter((b) => b.count > 0)
	);
	const TOP = 10;

	let onlyMine = $state(false);
	const best = $derived(v.best.filter((b) => !onlyMine || b.bottles > 0 || b.tastings > 0));
</script>

<svelte:head><title>{v.vintage} · WineLib</title></svelte:head>

{#snippet actions()}
	{#if v.prev}<a class="btn" href={links.vintage(v.prev)}>← {v.prev}</a>{/if}
	<a class="btn" href={links.vintages()}>All vintages</a>
	{#if v.next}<a class="btn" href={links.vintage(v.next)}>{v.next} →</a>{/if}
{/snippet}

{#snippet regions()}
	<h3 class="aside-h"><Icon name="globe" size={13} /> Where it comes from <span class="muted">({mine ? 'your bottles and tastings' : 'wines recorded'})</span></h3>
	<BarList bars={regionBars.slice(0, TOP)} total={regionBars.reduce((n, b) => n + b.count, 0)} unit={mine ? 'bottles and tastings' : 'wines'} />
	{#if regionBars.length > TOP}<p class="muted small">and {regionBars.length - TOP} more: {regionBars.slice(TOP).map((b) => b.label).join(', ')}</p>{/if}
{/snippet}

{#snippet badges(x: { bottles: number; tastings: number })}
	{#if x.tastings}<span class="badge tasted num" title={plural(x.tastings, 'tasting')}>✎ {x.tastings}</span>{/if}
	{#if x.bottles}<span class="badge num" title="{plural(x.bottles, 'bottle')} in the cellar">{x.bottles}</span>{/if}
{/snippet}

{#key v.vintage}
	<DetailHeader kind="Vintage" title={v.vintage === 'NV' ? 'Non-vintage' : v.vintage} {actions} aside={regionBars.length ? regions : undefined}>
		<Stats
			items={[
				{ label: 'Bottles in cellar', value: v.stats.bottles, sub: v.stats.value ? money(v.stats.value) : undefined, gold: v.stats.bottles > 0 },
				{ label: 'Wines tasted', value: v.stats.tastings },
				{ label: 'Wines', value: v.stats.wines },
				{ label: 'Producers', value: v.stats.producers },
				...(v.stats.score_mine ? [{ label: `Your wines’ ${v.stats.critic}`, value: v.stats.score_mine, sub: 'average, owned or tasted' }] : [])
			]}
		/>
	</DetailHeader>

	<Tabs
		tabs={[
			{ id: 'history', label: 'History', count: v.tastings.length },
			{ id: 'cellar', label: 'Cellar', count: v.stats.bottles },
			{ id: 'best', label: 'Best rated', count: v.stats.score_count },
			{ id: 'wines', label: 'Wines', count: v.stats.wines }
		]}
		initial={v.tastings.length || !v.stats.bottles ? 'history' : 'cellar'}
	>
		{#snippet children(tab)}
			{#if tab === 'history'}
				<TastingHistory tastings={v.tastings} regionColors={data.regionColors} empty="No tastings of this vintage yet." />
			{:else if tab === 'cellar'}
				<CellarSection bottles={v.cellar} regionColors={data.regionColors} empty="No bottles of this vintage in the cellar." />
			{:else if tab === 'best'}
				<label class="only">
					<input type="checkbox" bind:checked={onlyMine} />
					Only wines I have or tasted
				</label>
				<ol class="best">
					{#each best as b (b.id)}
						<li>
							<span class="score"><CriticPills scores={b.scores ?? b.score} /></span>
							<span class="dot" style:background={typeColor(b.color)}></span>
							<a href={links.wine(b.id)}><b>{b.producer}</b> {b.cuvee || b.appellation || ''}</a>
							{#if b.cuvee && b.appellation}<span class="muted small">{b.appellation}</span>{/if}
							{@render badges(b)}
						</li>
					{:else}
						<li class="muted">
							{#if v.stats.critic}No {v.stats.critic} scores {onlyMine ? 'for your wines of' : 'for'} this vintage.
							{:else}No critic scores yet: the first critic you add scores for (a wine’s page, or Maintenance › Import critic scores) ranks this list.{/if}
						</li>
					{/each}
				</ol>
				{#if v.stats.score_count > v.best.length}<p class="muted small">The best {v.best.length} of {v.stats.score_count} scored by {v.stats.critic} (Settings: preferred critic).</p>{/if}
			{:else}
				<WineCatalog wines={v.wines} showProducer />
			{/if}
		{/snippet}
	</Tabs>
{/key}

<style>
	.aside-h {
		font-size: 13px;
		font-weight: 600;
		margin: 0 0 8px;
	}
	.aside-h .muted {
		font-weight: 400;
		font-size: 12px;
	}
	.only {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		margin-bottom: 10px;
	}
	.best {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.best li {
		display: flex;
		align-items: baseline;
		gap: 8px;
		padding: 5px 0;
		border-top: 1px solid var(--border);
		font-size: 13px;
	}
	.best li:first-child {
		border-top: none;
	}
	.best a:hover {
		color: var(--accent);
	}
	.score {
		min-width: 54px;
	}
	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex: none;
		align-self: center;
	}
	.small {
		font-size: 12px;
	}
	.badge {
		font-size: 11px;
		font-weight: 600;
		color: var(--gold);
		box-shadow: inset 0 0 0 1px var(--gold);
		border-radius: 8px;
		padding: 0 6px;
	}
	.badge.tasted {
		color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
	}
</style>

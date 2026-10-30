<script lang="ts">
	import RegionName from '#lib/components/RegionName.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { FALLBACK_REGION, TYPE_COLORS } from '#lib/colors.ts';
	import AboutCard from '#lib/components/details/AboutCard.svelte';
	import CellarSection from '#lib/components/details/CellarSection.svelte';
	import RegionStrip from '#lib/components/RegionStrip.svelte';
	import { bottlePips, sortedByRegion, tastingPips } from '#lib/pips.ts';
	import DetailHeader from '#lib/components/details/DetailHeader.svelte';
	import Facts from '#lib/components/details/Facts.svelte';
	import GrapeFamily from '#lib/components/details/GrapeFamily.svelte';
	import { BERRY_COLORS } from '#lib/api/grapes.ts';
	import Tabs from '#lib/components/details/Tabs.svelte';
	import TastingHistory from '#lib/components/details/TastingHistory.svelte';
	import BarList from '#lib/components/summary/BarList.svelte';
	import { links } from '#lib/links.ts';
	import { plural, money } from '#lib/format.ts';

	let { data } = $props();
	const g = $derived(data.detail);
	const p = $derived(g.profile);
	const colour = $derived(g.color ?? p?.facts.find((f) => f.label === 'Colour')?.value ?? null);
	// Its parentage, when known, draws the family tree
	const hasFamily = $derived(g.family.parents.length > 0 || g.family.offspring.length > 0);
	const otherNames = $derived((g.aliases ?? '').split(',').map((s) => s.trim()).filter((n) => n && n !== g.name));

	// Where its wines come from: your bottles and tastings first, then the wines recorded
	const regionBars = $derived(
		g.regions.map((r) => ({
			key: r.name,
			label: regionLabel(r.name),
			count: r.bottles + r.tastings || r.wines,
			color: r.color ?? FALLBACK_REGION,
			href: links.region(r.name)
		}))
	);
	const mine = $derived(g.regions.some((r) => r.bottles + r.tastings > 0));

	let onlyMine = $state(false);
	const producers = $derived(g.producers.filter((pr) => !onlyMine || pr.bottles > 0 || pr.tastings > 0));
</script>

<svelte:head><title>{g.name} · WineLib</title></svelte:head>

{#snippet regions()}
	<h3 class="aside-h"><Icon name="globe" size={13} /> Where it comes from <span class="muted">({mine ? 'your bottles and tastings' : 'wines recorded'})</span></h3>
	<BarList bars={regionBars} total={regionBars.reduce((n, b) => n + b.count, 0)} unit={mine ? 'bottles and tastings' : 'wines'} />
{/snippet}

{#snippet badges(x: { bottles: number; tastings: number })}
	{#if x.tastings}<span class="badge tasted num" title={plural(x.tastings, 'tasting')}>✎ {x.tastings}</span>{/if}
	{#if x.bottles}<span class="badge num" title="{plural(x.bottles, 'bottle')} in the cellar">{x.bottles}</span>{/if}
{/snippet}

{#key g.id}
	<DetailHeader
		kind={colour ? `Grape · ${colour}` : 'Grape'}
		icon="grape"
		title={g.name}
		regionColor={colour ? (TYPE_COLORS[colour] ?? BERRY_COLORS[colour] ?? null) : null}
		aside={g.regions.length ? regions : undefined}
	>
		{#if g.tastings.length || g.cellar.length}
			<!-- Where yours come from: a pip per bottle and per tasting, in its region's color -->
			<div class="palette">
				<div class="caption">Your bottles and tastings</div>
				<RegionStrip pips={sortedByRegion([...bottlePips(g.cellar), ...tastingPips(g.tastings)])} height={14} />
			</div>
		{/if}
		{#if g.origin}<div class="profile"><Facts items={[{ label: 'Origin', value: g.origin }]} /></div>{/if}
		{#if !p && otherNames.length}
			<div class="profile"><Facts items={[{ label: 'Also known as', value: otherNames.join(', ') }]} /></div>
		{/if}
		{#if p}
			<div class="profile">
				<Facts items={[...(otherNames.length ? [{ label: 'Also known as', value: otherNames.join(', ') }] : []), ...p.facts]} />
				{#if p.notes}<p class="notes">{p.notes}</p>{/if}
				{#if p.regions.length}
					<details class="fold">
						<summary>Classic regions ({p.regions.length})</summary>
						<ul class="classic">{#each p.regions as r (r)}<li>{r}</li>{/each}</ul>
					</details>
				{/if}
			</div>
		{/if}
	</DetailHeader>

	{#if hasFamily}<GrapeFamily name={g.name} family={g.family} vivc={g.vivc} />{/if}

	<AboutCard src={`/api/grapes/${encodeURIComponent(String(g.id))}/about`} />

	<Tabs
		tabs={[
			{ id: 'history', label: 'History', count: g.tastings.length },
			{ id: 'cellar', label: 'Cellar', count: g.stats.bottles, note: g.stats.value ? money(g.stats.value) : undefined },
			{ id: 'producers', label: 'Producers', count: g.producers.length }
		]}
		initial={g.tastings.length || !g.stats.bottles ? 'history' : 'cellar'}
	>
		{#snippet children(tab)}
			{#if tab === 'history'}
				<TastingHistory tastings={g.tastings} regionColors={data.regionColors} empty="No tastings of this grape yet." />
			{:else if tab === 'cellar'}
				<CellarSection bottles={g.cellar} regionColors={data.regionColors} empty="No bottles of this grape in the cellar." />
			{:else}
				<label class="only">
					<input type="checkbox" bind:checked={onlyMine} />
					Only where I have bottles or tastings
				</label>
				<ul class="cols">
					{#each producers as pr (pr.id)}
						<li>
							<a href={links.producer(pr.id)}>{pr.name}</a>
							{#if pr.region}<a class="muted region" href={links.region(pr.region)}><RegionName name={pr.region} /></a>{/if}
							{@render badges(pr)}
						</li>
					{:else}
						<li class="muted">No producers {onlyMine ? 'with your bottles or tastings' : 'recorded'} for this grape.</li>
					{/each}
				</ul>
			{/if}
		{/snippet}
	</Tabs>
{/key}

<style>
	.palette {
		margin-top: 14px;
	}
	.palette .caption {
		font-size: 12px;
		color: var(--muted);
		margin-bottom: 6px;
	}
	.aside-h {
		font-size: 13px;
		font-weight: 600;
		margin: 0 0 8px;
	}
	.aside-h .muted {
		font-weight: 400;
		font-size: 12px;
	}
	.profile {
		margin-top: 16px;
	}
	.notes {
		margin: 10px 0 0;
		font-size: 13px;
		line-height: 1.5;
	}
	.fold {
		margin-top: 10px;
	}
	.fold summary {
		cursor: pointer;
		color: var(--accent);
		font-size: 13px;
	}
	.classic {
		margin: 6px 0 0;
		padding-left: 18px;
		font-size: 13px;
	}
	.only {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		margin-bottom: 10px;
	}
	.cols {
		list-style: none;
		margin: 0;
		padding: 0;
		columns: 3 260px;
		column-gap: 24px;
	}
	.cols li {
		display: flex;
		align-items: baseline;
		gap: 6px;
		padding: 3px 0;
		break-inside: avoid;
		font-size: 13px;
	}
	.cols a:hover {
		color: var(--accent);
	}
	.region {
		font-size: 11px;
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

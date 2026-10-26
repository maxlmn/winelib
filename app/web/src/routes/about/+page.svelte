<script lang="ts">
	/** About the data: what the reference data holds, where it comes from (and under which licence), how it was
	 * built. The texts are app/api/data/docs/*.md, the same files the README links to. */
	import Markdown from '#lib/components/Markdown.svelte';
	import Stats from '#lib/components/details/Stats.svelte';
	import BarList from '#lib/components/summary/BarList.svelte';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';

	let { data } = $props();
	const a = $derived(data.about);
	const c = $derived(a.counts);

	const TOP = 15;
	const countries = $derived(a.by_country.slice(0, TOP).map((r) => ({ key: r.name, label: r.name, count: r.count, color: FALLBACK_REGION })));
	const rest = $derived(a.by_country.slice(TOP));
	const types = $derived(a.by_type.map((r) => ({ key: r.name, label: r.name, count: r.count, color: 'var(--accent)' })));
	const pct = (n: number, of: number) => (of ? `${Math.round((n / of) * 100)}%` : '0%');
</script>

<svelte:head><title>About the data · WineLib</title></svelte:head>

<div class="page">
	<div class="head">
		<h1>About the data</h1>
		<p class="muted">
			The regions, appellations, grapes and outlines WineLib knows, where they come from, and how they were put together.
			How to use them: <a href={links.help()}>Help</a>.
		</p>
	</div>

	<Stats
		items={[
			{ label: 'Regions', value: c.regions, sub: `in ${c.countries} countries` },
			{ label: 'Appellations', value: c.appellations.toLocaleString(), sub: `${pct(c.appellations_outlined, c.appellations)} with an outline` },
			{ label: 'Vineyards', value: c.vineyards.toLocaleString(), sub: `${pct(c.vineyards_outlined, c.vineyards)} with an outline` },
			{ label: 'Grapes', value: c.grapes, sub: `${c.grapes_parents} with known parents` },
			{ label: 'Grape profiles', value: c.grapes_profile, sub: `${c.grapes_vivc} on VIVC` }
		]}
	/>

	<div class="cols">
		<section class="card">
			<h2>Appellations by country</h2>
			<BarList bars={countries} total={c.appellations} unit="appellations" />
			{#if rest.length}
				<p class="muted small more">And {rest.map((r) => `${r.name} (${r.count})`).join(', ')}.</p>
			{/if}
		</section>
		<section class="card">
			<h2>By kind</h2>
			<p class="muted small">As each register names it; the twelve most common.</p>
			<BarList bars={types} total={c.appellations} unit="appellations" />
			<p class="muted small more">
				Explore them on the <a href={links.map()}>map</a>, or the grapes' family on the <a href={links.grapes()}>grapes page</a>.
			</p>
		</section>
	</div>

	<section class="card md">
		<h2 class="title">Sources and licences</h2>
		<Markdown md={a.sources} />
		{#if a.map_credits.length}
			<h3>Outlines installed here</h3>
			<ul>
				{#each a.map_credits as m (m.source)}
					<li>
						{#if m.url}<a href={m.url} target="_blank" rel="noreferrer">{m.credit ?? m.source}</a>{:else}{m.credit ?? m.source}{/if}
						<span class="muted"> · {m.licence}{m.rows ? ` · ${m.rows.toLocaleString()} outlines` : ''}</span>
					</li>
				{/each}
			</ul>
		{/if}
	</section>

	<section class="card md">
		<Markdown md={a.built} />
	</section>
</div>

<style>
	.page {
		max-width: 1100px;
	}
	.head {
		margin-bottom: 16px;
	}
	.head h1 {
		margin-bottom: 4px;
	}
	.head p {
		margin: 0;
	}
	.head a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.head a:hover {
		color: var(--accent);
	}
	.cols {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
		gap: 16px;
		margin: 16px 0;
	}
	.card {
		padding: 16px 18px;
	}
	.card h2 {
		margin: 0 0 10px;
		font-size: 15px;
	}
	.more {
		margin: 10px 0 0;
		line-height: 1.5;
	}
	.md {
		margin-bottom: 16px;
		font-size: 14px;
	}
	.md h3 {
		font-size: 14px;
		margin: 16px 0 6px;
	}
	.md ul {
		padding-left: 20px;
	}
	.md a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.md a:hover {
		color: var(--accent);
	}
</style>

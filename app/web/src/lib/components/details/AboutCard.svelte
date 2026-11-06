<script lang="ts">
	/** A grape's description and where it's planted, shipped with the app (see app/api/grape_about.py).
	 *  Loaded after the page so it never holds it up; hidden when nothing is known of it. */
	import { links } from '#lib/links.ts';
	interface Section {
		title: string;
		text: string;
	}
	interface About {
		found: boolean;
		name?: string;
		sheet?: { title: string; url: string; sections: Section[]; france: Record<string, number> } | null;
		planted?: {
			world: Record<string, number>;
			rank: number | null;
			countries: [string, number][];
			regions: [string, string, number][];
		} | null;
		credits?: { name: string; licence: string; credit: string; url: string }[];
	}

	let { src }: { src: string } = $props();

	let about = $state<About | null>(null);
	let expanded = $state(false);

	$effect(() => {
		let cancelled = false;
		about = null;
		expanded = false;
		fetch(src)
			.then((r) => (r.ok ? r.json() : null))
			.then((d: About | null) => {
				if (!cancelled) about = d;
			})
			.catch(() => {});
		return () => (cancelled = true);
	});

	// What a wine lover looks for first; the vine's own sections after "More"
	const FIRST = ['Origin', 'Its wines'];
	const sections = $derived(about?.sheet?.sections ?? []);
	const first = $derived(sections.filter((s) => FIRST.includes(s.title)));
	const more = $derived(sections.filter((s) => !FIRST.includes(s.title)));
	const shown = $derived(expanded ? [...first, ...more] : first);

	const ha = (n: number) => `${Math.round(n).toLocaleString('en')} ha`;
	const planted = $derived(about?.planted);
	const latest = $derived(planted?.world['2023']);
	// France's hectares, first and last year of the sheet's
	const france = $derived(Object.entries(about?.sheet?.france ?? {}).sort(([a], [b]) => a.localeCompare(b)));
	const widest = $derived(planted?.countries[0]?.[1] ?? 1);
</script>

{#if about?.found}
	<section class="card about">
		<h2>{about.name}</h2>
		{#each shown as s (s.title)}
			<h3>{s.title}</h3>
			<p>{s.text}</p>
		{/each}
		{#if more.length}
			<button class="link" onclick={() => (expanded = !expanded)}>{expanded ? 'Less' : 'More'}</button>
		{/if}

		{#if planted}
			<h3>Where it's planted</h3>
			{#if latest}
				<p>
					{ha(latest)} in the world in 2023{#if planted.rank}, no. {planted.rank} of the world's grapes{/if}{planted.world['2000']
						? ` (${ha(planted.world['2000'])} in 2000)`
						: ''}.
				</p>
			{/if}
			{#if planted.countries.length}
				<ul class="bars">
					{#each planted.countries as [country, area] (country)}
						<li>
							<span class="name">{country}</span>
							<span class="bar"><span style:width={`${(area / widest) * 100}%`}></span></span>
							<span class="muted area">{ha(area)}</span>
						</li>
					{/each}
				</ul>
			{/if}
			{#if planted.regions.length}
				<p class="muted small">
					Mostly in {planted.regions.map(([region, country]) => `${region} (${country})`).join(', ')}.
				</p>
			{/if}
		{/if}
		{#if france.length > 1}
			<p class="muted small">
				In France: {ha(france[0][1])} in {france[0][0]}, {ha(france[france.length - 1][1])} in {france[france.length - 1][0]}.
			</p>
		{/if}

		<div class="foot muted small">
			{#each about.credits ?? [] as c (c.name)}
				<div><a class="source" href={c.url} target="_blank" rel="noreferrer">{c.credit}</a> ({c.licence})</div>
			{/each}
			<a href={links.about()}>Sources</a>
		</div>
	</section>
{/if}

<style>
	.about {
		padding: 16px 18px;
		margin-bottom: 14px;
	}
	h2 {
		font-size: 15px;
		margin: 0;
	}
	h3 {
		font-size: 12px;
		margin: 12px 0 0;
		color: var(--muted);
		font-weight: 600;
	}
	p {
		margin: 3px 0 0;
		font-size: 13px;
		line-height: 1.55;
	}
	.small {
		font-size: 12px;
	}
	.bars {
		list-style: none;
		margin: 8px 0 0;
		padding: 0;
		display: grid;
		gap: 3px;
		max-width: 480px;
		font-size: 12px;
	}
	.bars li {
		display: grid;
		grid-template-columns: 120px 1fr 76px;
		gap: 8px;
		align-items: center;
	}
	.name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.bar {
		height: 6px;
		border-radius: 3px;
		background: var(--surface-2);
		overflow: hidden;
	}
	.bar span {
		display: block;
		height: 100%;
		background: var(--accent);
	}
	.area {
		text-align: right;
	}
	.foot {
		margin-top: 12px;
		line-height: 1.5;
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		margin-top: 6px;
		color: var(--link);
		text-decoration: var(--link-decoration, none);
		cursor: pointer;
		font-size: 12px;
	}
	.link:hover {
		color: var(--accent);
	}
	.source {
		color: var(--muted);
	}
	.source:hover {
		color: var(--accent);
	}
</style>

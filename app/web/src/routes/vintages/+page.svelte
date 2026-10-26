<script lang="ts">
	import { links } from '#lib/links.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { plural } from '#lib/format.ts';

	let { data } = $props();

	let onlyMine = $state(true);
	const rows = $derived(data.vintages.filter((v) => !onlyMine || v.bottles > 0 || v.tastings > 0));
	// Bars scaled to the busiest vintage, a segment per region (bottles and tastings) in its color
	const peak = $derived(Math.max(1, ...rows.map((v) => v.bottles + v.tastings)));
</script>

<svelte:head><title>Vintages · WineLib</title></svelte:head>

<header class="page-head">
	<h1>Vintages</h1>
	<label class="only">
		<input type="checkbox" bind:checked={onlyMine} />
		Only vintages I have or tasted
	</label>
</header>

<div class="card">
	<ul>
		{#each rows as v (v.vintage)}
			<li>
				<a class="year num" href={links.vintage(v.vintage)}>{v.vintage}</a>
				<span class="bar">
					{#each v.regions as g (g.region)}
						<span
							style:width="{((g.bottles + g.tastings) / peak) * 100}%"
							style:background={regionColor(g.region) ?? FALLBACK_REGION}
							title="{regionLabel(g.region) || 'No region'}: {[g.bottles && `${plural(g.bottles, 'bottle')} in the cellar`, g.tastings && plural(g.tastings, 'tasting')].filter(Boolean).join(', ')}"
						></span>
					{/each}
				</span>
				<span class="muted num counts">
					{#if v.bottles}<span class="gold">{v.bottles} in cellar</span> ·{/if}
					{#if v.tastings}{v.tastings} tasted ·{/if}
					{v.wines} wine{v.wines === 1 ? '' : 's'}
				</span>
			</li>
		{:else}
			<li class="muted">No vintages yet.</li>
		{/each}
	</ul>
</div>

<style>
	.only {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
	}
	.card {
		padding: 8px 16px;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		display: grid;
		grid-template-columns: 56px minmax(80px, 1fr) auto;
		align-items: center;
		gap: 12px;
		padding: 5px 0;
		border-top: 1px solid var(--border);
		font-size: 13px;
	}
	li:first-child {
		border-top: none;
	}
	.year {
		font-weight: 650;
	}
	.year:hover {
		color: var(--accent);
	}
	.bar {
		display: flex;
		height: 8px;
		border-radius: 4px;
		gap: 1px;
		overflow: hidden;
		background: var(--surface-2);
	}
	.gold {
		color: var(--gold);
	}
	.counts {
		font-size: 12px;
		text-align: right;
	}
	/* A phone: the counts under the bar, so the bar keeps the row's width */
	@media (max-width: 600px) {
		li {
			grid-template-columns: 44px minmax(0, 1fr);
			row-gap: 3px;
		}
		.counts {
			grid-column: 2;
			text-align: left;
		}
	}
</style>

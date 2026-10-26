<script lang="ts" generics="T">
	import RegionName from '#lib/components/RegionName.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { Snippet } from 'svelte';
	import MultiSelect from '#lib/components/MultiSelect.svelte';
	import type { Facet, Selection } from './facets.ts';

	interface Props {
		q: string;
		placeholder: string;
		facets: { facet: Facet<T>; options: { value: string; count: number }[] }[];
		selection: Selection;
		/** something besides the facets and search is active (a toggle in `extra`) */
		extraActive?: boolean;
		onsearch: (q: string) => void;
		onselect: (key: string, values: string[]) => void;
		onclear: () => void;
		extra?: Snippet;
	}

	let { q, placeholder, facets, selection, extraActive = false, onsearch, onselect, onclear, extra }: Props = $props();

	const chips = $derived(facets.flatMap(({ facet }) => (selection[facet.key] ?? []).map((value) => ({ facet, value }))));
	const active = $derived(Boolean(q) || chips.length > 0 || extraActive);
</script>

<div class="filters card">
	<input class="search" type="search" {placeholder} value={q} oninput={(e) => onsearch(e.currentTarget.value)} />
	<div class="row">
		{#each facets as { facet, options } (facet.key)}
			<MultiSelect
				label={facet.label}
				{options}
				selected={selection[facet.key] ?? []}
				onchange={(v) => onselect(facet.key, v)}
				swatch={facet.swatch}
				format={facet.key === 'region' ? regionLabel : undefined}
			/>
		{/each}
		{@render extra?.()}
		{#if active}
			<button class="reset" onclick={onclear}>Clear all</button>
		{/if}
	</div>
	{#if chips.length}
		<div class="chips">
			{#each chips as { facet, value } (facet.key + value)}
				<button class="chip" onclick={() => onselect(facet.key, selection[facet.key].filter((v) => v !== value))}>
					<span class="muted">{facet.label}:</span> {#if facet.key === 'region'}<RegionName name={value} />{:else}{value}{/if} ✕
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.filters {
		padding: 12px;
		margin-bottom: 14px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		position: relative;
		z-index: 10;
	}
	.search {
		width: 100%;
		padding: 9px 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
		outline: none;
	}
	.search:focus {
		border-color: var(--accent);
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		align-items: center;
	}
	.reset {
		border: none;
		background: none;
		color: var(--accent);
		cursor: pointer;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.chip {
		border: none;
		border-radius: 12px;
		padding: 2px 10px;
		background: var(--accent-soft);
		color: var(--accent);
		font-size: 12px;
		cursor: pointer;
	}
	.chip .muted {
		color: inherit;
		opacity: 0.7;
	}
</style>

<script lang="ts">
	/** Which of your wines a list takes: tags, colour, region, grape, vintages, in the cellar or tasted, your rating,
	 * words in the name; how many match, and the first of them, as you go. */
	import { onMount } from 'svelte';
	import TagPicker from '#lib/components/TagPicker.svelte';
	import { suggestions } from '#lib/api/tags.ts';
	import { previewCriteria, type Criteria, type CriteriaPreview } from '#lib/api/lists.ts';
	import { typeColor } from '#lib/colors.ts';

	let { criteria = $bindable() }: { criteria: Criteria } = $props();

	const COLORS = ['Red', 'White', 'Rose', 'Bubbles', 'Bubbles Rose', 'Sweet', 'Orange', 'Fortified'];
	let tagWords = $state<string[]>([]);
	let regions = $state<string[]>([]);
	onMount(async () => {
		tagWords = await suggestions();
		const o = await fetch('/api/lookups/options').then((r) => r.json()).catch(() => ({ regions: [] }));
		regions = (o.regions ?? []).map((r: { name: string }) => r.name);
	});

	const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
	let grapesText = $state(criteria.grapes.join(', '));
	$effect(() => {
		criteria.grapes = grapesText.split(',').map((g) => g.trim()).filter(Boolean);
	});

	// What they match, asked a moment after the last change
	let preview = $state<CriteriaPreview | null>(null);
	let timer: ReturnType<typeof setTimeout>;
	$effect(() => {
		const c = $state.snapshot(criteria);
		clearTimeout(timer);
		timer = setTimeout(async () => {
			preview = await previewCriteria(c).catch(() => null);
		}, 300);
		return () => clearTimeout(timer);
	});
</script>

<div class="criteria">
	<div class="row">
		<span class="label">Style</span>
		<div class="field">
			<TagPicker bind:value={criteria.tags} suggestions={tagWords} />
			{#if criteria.tags.length > 1}
				<label class="small"><input type="checkbox" bind:checked={criteria.tags_all} /> every one of them (else any)</label>
			{/if}
		</div>
	</div>
	<div class="row">
		<span class="label">Colour</span>
		<div class="field chips">
			{#each COLORS as c (c)}
				<button type="button" class="chip" class:on={criteria.colors.includes(c)} onclick={() => (criteria.colors = toggle(criteria.colors, c))}>
					<span class="dot" style:background={typeColor(c)}></span>{c}
				</button>
			{/each}
		</div>
	</div>
	<div class="row">
		<span class="label">Region</span>
		<div class="field chips">
			{#each criteria.regions as r (r)}
				<button type="button" class="chip on" onclick={() => (criteria.regions = toggle(criteria.regions, r))}>{r} ✕</button>
			{/each}
			<select aria-label="Add a region" onchange={(e) => { const v = e.currentTarget.value; if (v) criteria.regions = toggle(criteria.regions, v); e.currentTarget.value = ''; }}>
				<option value="">+ a region</option>
				{#each regions.filter((r) => !criteria.regions.includes(r)) as r (r)}<option value={r}>{r}</option>{/each}
			</select>
		</div>
	</div>
	<div class="row">
		<span class="label">Grape</span>
		<div class="field"><input bind:value={grapesText} placeholder="Chenin Blanc, Syrah… (any of them)" /></div>
	</div>
	<div class="row">
		<span class="label">Vintages</span>
		<div class="field inline">
			<input type="number" min="1900" max="2100" placeholder="from" value={criteria.vintage_from ?? ''}
				oninput={(e) => (criteria.vintage_from = e.currentTarget.value ? +e.currentTarget.value : null)} />
			<span class="muted">to</span>
			<input type="number" min="1900" max="2100" placeholder="to" value={criteria.vintage_to ?? ''}
				oninput={(e) => (criteria.vintage_to = e.currentTarget.value ? +e.currentTarget.value : null)} />
		</div>
	</div>
	<div class="row">
		<span class="label">Your wines</span>
		<div class="field inline">
			<div class="seg" role="group" aria-label="Which wines">
				<button type="button" class:on={criteria.where === 'any'} onclick={() => (criteria.where = 'any')}>Owned or tasted</button>
				<button type="button" class:on={criteria.where === 'cellar'} onclick={() => (criteria.where = 'cellar')}>In the cellar</button>
				<button type="button" class:on={criteria.where === 'tasted'} onclick={() => (criteria.where = 'tasted')}>Tasted</button>
			</div>
			<label class="small">rated at least
				<input type="number" min="50" max="100" placeholder="any" value={criteria.min_rating ?? ''}
					oninput={(e) => (criteria.min_rating = e.currentTarget.value ? +e.currentTarget.value : null)} />
			</label>
		</div>
	</div>
	<div class="row">
		<span class="label">Words</span>
		<div class="field"><input bind:value={criteria.text} placeholder="in the producer, cuvée or appellation" /></div>
	</div>
	<p class="found">
		{#if preview}
			<b class="num">{preview.count}</b> {preview.count === 1 ? 'wine matches' : 'wines match'}{#if preview.count}:
				<span class="muted">{preview.wines.slice(0, 6).map((w) => w.label).join(' · ')}{preview.count > 6 ? ' …' : ''}</span>{/if}
		{:else}
			<span class="muted">Looking…</span>
		{/if}
	</p>
</div>

<style>
	.criteria {
		display: flex;
		flex-direction: column;
		gap: 10px;
		font-size: 13px;
	}
	.row {
		display: flex;
		gap: 12px;
		align-items: baseline;
	}
	.label {
		flex: none;
		width: 84px;
		color: var(--muted);
		font-size: 12px;
	}
	.field {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.field.chips,
	.field.inline {
		flex-direction: row;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 10px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 3px 10px;
		border: 1px solid var(--border);
		border-radius: 12px;
		background: var(--surface);
		color: var(--muted);
		font: inherit;
		font-size: 12px;
		cursor: pointer;
	}
	.chip.on {
		border-color: var(--accent);
		background: var(--accent-soft);
		color: var(--accent);
	}
	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}
	input:not([type='checkbox']),
	select {
		padding: 5px 9px;
		border: 1px solid var(--border);
		border-radius: 7px;
		background: var(--surface-2);
		font: inherit;
		font-size: 13px;
		color: inherit;
	}
	input[type='number'] {
		width: 84px;
	}
	.seg {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.seg button {
		border: none;
		background: none;
		padding: 5px 10px;
		font: inherit;
		font-size: 12px;
		color: var(--muted);
		cursor: pointer;
	}
	.seg button.on {
		background: var(--accent);
		color: #fff;
	}
	.small {
		font-size: 12px;
		color: var(--muted);
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.found {
		margin: 4px 0 0;
		padding: 8px 10px;
		border-radius: 8px;
		background: var(--surface-2);
	}
</style>

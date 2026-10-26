<script lang="ts">
	import Combobox from './Combobox.svelte';
	import Field from './Field.svelte';
	import WineCard from './WineCard.svelte';
	import WineFields from './WineFields.svelte';
	import RegionName from '#lib/components/RegionName.svelte';
	import { TYPE_COLORS } from '#lib/colors.ts';
	import { emptyWine, getJson, lookup, newVintageDraft, vintageLabel } from '#lib/api/forms.ts';
	import type { Options, WineDraft, WineForm, WineSummary } from '#lib/api/forms.ts';

	interface Props {
		/** the picked wine, or */
		wine: WineSummary | null;
		/** a new wine to create on save */
		draft: WineDraft | null;
		options: Options;
		prefix: string;
		errors?: Record<string, string>;
	}

	/**
	 * The smart wine selector: type-ahead over every wine by producer,
	 * cuvée, appellation and vintage; or a new vintage of a wine; or a whole new wine (and producer...).
	 */
	let { wine = $bindable(), draft = $bindable(), options, prefix, errors = {} }: Props = $props();

	type Option = WineSummary & { name: string };
	let last: Option[] = [];

	async function search(q: string): Promise<Option[]> {
		const rows = await lookup<WineSummary>('wines', { q });
		last = rows.map((w) => ({ ...w, name: [w.producer, w.cuvee, w.vintage].filter(Boolean).join(' ') }));
		return last;
	}

	function newWine() {
		// Searching one producer's wines? Start the new wine there.
		const producers = new Map(last.map((w) => [w.producer_id, w]));
		const only = producers.size === 1 ? [...producers.values()][0] : null;
		draft = emptyWine(only && { id: only.producer_id, name: only.producer });
		wine = null;
	}

	async function newVintage(w: WineSummary) {
		draft = newVintageDraft(await getJson<WineForm>(fetch, `/api/forms/wines/${w.id}`));
		wine = null;
	}

	const stock = (w: WineSummary) => (w.stock ? `${w.stock} in cellar` : '');
</script>

{#snippet row(w: Option)}
	<span class="dot" style:background={TYPE_COLORS[w.type ?? ''] ?? 'var(--muted)'}></span>
	<span class="opt">
		<span><b>{w.producer}</b> {w.cuvee} <span class="num">{vintageLabel(w)}</span></span>
		<span class="muted small">{[w.appellation, w.varietal].filter(Boolean).join(', ')}{#if w.region}{w.appellation || w.varietal ? ' · ' : ''}<RegionName name={w.region} />{/if}</span>
	</span>
	{#if w.stock}<span class="stock small">{stock(w)}</span>{/if}
{/snippet}

{#if wine}
	<WineCard {wine} extra={stock(wine)}>
		{#snippet actions()}
			<button type="button" class="btn small-btn" onclick={() => wine && newVintage(wine)} title="Same wine, another vintage">＋ New vintage</button>
			<button type="button" class="btn small-btn" onclick={() => (wine = null)}>Change</button>
		{/snippet}
	</WineCard>
{:else if draft}
	<div class="new">
		<div class="new-head">
			<b>New wine</b>
			<button type="button" class="link" onclick={() => (draft = null)}>← Pick an existing wine instead</button>
		</div>
		<WineFields bind:value={draft} {options} prefix="{prefix}-new" {errors} compact />
	</div>
{:else}
	<Field label="Wine" for="{prefix}-wine" required error={errors.wine} hint="Producer, cuvée, appellation, vintage, e.g. “coulaine chinon 2020”">
		<Combobox
			id="{prefix}-wine"
			value={null}
			{search}
			{row}
			required
			invalid={!!errors.wine}
			placeholder="Search wines…"
			action={{ label: '＋ New wine…', run: newWine }}
			onchange={(_, item) => item && (wine = item)}
		/>
	</Field>
{/if}

<style>
	.opt {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}
	.small {
		font-size: 12px;
	}
	.stock {
		color: var(--accent);
		white-space: nowrap;
	}
	.small-btn {
		padding: 4px 10px;
		font-size: 13px;
	}
	.new {
		padding: 14px;
		border: 1px dashed var(--accent);
		border-radius: 10px;
	}
	.new-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 12px;
		flex-wrap: wrap;
		margin-bottom: 12px;
	}
</style>

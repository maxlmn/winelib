<script lang="ts">
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { untrack } from 'svelte';
	import Combobox from './Combobox.svelte';
	import Field from './Field.svelte';
	import LinkFill from './LinkFill.svelte';
	import TypePicker from './TypePicker.svelte';
	import { emptyGrape, lookup, num } from '#lib/api/forms.ts';
	import type { Choice, Options, ProducerOption, WineDraft } from '#lib/api/forms.ts';

	interface Props {
		value: WineDraft;
		options: Options;
		prefix: string;
		errors?: Record<string, string>;
		/** fold the less used fields away (inline creation inside another form) */
		compact?: boolean;
		/** a new wine: offer Fill from a link above the fields */
		fromLink?: boolean;
	}

	/** The wine's own fields; producer, appellation, varietal and region can be new. */
	let { value = $bindable(), options, prefix, errors = {}, compact = false, fromLink = false }: Props = $props();

	// A new vintage carries the blend, LWIN and drinking window over: show them
	const hasMore = untrack(() => !!(value.blend || value.lwin || value.drink_window_start || value.drink_window_end));

	type Row = { id: number; name: string; region?: string | null; region_id?: number | null; alias?: string | null };

	// The wine's region follows the producer's, then the appellation's, until it's picked by hand
	let regionTouched = $state(!!value.region);
	const regionId = $derived(value.region?.id ?? undefined);
	const regionHint = (r: Row) => regionLabel(r.region);

	function setProducer(c: Choice | null, item?: ProducerOption) {
		value.producer = c;
		value.producerRegion = null;
		if (!regionTouched && item?.region_id) setRegion({ id: item.region_id, name: item.region ?? '' }, false);
	}

	function setAppellation(c: Choice | null, item?: Row) {
		value.appellation = c;
		if (!regionTouched && item?.region_id) setRegion({ id: item.region_id, name: item.region ?? '' }, false);
	}

	function setProducerRegion(c: Choice | null) {
		value.producerRegion = c;
		if (!regionTouched && c) setRegion(c, false);
	}

	// LWIN candidates from the Liv-ex list (GET /api/lookups/lwin), from the producer, cuvée and appellation
	type LwinHit = { lwin: string; name: string; colour: string | null; match: string };
	let lwinHits = $state<LwinHit[] | null>(null);
	let lwinNote = $state('');
	let lwinBusy = $state(false);
	async function suggestLwin() {
		if (!value.producer?.name || lwinBusy) return;
		lwinBusy = true;
		lwinNote = '';
		try {
			const q = new URLSearchParams({ producer: value.producer.name, cuvee: value.cuvee ?? '', appellation: value.appellation?.name ?? '' });
			const body = await fetch(`/api/lookups/lwin?${q}`).then((r) => r.json());
			lwinHits = body.suggestions;
			if (!body.available) lwinNote = 'No LWIN list installed: see Settings › Integrations.';
			else if (!body.suggestions.length) lwinNote = `No match in the Liv-ex list for ${value.producer.name}.`;
		} catch {
			lwinNote = 'The app couldn’t be reached';
		} finally {
			lwinBusy = false;
		}
	}

	function setRegion(c: Choice | null, byHand = true) {
		if (c?.id !== value.region?.id || c?.name !== value.region?.name) value.vineyard = null; // vineyards are per region
		value.region = c;
		regionTouched ||= byHand;
	}

	// The grapes: the first the main one
	function moveGrape(i: number, by: number) {
		const list = [...value.grapes];
		const [g] = list.splice(i, 1);
		list.splice(Math.max(0, i + by), 0, g);
		value.grapes = list;
	}
	function removeGrape(i: number) {
		const list = value.grapes.filter((_, j) => j !== i);
		value.grapes = list.length ? list : [emptyGrape()];
	}
</script>

<div class="grid">
	{#if fromLink}<LinkFill bind:value {prefix} />{/if}
	<Field label="Producer" for="{prefix}-producer" required error={errors.producer}>
		<Combobox
			id="{prefix}-producer"
			value={value.producer}
			search={(q) => lookup<ProducerOption>('producers', { q })}
			hint={regionHint}
			hintDot={(r) => regionColor(r.region)}
			creatable="producer"
			required
			invalid={!!errors.producer}
			placeholder="Search producers…"
			onchange={setProducer}
		/>
	</Field>
	{#if value.producer?.id === null}
		<Field label="New producer’s region" for="{prefix}-producer-region">
			<Combobox
				id="{prefix}-producer-region"
				value={value.producerRegion}
				options={options.regions}
				hint={(r) => r.country}
				hintDot={(r) => regionColor(r.name)}
				creatable="region"
				placeholder="Region…"
				onchange={setProducerRegion}
			/>
		</Field>
	{:else}
		<span class="spacer"></span>
	{/if}

	<Field label="Cuvée / name" for="{prefix}-cuvee">
		<input id="{prefix}-cuvee" bind:value={value.cuvee} placeholder="e.g. Les Pucelles" />
	</Field>
	<Field label="Vintage" for="{prefix}-vintage" error={errors.vintage}>
		<input id="{prefix}-vintage" bind:value={value.vintage} placeholder="2020 or NV" inputmode="text" />
	</Field>

	<Field label="Type" span>
		<TypePicker name="{prefix}-type" types={options.wine_types} value={value.type} onchange={(t) => (value.type = t)} />
	</Field>
	<!-- Sparkling and NV wines, or any wine that already has one, so a stored value is never hidden -->
	{#if value.type?.startsWith('Bubbles') || /^nv\b/i.test(value.vintage ?? '') || value.disgorgement_date}
		<Field label="Disgorgement date" for="{prefix}-disgorge" hint="e.g. Oct 2024">
			<input id="{prefix}-disgorge" bind:value={value.disgorgement_date} />
		</Field>
		<span class="spacer"></span>
	{/if}

	<Field label="Region" for="{prefix}-region" error={errors.region}>
		<Combobox
			id="{prefix}-region"
			value={value.region}
			options={options.regions}
			hint={(r) => r.country}
			hintDot={(r) => regionColor(r.name)}
			creatable="region"
			placeholder="Region…"
			onchange={(c) => setRegion(c)}
		/>
	</Field>
	<Field label="Appellation" for="{prefix}-appellation" hint={value.appellation?.id === null ? 'Created in the wine’s region' : undefined}>
		<Combobox
			id="{prefix}-appellation"
			value={value.appellation}
			search={(q) => lookup<Row>('appellations', { q, region_id: regionId })}
			hint={regionHint}
			hintDot={(r) => regionColor(r.region)}
			creatable="appellation"
			placeholder="Search appellations…"
			onchange={setAppellation}
		/>
	</Field>
	<Field label="Grapes" for="{prefix}-grape-0" hint="In order, the main grape first; % when known" span>
		<div class="grapes">
			{#each value.grapes as g, i (i)}
				<div class="grape">
					<Combobox
						id="{prefix}-grape-{i}"
						value={g.varietal}
						search={(q) => lookup<Row>('varietals', { q, limit: 200 })}
						hint={(r) => r.alias}
						creatable="varietal"
						placeholder={i ? 'Another grape…' : 'Main grape…'}
						onchange={(c) => (value.grapes[i].varietal = c)}
					/>
					<input class="share" type="number" min="1" max="100" step="any" placeholder="%" aria-label="Share in percent"
						bind:value={g.share} />
					<button type="button" class="icon" title="Move up" aria-label="Move up" disabled={i === 0} onclick={() => moveGrape(i, -1)}>↑</button>
					<button type="button" class="icon" title="Remove" aria-label="Remove" disabled={value.grapes.length === 1 && !g.varietal}
						onclick={() => removeGrape(i)}>✕</button>
				</div>
			{/each}
			<button type="button" class="add" onclick={() => (value.grapes = [...value.grapes, emptyGrape()])}>＋ Add a grape</button>
		</div>
	</Field>
	<Field label="Vineyard" for="{prefix}-vineyard" hint={value.region ? `In ${regionLabel(value.region.name)}` : 'Optional'}>
		<Combobox
			id="{prefix}-vineyard"
			value={value.vineyard}
			search={(q) => lookup<Row>('vineyards', { q, region_id: regionId })}
			placeholder="Sub-region, village or vineyard…"
			onchange={(c) => (value.vineyard = c)}
		/>
	</Field>
</div>

{#if compact}
	<details open={hasMore} class="more">
		<summary>Blend, LWIN, drinking window</summary>
		{@render more()}
	</details>
{:else}
	<div class="gap">{@render more()}</div>
{/if}

{#snippet more()}
<div class="grid">
	<Field label="Blend" for="{prefix}-blend" hint="Its style; field blend: co-planted, co-fermented">
		<select id="{prefix}-blend" bind:value={value.blend}>
			<option value="">—</option>
			{#each options.blend_styles ?? [] as style (style)}<option value={style}>{style}</option>{/each}
			{#if value.blend && !(options.blend_styles ?? []).includes(value.blend)}<option value={value.blend}>{value.blend}</option>{/if}
		</select>
	</Field>
	<Field label="LWIN" for="{prefix}-lwin" hint="Needed for market prices">
		<div class="lwin">
			<input id="{prefix}-lwin" bind:value={value.lwin} inputmode="numeric" />
			<button type="button" class="btn" disabled={!value.producer?.name || lwinBusy} onclick={suggestLwin}>
				{lwinBusy ? '…' : 'Suggest'}
			</button>
		</div>
		{#if lwinHits?.length}
			<ul class="lwin-hits">
				{#each lwinHits as h (h.lwin)}
					<li>
						<button type="button" onclick={() => ((value.lwin = h.lwin), (lwinHits = null))}>
							<b class="num">{h.lwin}</b> {h.name}{h.colour ? ` · ${h.colour}` : ''}
							<span class="muted">{h.match === 'EXACT' ? 'exact' : h.match.toLowerCase()}</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
		{#if lwinNote}<p class="lwin-note muted">{lwinNote}</p>{/if}
	</Field>


	<Field label="Drink from" for="{prefix}-ds" error={errors.drink_window_start}>
		<input
			id="{prefix}-ds"
			type="number"
			min="1900"
			max="2200"
			placeholder="Year"
			value={value.drink_window_start ?? ''}
			oninput={(e) => (value.drink_window_start = num(e.currentTarget.value))}
		/>
	</Field>
	<Field label="Drink until" for="{prefix}-de" error={errors.drink_window_end}>
		<input
			id="{prefix}-de"
			type="number"
			min="1900"
			max="2200"
			placeholder="Year"
			value={value.drink_window_end ?? ''}
			oninput={(e) => (value.drink_window_end = num(e.currentTarget.value))}
		/>
	</Field>
</div>
{/snippet}

<style>
	.grapes {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.grape {
		display: grid;
		grid-template-columns: 1fr 72px auto auto;
		gap: 6px;
		align-items: center;
	}
	.grape .share {
		width: 100%;
	}
	.grape .icon {
		border: 1px solid var(--border);
		background: var(--surface);
		border-radius: 6px;
		padding: 4px 8px;
		cursor: pointer;
	}
	.grape .icon:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.add {
		align-self: flex-start;
		border: none;
		background: none;
		color: var(--accent);
		cursor: pointer;
		padding: 2px 0;
		font-size: 13px;
	}
	.gap {
		margin-top: 14px;
	}
	.more {
		margin-top: 14px;
	}
	.more summary {
		cursor: pointer;
		color: var(--accent);
		margin-bottom: 12px;
		width: fit-content;
	}
	@media (max-width: 640px) {
		.spacer {
			display: none;
		}
	}
	.lwin {
		display: flex;
		gap: 8px;
	}
	.lwin input {
		flex: 1;
		min-width: 0;
	}
	.lwin-hits {
		list-style: none;
		margin: 6px 0 0;
		padding: 0;
		border: 1px solid var(--border);
		border-radius: 8px;
	}
	.lwin-hits button {
		display: block;
		width: 100%;
		padding: 6px 10px;
		border: none;
		border-bottom: 1px solid var(--border);
		background: none;
		text-align: left;
		font-size: 13px;
		cursor: pointer;
	}
	.lwin-hits button:hover {
		background: var(--surface-2);
	}
	.lwin-note {
		margin: 6px 0 0;
		font-size: 12px;
	}
</style>

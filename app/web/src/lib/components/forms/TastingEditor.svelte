<script lang="ts" module>
	import type { BottleOption, PlaceOption, WineSummary } from '#lib/api/forms.ts';

	/** What a new note starts from (?bottle_id, ?wine_id, ?place_id, ?date). */
	export interface TastingPrefill {
		bottle: BottleOption | null;
		wine: WineSummary | null;
		place: PlaceOption | null;
		date: string | null;
	}
</script>

<script lang="ts">
	import { untrack } from 'svelte';
	import BottleFields from './BottleFields.svelte';
	import Combobox from './Combobox.svelte';
	import Field from './Field.svelte';
	import PhotoField from './PhotoField.svelte';
	import { applyPhotoChange } from '#lib/api/photos.ts';
	import FormPage from './FormPage.svelte';
	import PlacePicker from './PlacePicker.svelte';
	import Section from './Section.svelte';
	import WineCard from './WineCard.svelte';
	import WinePicker from './WinePicker.svelte';
	import {
		blank, bottleDraft, check, lookup, num, placeChoice, remove, save, scoped, toBottleDetails, toPlaceRef, toWineIn, today, wineErrors
	} from '#lib/api/forms.ts';
	import type { Choice, Options, PlaceChoice, TastingForm, WineDraft } from '#lib/api/forms.ts';
	import { links } from '#lib/links.ts';

	let { options, tasting, prefill }: { options: Options; tasting: TastingForm | null; prefill: TastingPrefill } = $props();

	// The form edits a copy; the route re-creates the editor for another note ({#key})
	const t = untrack(() => tasting);
	const pre = untrack(() => prefill);

	type BottleRow = BottleOption & { name: string };
	const asChoice = (b: BottleOption): Choice => ({ id: b.id, name: b.label, hint: `${b.qty} left` });

	// "Other wine" by default, or the cellar when drinking one of its bottles
	let source = $state<'cellar' | 'other'>(pre.bottle ? 'cellar' : 'other');
	let bottle = $state<Choice | null>(pre.bottle ? asChoice(pre.bottle) : null);
	let consume = $state(true);
	let wine = $state<WineSummary | null>(pre.wine ?? pre.bottle?.wine ?? null);
	let draft = $state<WineDraft | null>(null);
	let details = $state(bottleDraft(t?.bottle, untrack(() => options.ad_hoc)));

	let date = $state(t ? blank(t.date) : (pre.date ?? today()));
	let place = $state<PlaceChoice | null>(placeChoice(t?.place ?? pre.place));
	// Your score (100-point): a slider, empty until you move it
	let rating = $state<number | null>(t?.rating ?? null);
	let glasses = $state<number | null>(t ? t.glasses : 1);
	let sequence = $state<number | null>(t ? t.sequence : 1);
	let photo = $state({ file: null as File | null, remove: false });
	// New notes take the next slot in that evening's line-up, until the order is typed by hand
	let sequenceTouched = false;
	let evening = $state<{ next: number; count: number } | null>(null);
	$effect(() => {
		if (t) return;
		const placeId = place?.id;
		if (!date || !placeId) {
			evening = null;
			if (!sequenceTouched) sequence = 1;
			return;
		}
		const ctrl = new AbortController();
		fetch(`/api/lookups/next-sequence?date=${date}&place_id=${placeId}`, { signal: ctrl.signal })
			.then((r) => (r.ok ? r.json() : null))
			.then((d) => {
				evening = d;
				if (d && !sequenceTouched) sequence = d.next;
			})
			.catch(() => {});
		return () => ctrl.abort();
	});
	const ordinal = (n: number) => `${n}${n % 10 === 1 && n !== 11 ? 'st' : n % 10 === 2 && n !== 12 ? 'nd' : n % 10 === 3 && n !== 13 ? 'rd' : 'th'}`;
	const sequenceHint = $derived(
		evening?.count
			? `${ordinal(evening.next)} wine that evening · ${evening.count} already logged there`
			: 'Order in the day’s line-up'
	);
	let tags = $state(blank(t?.tags));
	let notes = $state(blank(t?.notes));
	let errors = $state<Record<string, string>>({});
	// Purchase details are secondary when logging a tasting: folded, unless one of them has a problem
	let detailsOpen = $state(false);
	const bottleErrors = $derived(scoped(errors, 'bottle'));
	$effect(() => {
		if (Object.keys(bottleErrors).length) detailsOpen = true;
	});
	const detailsSummary = $derived(
		[details.bottle_size, details.price ? `${details.price} ${details.currency}` : null, details.provenance, details.vendor]
			.filter(Boolean)
			.join(' · ')
	);

	const searchBottles = async (q: string): Promise<BottleRow[]> =>
		(await lookup<BottleOption>('bottles', { q })).map((b) => ({ ...b, name: b.label }));

	async function onsave() {
		check({
			...(!date ? { date: 'Pick the date' } : {}),
			...(!t && source === 'cellar' && !bottle ? { bottle_id: 'Pick the bottle from the cellar' } : {}),
			...(!t && source === 'other' && !wine && !draft ? { wine: 'Pick the wine, or create a new one' } : {}),
			...(!t && source === 'other' && draft ? wineErrors(draft, 'wine.') : {})
		});
		const note = { date, place: toPlaceRef(place), rating, glasses, sequence, tags, notes };
		if (t) {
			await save('tastings', t.id, { ...note, bottle: toBottleDetails(details) });
			await applyPhotoChange(place?.name, date, photo);
			return links.tasting(t.id);
		}
		const body =
			source === 'cellar'
				? { ...note, source, bottle_id: bottle?.id, consume }
				: { ...note, source, wine: wine?.id ?? toWineIn(draft!), bottle: toBottleDetails(details) };
		const { id } = await save('tastings', null, body);
		await applyPhotoChange(place?.name, date, photo);
		return links.tasting(id);
	}
</script>

{#snippet bottleRow(b: BottleRow)}
	<span class="name">{b.label}</span>
	<span class="muted small">{b.qty} left</span>
{/snippet}

<FormPage
	title={t ? 'Edit tasting note' : 'Add tasting note'}
	saveLabel="Save note"
	fallback={t ? links.tasting(t.id) : links.tastings()}
	{onsave}
	bind:fieldErrors={errors}
	remove={t
		? {
				what: 'this tasting note',
				message: 'The note is deleted. A bottle created just for it goes too; a cellar bottle keeps its quantity.',
				run: async () => (await remove('tastings', t.id), links.tastings())
			}
		: undefined}
>
	<Section title="Wine">
		{#snippet aside()}
			{#if !t}
				<div class="seg" role="radiogroup" aria-label="Source">
					<label class:on={source === 'cellar'}><input type="radio" name="source" value="cellar" bind:group={source} />From the cellar</label>
					<label class:on={source === 'other'}><input type="radio" name="source" value="other" bind:group={source} />Other wine</label>
				</div>
			{/if}
		{/snippet}

		{#if t}
			<WineCard wine={t.wine} extra={t.source === 'other' ? 'Not from the cellar' : 'Cellar bottle'} />
		{:else if source === 'cellar'}
			<div class="grid">
				<Field label="Bottle" for="t-bottle" required error={errors.bottle_id} span hint="Bottles in stock: producer, cuvée, appellation, vintage or bin">
					<Combobox
						id="t-bottle"
						value={bottle}
						search={searchBottles}
						row={bottleRow}
						required
						invalid={!!errors.bottle_id}
						placeholder="Search the cellar…"
						onchange={(c, item) => (bottle = item ? asChoice(item) : c)}
					/>
				</Field>
				<label class="check span">
					<input type="checkbox" bind:checked={consume} />
					Take the bottle out of the cellar (quantity − 1)
				</label>
			</div>
		{:else}
			<WinePicker bind:wine bind:draft {options} prefix="t" errors={{ ...scoped(errors, 'wine'), wine: errors.wine }} />
		{/if}
	</Section>

	<Section title="Tasting">
		<div class="grid">
			<Field label="Date drank" for="t-date" required error={errors.date}>
				<input id="t-date" type="date" bind:value={date} aria-invalid={!!errors.date} />
			</Field>
			<div class="span place">
				<PlacePicker bind:value={place} placeTypes={options.place_types} id="t-place" error={errors.place ?? errors['place.name']} />
			</div>
			<Field label="Notes" for="t-notes" span>
				<textarea id="t-notes" rows="5" bind:value={notes} placeholder="Explosive nose of…"></textarea>
			</Field>
			<Field label="Your score" for="t-rating" span hint="Leave it empty for no score">
				<div class="score">
					<input id="t-rating" type="range" min="70" max="100" step="1" value={rating ?? 90}
						class:unset={rating === null} oninput={(e) => (rating = +e.currentTarget.value)} />
					<span class="score-value num">{rating ?? '–'}</span>
					{#if rating !== null}<button type="button" class="link" onclick={() => (rating = null)}>Clear</button>{/if}
				</div>
			</Field>
			<Field label="Glasses" for="t-glasses" error={errors.glasses}>
				<input id="t-glasses" type="number" min="0" step="0.5" value={glasses ?? ''} oninput={(e) => (glasses = num(e.currentTarget.value))} />
			</Field>
			<Field label="Sequence" for="t-seq" hint={sequenceHint} error={errors.sequence}>
				<input
					id="t-seq"
					type="number"
					min="0"
					step="1"
					value={sequence ?? ''}
					oninput={(e) => ((sequenceTouched = true), (sequence = num(e.currentTarget.value)))}
				/>
			</Field>
			<Field label="Tags" for="t-tags" span hint="Comma separated, e.g. Dinner, Gift, corked">
				<input id="t-tags" bind:value={tags} />
			</Field>
			<div class="span">
				<PhotoField place={place?.name} {date} bind:file={photo.file} bind:remove={photo.remove} />
			</div>
		</div>
	</Section>

	{#if t || source === 'other'}
		<Section title="Bottle details" collapsible bind:open={detailsOpen} summary={detailsSummary || 'Size, price, vendor, provenance'}>
			<BottleFields bind:value={details} {options} prefix="t-b" errors={bottleErrors} />
		</Section>
	{/if}
</FormPage>

<style>
	.seg {
		display: inline-flex;
		padding: 2px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
	}
	.seg label {
		padding: 4px 12px;
		border-radius: 6px;
		cursor: pointer;
		color: var(--muted);
		font-size: 13px;
	}
	.seg label.on {
		background: var(--surface);
		color: var(--text);
		font-weight: 600;
		box-shadow: var(--shadow);
	}
	.seg label:focus-within {
		outline: 2px solid var(--accent);
	}
	.seg input {
		position: absolute;
		opacity: 0;
		pointer-events: none;
	}
	.check {
		display: flex;
		align-items: center;
		gap: 8px;
		cursor: pointer;
	}
	.place {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.name {
		flex: 1;
		min-width: 0;
	}
	.small {
		font-size: 12px;
		white-space: nowrap;
	}
	.score {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.score input[type='range'] {
		flex: 1;
		accent-color: var(--accent);
	}
	.score input.unset {
		opacity: 0.45;
	}
	.score-value {
		min-width: 2.5em;
		font-size: 18px;
		font-weight: 700;
		color: var(--accent);
		text-align: right;
	}
</style>

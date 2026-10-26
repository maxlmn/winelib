<script lang="ts">
	import { untrack } from 'svelte';
	import Field from './Field.svelte';
	import PhotoField from './PhotoField.svelte';
	import { applyPhotoChange } from '#lib/api/photos.ts';
	import FormPage from './FormPage.svelte';
	import PlacePicker from './PlacePicker.svelte';
	import Section from './Section.svelte';
	import { blank, check, placeChoice, remove, save, toPlaceRef, today } from '#lib/api/forms.ts';
	import type { Options, PlaceChoice, PlaceOption, VisitForm } from '#lib/api/forms.ts';
	import { links } from '#lib/links.ts';

	let { options, visit, place: initialPlace }: { options: Options; visit: VisitForm | null; place: PlaceOption | null } = $props();

	// The form edits a copy; the route re-creates the editor for another visit ({#key})
	const v = untrack(() => visit);
	let place = $state<PlaceChoice | null>(placeChoice(untrack(() => v?.place ?? initialPlace)));
	let date = $state(v ? blank(v.date) : today());
	let notes = $state(blank(v?.notes));
	let photo = $state({ file: null as File | null, remove: false });
	let errors = $state<Record<string, string>>({});

	async function onsave() {
		check({ ...(!place ? { place: 'Pick the place, or type a new name' } : {}), ...(!date ? { date: 'Pick the date' } : {}) });
		const res = await save<{ id: number; place_id: number }>('visits', v?.id ?? null, { date, place: toPlaceRef(place), notes });
		await applyPhotoChange(place?.name, date, photo);
		return links.place(res.place_id);
	}
</script>

<FormPage
	title={v ? 'Edit restaurant visit' : 'Add restaurant visit'}
	saveLabel="Save visit"
	fallback={v?.place ? links.place(v.place.id) : links.places()}
	{onsave}
	bind:fieldErrors={errors}
	remove={v
		? {
				what: 'this visit',
				message: 'This can’t be undone.',
				run: async () => {
					const { place_id } = await remove<{ place_id: number | null }>('visits', v.id);
					return place_id ? links.place(place_id) : links.places();
				}
			}
		: undefined}
>
	<Section title="Visit">
		<div class="stack">
			<PlacePicker bind:value={place} placeTypes={options.place_types} id="v-place" required error={errors.place ?? errors['place.name']} />
			<div class="grid">
				<Field label="Date" for="v-date" required error={errors.date}>
					<input id="v-date" type="date" bind:value={date} aria-invalid={!!errors.date} />
				</Field>
			</div>
			<Field label="Notes" for="v-notes">
				<textarea id="v-notes" rows="5" bind:value={notes}></textarea>
			</Field>
			<PhotoField place={place?.name} {date} bind:file={photo.file} bind:remove={photo.remove} />
		</div>
	</Section>
</FormPage>

<style>
	.stack {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
</style>

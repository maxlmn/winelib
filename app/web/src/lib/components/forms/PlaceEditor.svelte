<script lang="ts">
	import { untrack } from 'svelte';
	import Field from './Field.svelte';
	import LocationPicker from './LocationPicker.svelte';
	import FormPage from './FormPage.svelte';
	import Section from './Section.svelte';
	import { blank, check, num, remove, save } from '#lib/api/forms.ts';
	import type { Options, PlaceForm } from '#lib/api/forms.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';
	import { FRIENDS, isFriends, withFriends } from '#lib/places.ts';

	let { options, place }: { options: Options; place: PlaceForm | null } = $props();

	// Stored coordinates can carry 15 decimals; 6 is ~10 cm
	const round6 = (n?: number | null) => (n === null || n === undefined ? null : Math.round(n * 1e6) / 1e6);

	// The form edits a copy; the route re-creates the editor for another place ({#key})
	const p = untrack(() => place);
	let f = $state({
		name: blank(p?.name), city: blank(p?.city), country: blank(p?.country), type: blank(p?.type), notes: blank(p?.notes),
		michelin_stars: p?.michelin_stars ?? null, lat: round6(p?.lat), lng: round6(p?.lng)
	});
	let errors = $state<Record<string, string>>({});
	// "@Mia": a friend's home, named after who it is
	const friends = $derived(isFriends(f.type));
	function onname() {
		if (f.name.startsWith('@')) {
			f.name = f.name.slice(1).trimStart();
			f.type = FRIENDS;
		}
	}

	async function onsave() {
		check(f.name.trim() ? {} : { name: 'Name is required' });
		const { id } = await save('places', p?.id ?? null, f);
		return links.place(id);
	}

	const used = p ? [p.tastings && plural(p.tastings, 'tasting note'), p.visits && plural(p.visits, 'visit')].filter(Boolean).join(' and ') : '';
</script>

<FormPage
	title={p ? `Edit ${p.name}` : 'Add place'}
	subtitle={used || undefined}
	saveLabel="Save place"
	fallback={p ? links.place(p.id) : links.places()}
	{onsave}
	bind:fieldErrors={errors}
	remove={p
		? {
				what: p.name,
				message: used ? `It is used by ${used}.` : 'This can’t be undone.',
				blocked: !!used,
				run: async () => (await remove('places', p.id), links.places())
			}
		: undefined}
>
	<Section title="Place">
		<div class="grid">
			<Field label={friends ? 'Who' : 'Name'} for="pl-name" required error={errors.name} span
				hint={friends ? 'Whose home: shown as a house, who, and the city' : 'A friend’s home: @ and their name'}>
				<input id="pl-name" bind:value={f.name} oninput={onname} aria-invalid={!!errors.name} placeholder={friends ? 'e.g. Matt & Sarah' : 'e.g. Odette'} />
			</Field>
			<Field label="City" for="pl-city">
				<input id="pl-city" bind:value={f.city} />
			</Field>
			<Field label="Country" for="pl-country">
				<input id="pl-country" bind:value={f.country} />
			</Field>
			<Field label="Type" for="pl-type" hint="Restaurant, Home, Friend’s Place, Bar, Winery…">
				<input id="pl-type" list="pl-types" bind:value={f.type} />
				<datalist id="pl-types">
					{#each withFriends(options.place_types) as t}<option value={t}></option>{/each}
				</datalist>
			</Field>
			{#if !friends}
			<Field label="Michelin stars" for="pl-stars" error={errors.michelin_stars}>
				<select
					id="pl-stars"
					value={f.michelin_stars ?? ''}
					onchange={(e) => (f.michelin_stars = num(e.currentTarget.value))}
				>
					<option value="">—</option>
					{#each [0, 1, 2, 3] as s}<option value={s}>{s ? '★'.repeat(s) : 'None'}</option>{/each}
				</select>
			</Field>
			{/if}
			<Field label="Notes" for="pl-notes" span>
				<textarea id="pl-notes" rows="3" bind:value={f.notes}></textarea>
			</Field>
		</div>
	</Section>

	<Section title="Location">
		<LocationPicker
			bind:lat={f.lat}
			bind:lng={f.lng}
			onname={(name) => !f.name.trim() && (f.name = name)}
			query={[f.name, f.city, f.country].map((x) => x?.trim()).filter(Boolean).join(', ')}
		/>
		<div class="grid">
			<Field label="Latitude" for="pl-lat" error={errors.lat}>
				<input id="pl-lat" type="number" step="0.000001" min="-90" max="90" value={f.lat ?? ''} oninput={(e) => (f.lat = num(e.currentTarget.value))} />
			</Field>
			<Field label="Longitude" for="pl-lng" error={errors.lng}>
				<input id="pl-lng" type="number" step="0.000001" min="-180" max="180" value={f.lng ?? ''} oninput={(e) => (f.lng = num(e.currentTarget.value))} />
			</Field>
		</div>
	</Section>
</FormPage>

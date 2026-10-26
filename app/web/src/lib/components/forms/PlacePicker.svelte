<script lang="ts">
	import { FRIENDS, withFriends } from '#lib/places.ts';
	import Combobox from './Combobox.svelte';
	import Field from './Field.svelte';
	import { lookup, placeHint } from '#lib/api/forms.ts';
	import type { PlaceChoice, PlaceOption } from '#lib/api/forms.ts';

	interface Props {
		value: PlaceChoice | null;
		placeTypes: string[];
		id: string;
		label?: string;
		required?: boolean;
		error?: string;
	}

	/** Pick a place, or name a new one and give its city, country and type. */
	let { value = $bindable(), placeTypes, id, label = 'Place', required = false, error }: Props = $props();

	const search = (q: string) => lookup<PlaceOption>('places', { q });
</script>

<Field {label} for={id} {required} {error} hint={value?.id === null ? undefined : 'Type to search; a new name creates the place (@ and a name: a friend’s home)'}>
	<Combobox
		{id}
		{value}
		{search}
		{required}
		invalid={!!error}
		creatable="place"
		placeholder="Search places…"
		hint={(p) => placeHint(p) || p.type}
		onchange={(c, item) =>
			(value = c && (item ? { ...c, city: item.city, country: item.country, type: item.type }
				: c.name.startsWith('@') ? { ...c, name: c.name.slice(1).trim(), type: FRIENDS } // "@Mia": a friend's home
				: { ...c, type: 'Restaurant' }))}
	/>
</Field>

{#if value && value.id === null}
	<div class="new grid three">
		<Field label="City" for="{id}-city">
			<input id="{id}-city" bind:value={value.city} />
		</Field>
		<Field label="Country" for="{id}-country">
			<input id="{id}-country" bind:value={value.country} />
		</Field>
		<Field label="Type" for="{id}-type">
			<input id="{id}-type" list="{id}-types" bind:value={value.type} />
			<datalist id="{id}-types">
				{#each withFriends(placeTypes) as t}<option value={t}></option>{/each}
			</datalist>
		</Field>
	</div>
{/if}

<style>
	.new {
		padding: 12px;
		border-left: 3px solid var(--accent);
		background: var(--accent-soft);
		border-radius: 0 8px 8px 0;
	}
</style>

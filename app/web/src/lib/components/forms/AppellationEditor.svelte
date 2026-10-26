<script lang="ts">
	import { regionColor } from '#lib/regions.svelte.ts';
	import { untrack } from 'svelte';
	import Combobox from './Combobox.svelte';
	import Field from './Field.svelte';
	import FormPage from './FormPage.svelte';
	import Section from './Section.svelte';
	import { blank, check, remove, save, toRef } from '#lib/api/forms.ts';
	import type { AppellationForm, Choice, Options } from '#lib/api/forms.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';

	/** An appellation's own fields; the EU / INAO ones (PDO ID, yields, shapes) stay as imported. */
	let { options, appellation }: { options: Options; appellation: AppellationForm } = $props();

	// The form edits a copy; the route re-creates the editor for another appellation ({#key})
	const a = untrack(() => appellation);
	let name = $state(blank(a.name));
	let region = $state<Choice | null>(a.region ?? null);
	let f = $state({
		subregion: blank(a.subregion), type: blank(a.type), colors: blank(a.colors), varieties_text: blank(a.varieties_text),
		location_link: blank(a.location_link), details: blank(a.details), aliases: blank(a.aliases)
	});
	let errors = $state<Record<string, string>>({});

	async function onsave() {
		check(name.trim() ? {} : { name: 'Name is required' });
		const { id } = await save('appellations', a.id, { name, region: toRef(region), ...f });
		return links.appellation(id);
	}
</script>

<FormPage
	title={`Edit ${a.name}`}
	subtitle={plural(a.wines, 'wine')}
	saveLabel="Save appellation"
	fallback={links.appellation(a.id)}
	{onsave}
	bind:fieldErrors={errors}
	remove={{
		what: a.name,
		message: a.wines ? `${a.name} still has ${plural(a.wines, 'wine')}: give them another appellation first.` : 'This can’t be undone.',
		blocked: !!a.wines,
		run: async () => {
			const r = await remove<{ deleted: number; region: string | null }>('appellations', a.id);
			return r.region ? links.region(r.region) : '/';
		}
	}}
>
	<Section title="Appellation">
		<div class="grid">
			<Field label="Name" for="a-name" required error={errors.name} span>
				<input id="a-name" bind:value={name} aria-invalid={!!errors.name} placeholder="e.g. Côte-Rôtie" />
			</Field>
			<Field label="Also known as" for="a-aliases" hint="Other names, comma separated: imports and searches match them" span>
				<input id="a-aliases" bind:value={f.aliases} placeholder="e.g. Ermitage" />
			</Field>
			<Field label="Region" for="a-region">
				<Combobox
					id="a-region"
					value={region}
					options={options.regions}
					hint={(r) => r.country}
					hintDot={(r) => regionColor(r.name)}
					creatable="region"
					placeholder="Region…"
					onchange={(c) => (region = c)}
				/>
			</Field>
			<Field label="Subregion" for="a-subregion">
				<input id="a-subregion" bind:value={f.subregion} placeholder="e.g. Côte de Nuits" />
			</Field>
			<Field label="Type" for="a-type" hint="e.g. AOC, DOCG, PDO">
				<input id="a-type" bind:value={f.type} />
			</Field>
			<Field label="Colors" for="a-colors" hint="e.g. Red, White">
				<input id="a-colors" bind:value={f.colors} />
			</Field>
			<Field label="Authorized varieties" for="a-varieties" hint="Comma separated" span>
				<input id="a-varieties" bind:value={f.varieties_text} />
			</Field>
			<Field label="Official info link" for="a-link" span>
				<input id="a-link" type="url" bind:value={f.location_link} />
			</Field>
		</div>
	</Section>

	<Section title="Details">
		<div class="grid">
			<Field label="Details" for="a-details" span>
				<textarea id="a-details" rows="5" bind:value={f.details}></textarea>
			</Field>
		</div>
	</Section>
</FormPage>

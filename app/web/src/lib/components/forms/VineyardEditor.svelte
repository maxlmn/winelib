<script lang="ts">
	import { regionColor } from '#lib/regions.svelte.ts';
	import { untrack } from 'svelte';
	import Combobox from './Combobox.svelte';
	import Field from './Field.svelte';
	import FormPage from './FormPage.svelte';
	import Section from './Section.svelte';
	import { blank, check, remove, save, toRef } from '#lib/api/forms.ts';
	import type { Choice, Options, VineyardForm } from '#lib/api/forms.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';

	/** A vineyard's name and place; its outline (Draw outline) and external id stay. */
	let { options, vineyard }: { options: Options; vineyard: VineyardForm } = $props();

	// The form edits a copy; the route re-creates the editor for another vineyard ({#key})
	const v = untrack(() => vineyard);
	let name = $state(blank(v.name));
	let region = $state<Choice | null>(v.region ?? null);
	let f = $state({ sub_region: blank(v.sub_region), village: blank(v.village) });
	let errors = $state<Record<string, string>>({});

	async function onsave() {
		check(name.trim() ? {} : { name: 'Name is required' });
		const { id } = await save('vineyards', v.id, { name, region: toRef(region), ...f });
		return links.vineyard(id);
	}
</script>

<FormPage
	title={`Edit ${v.name}`}
	subtitle={plural(v.wines, 'wine')}
	saveLabel="Save vineyard"
	fallback={links.vineyard(v.id)}
	{onsave}
	bind:fieldErrors={errors}
	remove={{
		what: v.name,
		message: v.wines ? `${v.name} still has ${plural(v.wines, 'wine')}: give them another vineyard first.` : 'Its outline goes too. This can’t be undone.',
		blocked: !!v.wines,
		run: async () => {
			const r = await remove<{ deleted: number; region: string | null }>('vineyards', v.id);
			return r.region ? links.region(r.region) : '/';
		}
	}}
>
	<Section title="Vineyard">
		<div class="grid">
			<Field label="Name" for="v-name" required error={errors.name} span>
				<input id="v-name" bind:value={name} aria-invalid={!!errors.name} placeholder="e.g. Les Amoureuses" />
			</Field>
			<Field label="Region" for="v-region">
				<Combobox
					id="v-region"
					value={region}
					options={options.regions}
					hint={(r) => r.country}
					hintDot={(r) => regionColor(r.name)}
					creatable="region"
					placeholder="Region…"
					onchange={(c) => (region = c)}
				/>
			</Field>
			<Field label="Sub-region" for="v-subregion">
				<input id="v-subregion" bind:value={f.sub_region} placeholder="e.g. Côte de Nuits" />
			</Field>
			<Field label="Village" for="v-village">
				<input id="v-village" bind:value={f.village} placeholder="e.g. Chambolle-Musigny" />
			</Field>
		</div>
	</Section>
</FormPage>

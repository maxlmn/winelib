<script lang="ts">
	import { regionColor } from '#lib/regions.svelte.ts';
	import { untrack } from 'svelte';
	import Combobox from './Combobox.svelte';
	import Field from './Field.svelte';
	import FormPage from './FormPage.svelte';
	import Section from './Section.svelte';
	import { blank, check, remove, save, toRef } from '#lib/api/forms.ts';
	import type { Choice, Options, ProducerForm } from '#lib/api/forms.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';

	let { options, producer }: { options: Options; producer: ProducerForm | null } = $props();

	// The form edits a copy; the route re-creates the editor for another producer ({#key})
	const p = untrack(() => producer);
	let name = $state(blank(p?.name));
	let region = $state<Choice | null>(p?.region ?? null);
	let f = $state({
		subregion: blank(p?.subregion), village: blank(p?.village), winemaker: blank(p?.winemaker), owner: blank(p?.owner),
		type: blank(p?.type), importers: blank(p?.importers), lists: blank(p?.lists), profile_url: blank(p?.profile_url),
		website: blank(p?.website), notes: blank(p?.notes), description: blank(p?.description), aliases: blank(p?.aliases)
	});
	let errors = $state<Record<string, string>>({});

	async function onsave() {
		check(name.trim() ? {} : { name: 'Name is required' });
		const { id } = await save('producers', p?.id ?? null, { name, region: toRef(region), ...f });
		return links.producer(id);
	}

	const capitalize = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
</script>

<FormPage
	title={p ? `Edit ${p.name}` : 'Add producer'}
	subtitle={p ? plural(p.wines, 'wine') : undefined}
	saveLabel="Save producer"
	fallback={p ? links.producer(p.id) : links.producers()}
	{onsave}
	bind:fieldErrors={errors}
	remove={p
		? {
				what: p.name,
				message: p.wines ? `${p.name} still has ${plural(p.wines, 'wine')}: move or delete them first.` : 'This can’t be undone.',
				blocked: !!p.wines,
				run: async () => (await remove('producers', p.id), links.producers())
			}
		: undefined}
>
	<Section title="Producer">
		<div class="grid">
			<Field label="Name" for="p-name" required error={errors.name} span>
				<input id="p-name" bind:value={name} aria-invalid={!!errors.name} placeholder="e.g. Domaine Leflaive" />
			</Field>
			<Field label="Region" for="p-region">
				<Combobox
					id="p-region"
					value={region}
					options={options.regions}
					hint={(r) => r.country}
					hintDot={(r) => regionColor(r.name)}
					creatable="region"
					placeholder="Region…"
					onchange={(c) => (region = c)}
				/>
			</Field>
			<Field label="Also known as" for="p-aliases" hint="Other names, comma separated: imports match them (e.g. Chave)" span>
				<input id="p-aliases" bind:value={f.aliases} placeholder="e.g. Chave, JL Chave" />
			</Field>
			<Field label="Type" for="p-type">
				<select id="p-type" bind:value={f.type}>
					<option value="">—</option>
					{#each options.producer_types as t}<option value={t}>{capitalize(t)}</option>{/each}
				</select>
			</Field>
			<Field label="Subregion" for="p-subregion">
				<input id="p-subregion" bind:value={f.subregion} placeholder="e.g. Côte de Beaune" />
			</Field>
			<Field label="Village" for="p-village">
				<input id="p-village" bind:value={f.village} placeholder="e.g. Puligny-Montrachet" />
			</Field>
			<Field label="Winemaker" for="p-winemaker">
				<input id="p-winemaker" bind:value={f.winemaker} />
			</Field>
			<Field label="Owner" for="p-owner">
				<input id="p-owner" bind:value={f.owner} />
			</Field>
		</div>
	</Section>

	<Section title="Links and lists">
		<div class="grid">
			<Field label="Importers" for="p-importers">
				<input id="p-importers" bind:value={f.importers} />
			</Field>
			<Field label="Lists" for="p-lists" hint="e.g. [The New French Wine]">
				<input id="p-lists" bind:value={f.lists} />
			</Field>
			<Field label="Profile URL" for="p-profile">
				<input id="p-profile" type="url" bind:value={f.profile_url} />
			</Field>
			<Field label="Website" for="p-website">
				<input id="p-website" type="url" bind:value={f.website} />
			</Field>
		</div>
	</Section>

	<Section title="Notes">
		<div class="grid">
			<Field label="Notes" for="p-notes" span>
				<textarea id="p-notes" rows="3" bind:value={f.notes}></textarea>
			</Field>
			<Field label="Description" for="p-description" span>
				<textarea id="p-description" rows="5" bind:value={f.description}></textarea>
			</Field>
		</div>
	</Section>
</FormPage>

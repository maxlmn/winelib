<script lang="ts">
	import { untrack } from 'svelte';
	import FormPage from './FormPage.svelte';
	import Section from './Section.svelte';
	import WineFields from './WineFields.svelte';
	import { check, emptyWine, remove, save, toWineIn, vintageLabel, wineDraft, wineErrors } from '#lib/api/forms.ts';
	import type { Options, ProducerForm, WineForm } from '#lib/api/forms.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';

	let { options, wine, producer }: { options: Options; wine: WineForm | null; producer: ProducerForm | null } = $props();

	// The form edits a copy; the route re-creates the editor for another wine ({#key})
	const w = untrack(() => wine);
	let draft = $state(untrack(() => (w ? wineDraft(w) : emptyWine(producer && { id: producer.id, name: producer.name }, producer?.region ?? null))));
	let errors = $state<Record<string, string>>({});

	async function onsave() {
		check(wineErrors(draft));
		const { id } = await save('wines', w?.id ?? null, toWineIn(draft));
		return links.wine(id);
	}

	const title = w ? `${w.summary.producer} ${w.summary.cuvee} ${vintageLabel(w.summary)}`.trim() : 'Add wine';
</script>

<FormPage
	title={w ? `Edit ${title}` : title}
	subtitle={w ? plural(w.bottles, 'bottle') + ' recorded' : undefined}
	saveLabel="Save wine"
	fallback={w ? links.wine(w.id) : producer ? links.producer(producer.id) : links.cellar()}
	{onsave}
	bind:fieldErrors={errors}
	remove={w
		? {
				what: 'this wine',
				message: w.bottles ? `It still has ${plural(w.bottles, 'bottle')} (in the cellar or tasted): delete them first.` : 'This can’t be undone.',
				blocked: !!w.bottles,
				run: async () => links.producer((await remove<{ producer_id: number }>('wines', w.id)).producer_id)
			}
		: undefined}
>
	<Section title="Wine">
		<WineFields bind:value={draft} {options} prefix="w" {errors} fromLink={!wine} />
	</Section>
</FormPage>

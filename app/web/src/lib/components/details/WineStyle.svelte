<script lang="ts">
	/** A wine's style tags on its page, under its appellation: those set on it (outlined in the accent) and its
	 * tastings' (with how many found it); none, nothing shown. `editing` (bound, the header menu's Style tags) opens
	 * the picker: its own set, the other vintages' and the shared words offered. */
	import { invalidateAll } from '$app/navigation';
	import TagPicker from '#lib/components/TagPicker.svelte';
	import { setWineTags, suggestions, type WineTag } from '#lib/api/tags.ts';

	let {
		wineId,
		tags,
		cuvee = [],
		editing = $bindable(false)
	}: { wineId: number; tags: WineTag[]; cuvee?: string[]; editing?: boolean } = $props();

	let picked = $state<string[]>([]);
	let offered = $state<string[]>([]);
	let error = $state('');
	// opened (the menu): the picker starts from what's set
	$effect(() => {
		if (editing) load();
	});
	async function load() {
		error = '';
		picked = tags.filter((t) => t.set).map((t) => t.tag);
		offered = await suggestions(cuvee, tags.map((t) => t.tag));
	}
	async function save() {
		error = '';
		try {
			await setWineTags(wineId, picked);
			editing = false;
			await invalidateAll();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Couldn’t save';
		}
	}
	const title = (t: WineTag) =>
		[t.set && 'set on the wine', t.tastings && `found in ${t.tastings} tasting${t.tastings > 1 ? 's' : ''}`].filter(Boolean).join(', ');
</script>

{#if editing}
	<div class="style">
		<div class="edit">
			<TagPicker bind:value={picked} suggestions={offered} />
			<div class="buttons">
				<button class="btn small primary" onclick={save}>Save</button>
				<button class="btn small" onclick={() => (editing = false)}>Cancel</button>
				{#if error}<span class="error">{error}</span>{/if}
			</div>
			<p class="muted hint">The words from its tastings show on their own: pick here what you'd say of the wine itself.</p>
		</div>
	</div>
{:else if tags.length}
	<div class="pills" aria-label="Style">
		{#each tags as t (t.tag)}
			<span class="pill" class:set={t.set} title={title(t)}>{t.tag}{#if t.tastings > 1}<span class="n num">×{t.tastings}</span>{/if}</span>
		{/each}
	</div>
{/if}

<style>
	.style {
		margin-top: 8px;
		font-size: 13px;
	}
	.pills {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: 6px;
	}
	.pill {
		padding: 0 8px;
		border: 1px solid var(--border);
		border-radius: 10px;
		font-size: 11px;
		line-height: 1.6;
	}
	.pill.set {
		border-color: var(--accent);
		color: var(--accent);
	}
	.n {
		margin-left: 4px;
		color: var(--muted);
		font-size: 11px;
	}
	.edit {
		display: flex;
		flex-direction: column;
		gap: 8px;
		flex: 1;
	}
	.buttons {
		display: flex;
		gap: 8px;
		align-items: center;
	}
	.hint {
		margin: 0;
		font-size: 12px;
	}
	.error {
		color: var(--down);
		font-size: 12px;
	}
</style>

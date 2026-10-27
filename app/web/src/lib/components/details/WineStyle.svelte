<script lang="ts">
	/** A wine's style tags on its page: those set on it (filled) and its tastings' (with how many found it);
	 * Edit sets its own, the other vintages' and the shared words offered. */
	import { invalidateAll } from '$app/navigation';
	import TagPicker from '#lib/components/TagPicker.svelte';
	import { setWineTags, suggestions, type WineTag } from '#lib/api/tags.ts';

	let { wineId, tags, cuvee = [] }: { wineId: number; tags: WineTag[]; cuvee?: string[] } = $props();

	let editing = $state(false);
	let picked = $state<string[]>([]);
	let offered = $state<string[]>([]);
	let error = $state('');
	async function edit() {
		picked = tags.filter((t) => t.set).map((t) => t.tag);
		offered = await suggestions(cuvee, tags.map((t) => t.tag));
		editing = true;
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

<div class="style">
	<span class="label">Style</span>
	{#if editing}
		<div class="edit">
			<TagPicker bind:value={picked} suggestions={offered} />
			<div class="buttons">
				<button class="btn small primary" onclick={save}>Save</button>
				<button class="btn small" onclick={() => (editing = false)}>Cancel</button>
				{#if error}<span class="error">{error}</span>{/if}
			</div>
			<p class="muted hint">The words from its tastings show on their own: pick here what you'd say of the wine itself.</p>
		</div>
	{:else}
		<div class="pills">
			{#each tags as t (t.tag)}
				<span class="pill" class:set={t.set} title={title(t)}>{t.tag}{#if t.tastings > 1}<span class="n num">×{t.tastings}</span>{/if}</span>
			{:else}
				<span class="muted none">{cuvee.length ? `Other vintages: ${cuvee.join(', ')}` : 'None yet'}</span>
			{/each}
			<button class="link" onclick={edit}>{tags.some((t) => t.set) ? 'Edit' : '+ Add'}</button>
		</div>
	{/if}
</div>

<style>
	.style {
		display: flex;
		gap: 10px;
		align-items: baseline;
		margin-top: 10px;
		font-size: 13px;
	}
	.label {
		flex: none;
		width: 92px;
		color: var(--muted);
	}
	.pills {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		align-items: baseline;
	}
	.pill {
		padding: 1px 9px;
		border: 1px solid var(--border);
		border-radius: 11px;
		font-size: 12px;
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
	.none {
		font-size: 12px;
	}
	.link {
		border: none;
		background: none;
		padding: 0 4px;
		color: var(--accent);
		font: inherit;
		font-size: 12px;
		cursor: pointer;
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

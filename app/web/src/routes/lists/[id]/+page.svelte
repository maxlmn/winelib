<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { onMount } from 'svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import ListDots from '#lib/components/ListDots.svelte';
	import { addEntry, compareKeys, deleteList, editEntry, editList, entryName, KIND_LABEL, noteKey, removeEntry, type EntryKind, type ListEntry } from '#lib/api/lists.ts';
	import { links } from '#lib/links.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';

	let { data } = $props();
	const list = $derived(data.list);

	let show = $state<'all' | 'todo' | 'tasted' | 'owned'>('all');
	// Sorted by the list's order, its notes (they hold ranks and tiers: "#7", "Premier Grand Cru Classé"), the names,
	// or what's left to taste first
	let sort = $state<'list' | 'note' | 'name' | 'todo'>('list');
	const byName = (a: ListEntry, b: ListEntry) => entryName(a).localeCompare(entryName(b));
	const sorted = $derived(
		[...list.items].sort((a, b) =>
			sort === 'note'
				? compareKeys(noteKey(a.note), noteKey(b.note)) || byName(a, b)
				: sort === 'name'
					? byName(a, b)
					: sort === 'todo'
						? Number(a.tasted) - Number(b.tasted) || a.position - b.position
						: a.position - b.position
		)
	);
	const shown = $derived(
		sorted.filter((i) => (show === 'todo' ? !i.tasted : show === 'tasted' ? i.tasted : show === 'owned' ? i.owned > 0 : true))
	);
	const hasNotes = $derived(list.items.some((i) => i.note));
	// Greyed out, not hidden: what's left to find stands out in the whole list (remembered on this device)
	let dim = $state({ tasted: false, owned: false });
	onMount(() => {
		try {
			dim = { ...dim, ...JSON.parse(localStorage.getItem('winelib-list-dim') ?? '{}') };
		} catch {
			/* no storage: not remembered */
		}
	});
	function setDim(key: 'tasted' | 'owned', on: boolean) {
		dim = { ...dim, [key]: on };
		try {
			localStorage.setItem('winelib-list-dim', JSON.stringify(dim));
		} catch {
			/* no storage */
		}
	}
	const dimmed = (i: ListEntry) => (dim.tasted && i.tasted) || (dim.owned && i.owned > 0);
	// the mosaic in the entries' order (the whole list, whatever's shown)
	const dots = $derived(sorted.map((i) => ({ tasted: i.tasted, owned: i.owned > 0, region: i.region, color: i.wine?.color ?? null })));
	const pct = $derived(list.entries ? Math.round((100 * list.tasted) / list.entries) : 0);
	const when = (d: string | null) => (d ? new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '');
	const href = (i: ListEntry) => (i.kind === 'producer' || !i.wine ? links.producer(i.producer!.id) : links.wine(i.wine.id));

	// --- Adding: a wine (this vintage or any) or a producer, found by name ---
	let q = $state('');
	let results = $state<{ kind: string; id: number; title: string; sub: string; region?: string }[]>([]);
	let timer: ReturnType<typeof setTimeout>;
	let note = $state('');
	function search(text: string) {
		q = text;
		clearTimeout(timer);
		timer = setTimeout(async () => {
			if (text.trim().length < 2) return (results = []);
			const r = await fetch(`/api/search?q=${encodeURIComponent(text)}&limit=6`).then((r) => r.json());
			results = r.results.filter((x: { kind: string }) => x.kind === 'wine' || x.kind === 'producer');
		}, 150);
	}
	async function add(kind: EntryKind, id: number) {
		const r = await addEntry(list.id, kind === 'producer' ? { kind, producer_id: id, note } : { kind, wine_id: id, note });
		addNote = r.existing ? 'Already on the list' : '';
		q = '';
		results = [];
		note = '';
		await invalidateAll();
	}
	let addNote = $state('');

	// --- An entry's note, the entry itself ---
	let editing = $state<number | null>(null);
	let draftNote = $state('');
	async function saveNote(i: ListEntry) {
		await editEntry(list.id, i.id, { note: draftNote });
		editing = null;
		await invalidateAll();
	}
	async function remove(i: ListEntry) {
		await removeEntry(list.id, i.id);
		await invalidateAll();
	}

	// --- The list itself ---
	let editingList = $state(false);
	let form = $state({ name: '', description: '', source: '', url: '' });
	let listError = $state('');
	function openEdit() {
		form = { name: list.name, description: list.description ?? '', source: list.source ?? '', url: list.url ?? '' };
		editingList = true;
		listError = '';
	}
	async function saveList() {
		try {
			await editList(list.id, { name: form.name, description: form.description || null, source: form.source || null, url: form.url || null });
			editingList = false;
			await invalidateAll();
		} catch (e) {
			listError = e instanceof Error ? e.message : 'Couldn’t save';
		}
	}
	async function drop() {
		if (!confirm(`Delete the list “${list.name}”? Its wines stay in WineLib.`)) return;
		await deleteList(list.id);
		goto(links.lists());
	}
</script>

<svelte:head><title>{list.name} · WineLib</title></svelte:head>

<div class="page-head">
	<div>
		<a class="muted crumb" href={links.lists()}>Lists</a>
		<h1>{list.name}</h1>
		{#if list.source || list.url}
			<div class="muted">{list.source ?? ''}{#if list.url}{list.source ? ' · ' : ''}<a href={list.url} target="_blank" rel="noopener noreferrer">the original ↗</a>{/if}</div>
		{/if}
	</div>
	<div class="actions">
		<button class="btn" onclick={openEdit}>Edit</button>
	</div>
</div>

{#if editingList}
	<form class="edit card" onsubmit={(e) => { e.preventDefault(); saveList(); }}>
		<label><span class="label">Name</span><input bind:value={form.name} required /></label>
		<label><span class="label">Made by</span><input bind:value={form.source} /></label>
		<label class="wide"><span class="label">About it</span><textarea rows="2" bind:value={form.description}></textarea></label>
		<label class="wide"><span class="label">Where it was published</span><input type="url" bind:value={form.url} placeholder="https://…" /></label>
		<div class="wide buttons">
			{#if listError}<span class="error">{listError}</span>{/if}
			<button type="button" class="btn danger-link" onclick={drop}>Delete the list</button>
			<button type="button" class="btn" onclick={() => (editingList = false)}>Cancel</button>
			<button class="btn primary">Save</button>
		</div>
	</form>
{/if}

{#if list.description}<p class="about">{list.description}</p>{/if}

<section class="progress card">
	<div class="score">
		<span class="big num">{list.tasted}<span class="of"> / {list.entries}</span></span>
		<span class="muted">tasted{#if list.owned}{` · ${list.owned} in the cellar`}{/if}</span>
		<span class="bar" aria-hidden="true"><span style:width="{pct}%"></span></span>
		{#if list.entries && list.tasted === list.entries}<span class="done">Complete</span>{/if}
	</div>
	<ListDots {dots} size={18} />
</section>

<section class="add card">
	<input type="search" placeholder="Add a wine or a producer: search by name…" value={q} oninput={(e) => search(e.currentTarget.value)} />
	{#if results.length}
		<input class="note-in" bind:value={note} placeholder="A note for it (optional): “the 2018”, “magnum”…" />
		<ul>
			{#each results as r (r.kind + r.id)}
				<li>
					<span class="dot" style:background={regionColor(r.region)}></span>
					<span class="what"><span>{r.title}</span> <span class="muted">{r.sub}</span></span>
					{#if r.kind === 'wine'}
						<button class="btn small" onclick={() => add('wine', r.id)}>This vintage</button>
						<button class="btn small" onclick={() => add('cuvee', r.id)}>Any vintage</button>
					{:else}
						<button class="btn small" onclick={() => add('producer', r.id)}>The producer</button>
					{/if}
				</li>
			{/each}
		</ul>
	{:else if q.trim().length >= 2}
		<p class="muted hint">Nothing by that name. A wine not in WineLib yet: <a href={links.newWine()}>add it</a> first.</p>
	{/if}
	{#if addNote}<p class="muted hint">{addNote}</p>{/if}
</section>

{#if list.items.length}
	<div class="tools">
	<div class="filters" role="group" aria-label="Show">
		<button class:on={show === 'all'} onclick={() => (show = 'all')}>All <span class="num">{list.entries}</span></button>
		<button class:on={show === 'todo'} onclick={() => (show = 'todo')}>To taste <span class="num">{list.entries - list.tasted}</span></button>
		<button class:on={show === 'tasted'} onclick={() => (show = 'tasted')}>Tasted <span class="num">{list.tasted}</span></button>
		<button class:on={show === 'owned'} onclick={() => (show = 'owned')}>In the cellar <span class="num">{list.owned}</span></button>
	</div>
	<div class="dim" role="group" aria-label="Grey out">
		<span class="muted">Grey out</span>
		<label><input type="checkbox" checked={dim.tasted} onchange={(e) => setDim('tasted', e.currentTarget.checked)} /> tasted</label>
		<label><input type="checkbox" checked={dim.owned} onchange={(e) => setDim('owned', e.currentTarget.checked)} /> in the cellar</label>
	</div>
	<label class="sort">
		<span class="muted">Sort</span>
		<select bind:value={sort}>
			<option value="list">The list’s order</option>
			{#if hasNotes}<option value="note">By note (ranks, tiers)</option>{/if}
			<option value="name">By name</option>
			<option value="todo">To taste first</option>
		</select>
	</label>
	</div>

	<ol class="entries card">
		{#each shown as i (i.id)}
			<li class:tasted={i.tasted} class:dimmed={dimmed(i)}>
				<span class="tick" role="img" aria-label={i.tasted ? 'Tasted' : 'Not tasted yet'}>{#if i.tasted}✓{/if}</span>
				<span class="end"><BottleEnd region={regionColor(i.region)} color={i.wine?.color} size={16} /></span>
				<div class="what">
					<div class="name">
						<a href={href(i)}>{entryName(i)}</a>
						<span class="kind">{KIND_LABEL[i.kind]}</span>
					</div>
					<div class="muted sub">{[i.wine?.appellation, regionLabel(i.region)].filter(Boolean).join(' · ')}</div>
					{#if editing === i.id}
						<form class="note-edit" onsubmit={(e) => { e.preventDefault(); saveNote(i); }}>
							<input bind:value={draftNote} placeholder="A note" />
							<button class="btn small primary">Save</button>
							<button type="button" class="btn small" onclick={() => (editing = null)}>Cancel</button>
						</form>
					{:else if i.note}
						<button class="note" onclick={() => { editing = i.id; draftNote = i.note ?? ''; }}>{i.note}</button>
					{/if}
				</div>
				<div class="status">
					{#if i.tasted}
						<div>
							Tasted {when(i.last_tasted)}{#if i.best_rating}{' · '}<b>{i.best_rating}</b>{/if}
							{#if i.tastings > 1}<span class="muted"> ({i.tastings}×)</span>{/if}
						</div>
						{#if i.kind !== 'wine' && i.tasted_wine_id}<a class="muted small-link" href={links.wine(i.tasted_wine_id)}>the vintage tasted</a>{/if}
					{:else}
						<div class="muted">To taste</div>
					{/if}
					{#if i.owned}<div class="owned">{i.owned} in the cellar</div>{/if}
				</div>
				<div class="row-actions">
					{#if editing !== i.id && !i.note}<button class="link" onclick={() => { editing = i.id; draftNote = ''; }}>Note</button>{/if}
					<button class="link" onclick={() => remove(i)} aria-label="Remove {entryName(i)} from the list">Remove</button>
				</div>
			</li>
		{/each}
	</ol>
{/if}

<style>
	.crumb {
		font-size: 13px;
	}
	.page-head h1 {
		margin: 2px 0;
	}
	.about {
		max-width: 760px;
		margin: -6px 0 16px;
		color: var(--muted);
	}
	.edit {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
		gap: 10px 14px;
		padding: 14px 16px;
		margin-bottom: 16px;
	}
	.edit label {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.wide {
		grid-column: 1 / -1;
	}
	.buttons {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: 8px;
	}
	.danger-link {
		margin-right: auto;
		color: var(--down);
	}
	.label {
		font-size: 12px;
		color: var(--muted);
	}
	.error {
		color: var(--down);
		font-size: 13px;
	}
	.progress {
		padding: 16px 18px;
		margin-bottom: 14px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.score {
		display: flex;
		align-items: baseline;
		gap: 10px;
		flex-wrap: wrap;
	}
	.big {
		font-size: 30px;
		font-weight: 700;
		letter-spacing: -0.02em;
	}
	.of {
		font-size: 18px;
		font-weight: 500;
		color: var(--muted);
	}
	.bar {
		flex: 0 0 140px;
		height: 7px;
		border-radius: 4px;
		background: var(--surface-2);
		overflow: hidden;
		align-self: center;
	}
	.bar span {
		display: block;
		height: 100%;
		background: var(--accent);
	}
	.done {
		font-size: 12px;
		font-weight: 600;
		padding: 2px 10px;
		border-radius: 10px;
		color: var(--up);
		background: color-mix(in srgb, var(--up) 16%, transparent);
	}
	.add {
		padding: 12px;
		margin-bottom: 14px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.add input {
		width: 100%;
		box-sizing: border-box;
		padding: 9px 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
	}
	.add ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.add li {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 4px;
		border-top: 1px solid var(--border);
	}
	.add .what {
		flex: 1;
		min-width: 0;
	}
	.dot {
		flex: none;
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}
	.btn.small {
		padding: 4px 10px;
		font-size: 12px;
	}
	.hint {
		margin: 0 2px;
		font-size: 13px;
	}
	.tools {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 10px 16px;
		margin-bottom: 10px;
	}
	.filters {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.dim {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 13px;
	}
	.dim label {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.entries li.dimmed {
		opacity: 0.38;
	}
	.entries li.dimmed:hover {
		opacity: 0.8;
	}
	.sort {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		margin-left: auto;
	}
	.filters button {
		border: none;
		background: none;
		padding: 6px 12px;
		font-size: 13px;
		cursor: pointer;
		color: var(--muted);
	}
	.filters button.on {
		background: var(--accent);
		color: #fff;
	}
	.entries {
		list-style: none;
		margin: 0;
		padding: 4px 0;
	}
	.entries li {
		display: grid;
		grid-template-columns: 26px 24px minmax(0, 1fr) auto auto;
		gap: 4px 12px;
		align-items: center;
		padding: 10px 16px;
	}
	.entries li + li {
		border-top: 1px solid var(--border);
	}
	.tick {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		border: 2px solid var(--border);
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 13px;
		font-weight: 700;
		box-sizing: border-box;
	}
	li.tasted .tick {
		border-color: var(--up);
		background: var(--up);
		color: #fff;
	}
	.end {
		display: flex;
		justify-content: center;
	}
	.name {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 8px;
		font-weight: 600;
	}
	.name a {
		color: var(--text);
	}
	.kind {
		font-weight: 400;
		font-size: 12px;
		color: var(--muted);
	}
	.sub {
		font-size: 12px;
	}
	.note {
		border: none;
		background: none;
		padding: 0;
		font: inherit;
		font-style: italic;
		font-size: 13px;
		color: var(--text);
		cursor: pointer;
		text-align: left;
	}
	.note-edit {
		display: flex;
		gap: 6px;
		margin-top: 4px;
	}
	.status {
		text-align: right;
		font-size: 13px;
	}
	.owned {
		color: var(--up);
		font-weight: 600;
	}
	.small-link {
		font-size: 12px;
	}
	.row-actions {
		display: flex;
		gap: 10px;
		font-size: 12px;
	}
	button.link {
		border: none;
		background: none;
		padding: 0;
		color: var(--link);
		cursor: pointer;
		font: inherit;
	}
	@media (max-width: 760px) {
		.entries li {
			grid-template-columns: 26px 24px minmax(0, 1fr);
			padding: 10px 12px;
		}
		.status,
		.row-actions {
			grid-column: 3;
			text-align: left;
		}
	}
</style>

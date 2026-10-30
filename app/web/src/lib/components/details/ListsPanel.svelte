<script lang="ts">
	import { addEntry, KIND_LABEL, listsOf, loadLists, type EntryKind, type ListCard, type Membership } from '#lib/api/lists.ts';
	import { links } from '#lib/links.ts';

	/** The lists a wine or a producer is on (as that wine, its cuvée, or through its producer), each with its tick and
	 * the list's progress; and adding it to a list. On none: no card, unless `adding` (the page header's Add to a list
	 * icon, bound: false again once added or cancelled). */
	let { wineId, producerId, adding = $bindable(false) }: { wineId?: number; producerId?: number; adding?: boolean } = $props();

	const of = $derived(wineId ? { wine_id: wineId } : { producer_id: producerId! });
	let on = $state<Membership[] | null>(null);
	let all = $state<ListCard[]>([]);
	let open = $state(false);
	let target = $state<number | null>(null);
	let note = $state('');

	async function refresh() {
		on = await listsOf(fetch, of).catch(() => []);
	}
	// on the page and on moving to another wine (same component, new id)
	$effect(() => {
		void of;
		refresh();
	});

	// the header's icon: the form, opened
	$effect(() => {
		if (adding && !open) openAdd();
	});
	$effect(() => {
		if (!open) adding = false;
	});

	async function openAdd() {
		open = !open;
		if (open && !all.length) all = await loadLists(fetch).catch(() => []);
		target ??= all[0]?.id ?? null;
	}
	async function add(kind: EntryKind) {
		if (!target) return;
		const body = kind === 'producer' ? { kind, producer_id: producerId! } : { kind, wine_id: wineId! };
		note = (await addEntry(target, body)).existing ? 'Already on that list' : '';
		if (!note) open = false;
		await refresh();
	}
	const ticked = (m: Membership) => m.item.tasted;
</script>

{#if on && (on.length || open)}
	<section class="card lists">
		<div class="head">
			<h2>Lists {#if on.length}<span class="muted num">{on.length}</span>{/if}</h2>
			<button class="btn small" onclick={openAdd}>{open ? 'Cancel' : '＋ Add to a list'}</button>
		</div>
		{#if open}
			<div class="add">
				{#if all.length}
					<select bind:value={target} aria-label="The list">
						{#each all as l (l.id)}<option value={l.id}>{l.name}</option>{/each}
					</select>
					{#if wineId}
						<button class="btn small primary" onclick={() => add('wine')}>This vintage</button>
						<button class="btn small" onclick={() => add('cuvee')}>Any vintage</button>
					{:else}
						<button class="btn small primary" onclick={() => add('producer')}>Add the producer</button>
					{/if}
				{:else}
					<span class="muted">No lists yet: <a href={links.lists()}>make one</a>.</span>
				{/if}
				{#if note}<span class="muted">{note}</span>{/if}
			</div>
		{/if}
		{#if on.length}
			<ul>
				{#each on as m (m.item.id)}
					<li>
						<span class="tick" class:on={ticked(m)} role="img" aria-label={ticked(m) ? 'Tasted' : 'Not tasted yet'}>{#if ticked(m)}✓{/if}</span>
						<a href={links.list(m.id)}>{m.name}</a>
						<span class="muted as">
							{#if m.as === 'producer' && wineId}through its producer{:else if m.as === 'cuvee'}{wineId ? 'its cuvée, ' : `${m.wine?.cuvee || 'a cuvée'}, `}{KIND_LABEL.cuvee}{:else if m.as === 'wine'}{wineId ? KIND_LABEL.wine : `${m.wine?.cuvee ?? ''} ${m.wine?.vintage ?? ''}`}{:else}{KIND_LABEL.producer}{/if}
							{#if m.item.note}· “{m.item.note}”{/if}
						</span>
						<span class="progress num">{m.tasted}/{m.entries}</span>
					</li>
				{/each}
			</ul>
		{/if}
	</section>
{/if}

<style>
	.lists {
		padding: 14px 16px;
		margin-bottom: 16px;
	}
	.head {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	h2 {
		margin: 0;
		font-size: 15px;
	}
	.head .btn {
		margin-left: auto;
	}
	.btn.small {
		padding: 4px 10px;
		font-size: 12px;
	}
	.add {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		margin-top: 10px;
	}
	.add select {
		max-width: 100%;
	}
	ul {
		list-style: none;
		margin: 10px 0 0;
		padding: 0;
	}
	li {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 0;
	}
	li + li {
		border-top: 1px solid var(--border);
	}
	.tick {
		flex: none;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		border: 2px solid var(--border);
		box-sizing: border-box;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 11px;
		font-weight: 700;
	}
	.tick.on {
		background: var(--up);
		border-color: var(--up);
		color: #fff;
	}
	.as {
		font-size: 12px;
		min-width: 0;
	}
	.progress {
		margin-left: auto;
		font-size: 12px;
		color: var(--muted);
	}
</style>

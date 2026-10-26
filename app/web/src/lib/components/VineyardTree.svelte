<script lang="ts">
	import { buildTree } from '#lib/vineyards.ts';
	import type { VineyardRow } from '#lib/vineyards.ts';

	interface Props {
		/** vineyards to show (already narrowed by search / ownership) */
		rows: VineyardRow[];
		picked: Set<number>;
		onpick: (ids: Set<number>) => void;
		/** clicking a vineyard's name: select it on the map */
		onfocus: (row: VineyardRow) => void;
		selectedId: number | null;
		/** expand everything (e.g. while searching) */
		expandAll: boolean;
	}

	let { rows, picked, onpick, onfocus, selectedId, expandAll }: Props = $props();

	let open = $state(new Set<string>());
	const tree = $derived(buildTree(rows));
	// Regions whose vineyards have no sub-region skip that level
	const flat = $derived(tree.length === 1 && tree[0].name === null);

	const isOpen = (key: string) => expandAll || open.has(key);
	function toggleOpen(key: string) {
		const next = new Set(open);
		next.has(key) ? next.delete(key) : next.add(key);
		open = next;
	}

	function pickState(list: VineyardRow[]) {
		const n = list.filter((r) => picked.has(r.id)).length;
		return { all: n > 0 && n === list.length, some: n > 0 && n < list.length, n };
	}

	function togglePick(list: VineyardRow[]) {
		const next = new Set(picked);
		const all = pickState(list).all;
		for (const r of list) all ? next.delete(r.id) : next.add(r.id);
		onpick(next);
	}

	// `indeterminate` only exists as a DOM property
	function indeterminate(node: HTMLInputElement, value: boolean) {
		node.indeterminate = value;
		return { update: (v: boolean) => (node.indeterminate = v) };
	}

	const owned = (list: VineyardRow[]) => list.reduce((n, r) => n + r.bottles, 0);
</script>

{#snippet group(key: string, label: string, list: VineyardRow[], depth: number)}
	{@const s = pickState(list)}
	{@const b = owned(list)}
	<div class="node" style:padding-left="{depth * 14}px">
		<button class="chev" class:open={isOpen(key)} onclick={() => toggleOpen(key)} aria-label="Expand">▸</button>
		<input type="checkbox" checked={s.all} use:indeterminate={s.some} onchange={() => togglePick(list)} />
		<button class="label" onclick={() => toggleOpen(key)}>{label}</button>
		<span class="count muted num">{s.n ? `${s.n}/` : ''}{list.length}</span>
		{#if b}<span class="badge num">{b}</span>{/if}
	</div>
{/snippet}

{#snippet leaves(list: VineyardRow[], depth: number)}
	{#each list as r (r.id)}
		<div class="node leaf" class:sel={selectedId === r.id} style:padding-left="{depth * 14 + 18}px">
			<input type="checkbox" checked={picked.has(r.id)} onchange={() => togglePick([r])} />
			<button class="label" onclick={() => onfocus(r)}>{r.name}</button>
			{#if r.bottles}<span class="badge num">{r.bottles}</span>{/if}
		</div>
	{/each}
{/snippet}

{#snippet villages(list: (typeof tree)[number]['villages'], depth: number)}
	{#each list as v (v.key)}
		{@render group(v.key, v.name ?? 'Other vineyards', v.rows, depth)}
		{#if isOpen(v.key)}{@render leaves(v.rows, depth + 1)}{/if}
	{/each}
{/snippet}

{#if flat}
	{@render villages(tree[0].villages, 0)}
{:else}
	{#each tree as s (s.key)}
		{@render group(s.key, s.name ?? 'No sub-region', s.rows, 0)}
		{#if isOpen(s.key)}{@render villages(s.villages, 1)}{/if}
	{/each}
{/if}

<style>
	.node {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 3px 4px;
		border-radius: 6px;
		font-size: 13px;
	}
	.node:hover {
		background: var(--surface-2);
	}
	.node.sel {
		background: var(--accent-soft);
	}
	.node input {
		margin: 0;
		accent-color: #4f772d;
	}
	.chev {
		width: 14px;
		border: none;
		background: none;
		padding: 0;
		color: var(--muted);
		cursor: pointer;
		font-size: 11px;
		transition: transform 0.12s;
	}
	.chev.open {
		transform: rotate(90deg);
	}
	.label {
		flex: 1;
		min-width: 0;
		border: none;
		background: none;
		padding: 2px 0;
		text-align: left;
		cursor: pointer;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.leaf .label {
		color: var(--text);
	}
	.count {
		font-size: 11px;
	}
	.badge {
		font-size: 11px;
		font-weight: 600;
		color: var(--gold);
		box-shadow: inset 0 0 0 1px var(--gold);
		border-radius: 8px;
		padding: 0 6px;
	}
</style>

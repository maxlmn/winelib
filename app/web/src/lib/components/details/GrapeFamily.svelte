<script lang="ts">
	/** A grape's family tree (VIVC's parentage), for a narrow column: a column per parent, its own parents stacked above
	 * it, the grape below; its offspring listed under. A grape in the list links to its page. */
	import type { Family, FamilyNode } from '#lib/api/grapes.ts';
	import { links } from '#lib/links.ts';

	let { name, family, vivc }: { name: string; family: Family; vivc?: { number: number; url: string } | null } = $props();

	const W = 134, H = 26, GAP = 12, STACK = 4, DROP = 24;
	const parents = $derived(family.parents);
	const grand = $derived(parents.flatMap((p) => p.parents));
	const stacked = $derived(Math.max(0, ...parents.map((p) => p.parents.length)));
	const width = $derived(Math.max(parents.length, 1) * (W + GAP) - GAP);
	const parentY = $derived(stacked ? stacked * (H + STACK) - STACK + DROP : 0);
	const selfY = $derived(parentY + H + DROP);
	const parentX = (i: number) => W / 2 + i * (W + GAP);
	const selfX = $derived(width / 2);
	// The stack sits on its parent: a parent with one known parent has it in the lower place
	const grandY = (p: Family['parents'][number], k: number) => (stacked - p.parents.length + k) * (H + STACK);

	const short = (s: string) => (s.length > 19 ? s.slice(0, 18) + '…' : s);
</script>

{#snippet box(n: FamilyNode, cx: number, y: number, self = false)}
	{#if n.id !== null && !self}
		<a href={links.grape(n.id)}>
			<rect x={cx - W / 2} y={y} width={W} height={H} rx="7" class="node link" />
			<text x={cx} y={y + H / 2 + 4} text-anchor="middle"><title>{n.name}</title>{short(n.name)}</text>
		</a>
	{:else}
		<rect x={cx - W / 2} y={y} width={W} height={H} rx="7" class="node" class:self class:unknown={n.id === null && !self} />
		<text x={cx} y={y + H / 2 + 4} text-anchor="middle" class:self-text={self}><title>{n.name}</title>{short(n.name)}</text>
	{/if}
{/snippet}

<section class="family card">
	<div class="top">
		<h2>Family</h2>
		{#if vivc}<a class="muted small" href={vivc.url} target="_blank" rel="noreferrer">VIVC no. {vivc.number} ↗</a>{/if}
	</div>
	{#if parents.length}
		<div class="tree">
			<svg viewBox="0 0 {width} {selfY + H}" width={width} style="max-width: 100%" role="img" aria-label="{name}'s parents">
				<!-- links: a stack to its parent, the parents to the grape -->
				{#each parents as p, i}
					{#if p.parents.length}
						<path d="M{parentX(i)},{parentY - DROP} L{parentX(i)},{parentY}" class="edge" />
					{/if}
					<path d="M{parentX(i)},{parentY + H} C{parentX(i)},{parentY + H + 12} {selfX},{selfY - 12} {selfX},{selfY}" class="edge" />
				{/each}
				{#each parents as p, i}
					{#each p.parents as gp, k}{@render box(gp, parentX(i), grandY(p, k))}{/each}
					{@render box(p, parentX(i), parentY)}
				{/each}
				{@render box({ name, id: null } as FamilyNode, selfX, selfY, true)}
			</svg>
		</div>
		{#if [...parents, ...grand].some((n) => n && n.id === null)}<p class="muted small legend">A dashed grape isn't in your list.</p>{/if}
	{:else}
		<p class="muted small">VIVC gives no parents for {name}.</p>
	{/if}
	{#if family.offspring.length}
		<div class="offspring">
			<span class="muted small">Offspring ({family.offspring.length})</span>
			<div class="chips">
				{#each family.offspring as o (o.name)}
					{#if o.id !== null}<a class="chip" href={links.grape(o.id)}>{o.name}</a>{:else}<span class="chip muted">{o.name}</span>{/if}
				{/each}
			</div>
		</div>
	{/if}
</section>

<style>
	.family {
		padding: 16px 18px;
		margin-bottom: 14px;
	}
	.top {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 12px;
	}
	h2 {
		margin: 0 0 12px;
		font-size: 15px;
	}
	.tree {
		overflow-x: auto;
		display: flex;
		justify-content: center;
	}
	.node {
		fill: var(--surface-2);
		stroke: var(--border);
	}
	.node.link {
		fill: var(--surface);
		stroke: var(--accent);
		cursor: pointer;
	}
	a:hover .node.link {
		fill: color-mix(in srgb, var(--accent) 12%, var(--surface));
	}
	.node.self {
		fill: var(--accent);
		stroke: var(--accent);
	}
	.node.unknown {
		stroke-dasharray: 3 3;
	}
	text {
		font-size: 11px;
		fill: var(--text);
		pointer-events: none;
	}
	text.self-text {
		fill: white;
		font-weight: 600;
	}
	.edge {
		fill: none;
		stroke: var(--border);
		stroke-width: 1.5;
	}
	.legend {
		margin: 8px 0 0;
		text-align: center;
	}
	.offspring {
		margin-top: 14px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		margin-top: 6px;
	}
	.chip {
		padding: 1px 9px;
		border-radius: 10px;
		background: var(--surface-2);
		border: 1px solid var(--border);
		font-size: 12px;
	}
	a.chip:hover {
		border-color: var(--accent);
	}
</style>

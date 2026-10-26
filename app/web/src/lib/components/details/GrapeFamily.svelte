<script lang="ts">
	/** A grape's family tree (VIVC's parentage): its grandparents, parents and itself drawn as a tree, its
	 * offspring listed below. A grape in the list links to its page. */
	import type { Family, FamilyNode } from '#lib/api/grapes.ts';
	import { links } from '#lib/links.ts';

	let { name, family, vivc }: { name: string; family: Family; vivc?: { number: number; url: string } | null } = $props();

	const W = 150, H = 30, GAP = 14, ROW = 62;
	// The rows, top down: grandparents (two per parent, or a blank), parents, the grape
	const parents = $derived(family.parents);
	const grand = $derived(parents.flatMap((p) => [p.parents[0] ?? null, p.parents[1] ?? null]));
	const hasGrand = $derived(grand.some(Boolean));
	const cols = $derived(Math.max(hasGrand ? grand.length : parents.length * 2, 2));
	const width = $derived(cols * W + (cols - 1) * GAP);
	const x = (i: number, n: number) => ((i + 0.5) * width) / n;
	const rows = $derived(hasGrand ? 3 : 2);
	const height = $derived(rows * ROW - (ROW - H));
	const yOf = (row: number) => row * ROW;
	// node positions
	const grandX = $derived(grand.map((_, i) => x(i, grand.length)));
	const parentX = $derived(parents.map((_, i) => (hasGrand ? (grandX[2 * i] + grandX[2 * i + 1]) / 2 : x(i, parents.length))));
	const selfX = $derived(parentX.length ? parentX.reduce((a, b) => a + b, 0) / parentX.length : width / 2);
	const parentRow = $derived(hasGrand ? 1 : 0);
	const selfRow = $derived(parentRow + 1);

	const short = (s: string) => (s.length > 20 ? s.slice(0, 19) + '…' : s);
</script>

{#snippet box(n: FamilyNode | null, cx: number, row: number, self = false)}
	{#if n}
		{@const y = yOf(row)}
		{#if n.id !== null && !self}
			<a href={links.grape(n.id)}>
				<rect x={cx - W / 2} y={y} width={W} height={H} rx="7" class="node link" />
				<text x={cx} y={y + H / 2 + 4} text-anchor="middle"><title>{n.name}</title>{short(n.name)}</text>
			</a>
		{:else}
			<rect x={cx - W / 2} y={y} width={W} height={H} rx="7" class="node" class:self class:unknown={n.id === null && !self} />
			<text x={cx} y={y + H / 2 + 4} text-anchor="middle" class:self-text={self}><title>{n.name}</title>{short(n.name)}</text>
		{/if}
	{/if}
{/snippet}

<section class="family card">
	<div class="top">
		<h2>Family</h2>
		{#if vivc}<a class="muted small" href={vivc.url} target="_blank" rel="noreferrer">VIVC no. {vivc.number} ↗</a>{/if}
	</div>
	{#if parents.length}
		<div class="tree">
			<svg viewBox="0 0 {width} {height}" width={width} style="max-width: 100%" role="img" aria-label="{name}'s parents">
				<!-- links: grandparents to parents, parents to the grape -->
				{#if hasGrand}
					{#each grand as gp, i}
						{#if gp}
							{@const px = parentX[Math.floor(i / 2)]}
							<path d="M{grandX[i]},{yOf(0) + H} C{grandX[i]},{yOf(0) + H + 16} {px},{yOf(1) - 16} {px},{yOf(1)}" class="edge" />
						{/if}
					{/each}
				{/if}
				{#each parentX as px}
					<path d="M{px},{yOf(parentRow) + H} C{px},{yOf(parentRow) + H + 16} {selfX},{yOf(selfRow) - 16} {selfX},{yOf(selfRow)}" class="edge" />
				{/each}
				{#if hasGrand}
					{#each grand as gp, i}{@render box(gp, grandX[i], 0)}{/each}
				{/if}
				{#each parents as p, i}{@render box(p, parentX[i], parentRow)}{/each}
				{@render box({ name, id: null }, selfX, selfRow, true)}
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
		margin-top: 16px;
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
		font-size: 12px;
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

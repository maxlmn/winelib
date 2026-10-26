<script lang="ts">
	/** Every known parent → offspring link between the grapes, as a network (laid out by a small force simulation).
	 * Colour: the berries'; size: your wines; a gold ring: in the cellar. A parent not in the list is a hollow dot.
	 * Hover a grape to see its family, click it for its page, wheel to zoom, drag to pan. */
	import { goto } from '$app/navigation';
	import { BERRY_COLORS } from '#lib/api/grapes.ts';
	import type { GrapeRow } from '#lib/api/grapes.ts';
	import { links } from '#lib/links.ts';

	let { rows, shown }: { rows: GrapeRow[]; /** the grapes the filters keep (null: all); a relative of one of them
	 * that they leave out is a hollow dot */ shown: Set<number> | null } = $props();

	interface Node {
		key: string;
		name: string;
		id: number | null;
		/** not drawn as a grape of the list: not in it, or left out by the filters (a relative of one that's in) */
		out: boolean;
		color: string | null;
		wines: number;
		bottles: number;
		x: number;
		y: number;
		vx: number;
		vy: number;
		degree: number;
	}

	const graph = $derived.by(() => {
		const nodes = new Map<string, Node>();
		const byId = new Map(rows.map((r) => [r.id, r]));
		const keep = (id: number | null) => id !== null && (shown === null || shown.has(id));
		const node = (key: string, name: string, r: GrapeRow | null): Node => {
			let n = nodes.get(key);
			if (!n) {
				n = { key, name, id: r?.id ?? null, out: !keep(r?.id ?? null), color: r?.color ?? null, wines: r?.wines ?? 0,
					bottles: r?.bottles ?? 0, x: 0, y: 0, vx: 0, vy: 0, degree: 0 };
				nodes.set(key, n);
			}
			return n;
		};
		const edges: { from: Node; to: Node }[] = [];
		for (const r of rows) {
			r.parents.forEach((p, i) => {
				const pid = r.parent_ids[i];
				// A link the filters leave out at both ends isn't drawn
				if (!keep(r.id) && !(pid !== null && keep(pid))) return;
				const parent = pid !== null && byId.has(pid) ? node(`#${pid}`, byId.get(pid)!.name, byId.get(pid)!) : node(`?${p.toLowerCase()}`, p, null);
				const child = node(`#${r.id}`, r.name, r);
				if (parent === child) return;
				parent.degree++;
				child.degree++;
				edges.push({ from: parent, to: child });
			});
		}
		const list = [...nodes.values()];
		layout(list, edges);
		return { nodes: list, edges };
	});

	/** A force layout: nodes repel, links pull, everything drifts to the centre. Seeded on a circle (by name), so the
	 * same data always gives the same picture. */
	function layout(nodes: Node[], edges: { from: Node; to: Node }[]) {
		const sorted = [...nodes].sort((a, b) => a.name.localeCompare(b.name));
		sorted.forEach((n, i) => {
			const a = (i / sorted.length) * Math.PI * 2;
			n.x = Math.cos(a) * 300 * (0.6 + ((i * 7) % 10) / 25);
			n.y = Math.sin(a) * 300 * (0.6 + ((i * 7) % 10) / 25);
		});
		const big = Math.min(1, Math.sqrt(60 / Math.max(nodes.length, 1))); // 1 for a small network, less for hundreds
		for (let step = 0, heat = 1; step < 320; step++, heat *= 0.988) {
			for (let i = 0; i < nodes.length; i++) {
				const a = nodes[i];
				for (let j = i + 1; j < nodes.length; j++) {
					const b = nodes[j];
					let dx = a.x - b.x, dy = a.y - b.y;
					const d2 = Math.max(dx * dx + dy * dy, 25);
					if (d2 > 40000) continue;
					const f = 900 / big / d2;
					dx *= f;
					dy *= f;
					a.vx += dx;
					a.vy += dy;
					b.vx -= dx;
					b.vy -= dy;
				}
			}
			for (const { from, to } of edges) {
				const dx = to.x - from.x, dy = to.y - from.y;
				const d = Math.sqrt(dx * dx + dy * dy) || 1;
				const f = ((d - 40) / d) * 0.08;
				from.vx += dx * f;
				from.vy += dy * f;
				to.vx -= dx * f;
				to.vy -= dy * f;
			}
			for (const n of nodes) {
				n.vx -= n.x * 0.02 * big;
				n.vy -= n.y * 0.02 * big;
				const v = Math.sqrt(n.vx * n.vx + n.vy * n.vy), cap = 30 * heat;
				if (v > cap) {
					n.vx *= cap / v;
					n.vy *= cap / v;
				}
				n.x += n.vx;
				n.y += n.vy;
				n.vx *= 0.55;
				n.vy *= 0.55;
			}
		}
	}

	// in pixels: a log scale, so the grapes of hundreds of wines stay dots (14 at most)
	const radius = (n: Node) => (n.out ? 3.5 : Math.min(14, 4 + 1.2 * Math.log2(1 + n.wines)));
	const bounds = $derived.by(() => {
		const xs = graph.nodes.map((n) => n.x), ys = graph.nodes.map((n) => n.y);
		const pad = 40;
		return { x: Math.min(...xs) - pad, y: Math.min(...ys) - pad, w: Math.max(...xs) - Math.min(...xs) + 2 * pad, h: Math.max(...ys) - Math.min(...ys) + 2 * pad };
	});

	// Pan and zoom: the view box, in graph units
	let zoom = $state(1);
	let pan = $state({ x: 0, y: 0 });
	const view = $derived({
		w: bounds.w / zoom,
		h: bounds.h / zoom,
		x: bounds.x + pan.x + (bounds.w - bounds.w / zoom) / 2,
		y: bounds.y + pan.y + (bounds.h - bounds.h / zoom) / 2
	});
	let svg: SVGSVGElement | undefined = $state();
	let wide = $state(1000), tall = $state(640); // the svg's size in pixels
	/** graph units per screen pixel (meet: the tighter of width and height) */
	const k = $derived(Math.max(view.w / (wide || 1), view.h / (tall || 1)));
	let drag: { x: number; y: number; px: number; py: number; moved: boolean } | null = null;

	function wheel(e: WheelEvent) {
		e.preventDefault();
		zoom = Math.min(8, Math.max(1, zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
		if (zoom === 1) pan = { x: 0, y: 0 };
	}
	function down(e: PointerEvent) {
		drag = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y, moved: false };
	}
	function move(e: PointerEvent) {
		if (!drag || !svg) return;
		const scale = view.w / svg.clientWidth;
		const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
		if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
		pan = { x: drag.px - dx * scale, y: drag.py - dy * scale };
	}
	function up(e: PointerEvent, n?: Node) {
		const clicked = drag && !drag.moved;
		drag = null;
		if (clicked && n?.id != null) goto(links.grape(n.id));
		e.stopPropagation();
	}

	// Hover: the grape, its links and its relatives stand out
	let hover: Node | null = $state.raw(null); // raw: the node itself, compared by identity
	const near = $derived.by(() => {
		if (!hover) return null;
		const s = new Set<Node>([hover]);
		for (const e of graph.edges) {
			if (e.from === hover) s.add(e.to);
			if (e.to === hover) s.add(e.from);
		}
		return s;
	});
	const dim = (n: Node) => near !== null && !near.has(n);
	// Names: the hovered grape's family; else the well-connected and those you drink most; all of them zoomed in
	const labelled = (n: Node) => (near ? near.has(n) : !n.out && (zoom >= 2.5 || n.degree >= 5 || n.wines >= 15 || (zoom >= 1.5 && (n.degree >= 3 || n.bottles > 0))));
</script>

{#if graph.edges.length}
	<div class="net">
		<div class="frame" bind:clientWidth={wide} bind:clientHeight={tall}>
		<svg
			bind:this={svg}
			viewBox="{view.x} {view.y} {view.w} {view.h}"
			role="img"
			aria-label="The grapes' parent and offspring links"
			onwheel={wheel}
			onpointerdown={down}
			onpointermove={move}
			onpointerup={(e) => up(e)}
			onpointerleave={() => (drag = null)}
		>
			<defs>
				<marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerUnits="userSpaceOnUse" markerWidth={6 * k} markerHeight={6 * k} orient="auto-start-reverse">
					<path d="M0,0 L10,5 L0,10 z" class="tip" />
				</marker>
			</defs>
			{#each graph.edges as e (e.from.key + '>' + e.to.key)}
				{@const dx = e.to.x - e.from.x}
				{@const dy = e.to.y - e.from.y}
				{@const d = Math.sqrt(dx * dx + dy * dy) || 1}
				{@const r = (radius(e.to) + 1.5) * k}
				<line
					x1={e.from.x}
					y1={e.from.y}
					x2={e.to.x - (dx / d) * r}
					y2={e.to.y - (dy / d) * r}
					class="edge"
					class:on={hover && (e.from === hover || e.to === hover)}
					class:dim={near !== null && !(e.from === hover || e.to === hover)}
					marker-end="url(#arrow)"
				/>
			{/each}
			{#each graph.nodes as n (n.key)}
				<g
					class="node"
					class:dim={dim(n)}
					class:link={n.id !== null}
					transform="translate({n.x},{n.y})"
					role="link"
					tabindex="-1"
					onpointerenter={() => (hover = n)}
					onpointerleave={() => (hover = null)}
					onpointerup={(e) => up(e, n)}
				>
					{#if n.bottles && !n.out}<circle r={(radius(n) + 2.5) * k} class="ring" />{/if}
					<circle r={radius(n) * k} class:ghost={n.out} class:uncoloured={!n.out && !BERRY_COLORS[n.color ?? '']} style:fill={n.out ? null : (BERRY_COLORS[n.color ?? ''] ?? null)} />
					<title>{n.name}{n.id === null ? ' (not in your list)' : n.out ? ' (left out by the filters)' : n.wines ? ` · ${n.wines} wines` : ''}</title>
				</g>
			{/each}
			<!-- The names above everything, so no dot or link covers one -->
			{#each graph.nodes as n (n.key)}
				{#if labelled(n)}
					<text x={n.x} y={n.y - (radius(n) + 5) * k} font-size={(radius(n) > 8 ? 12 : 11) * k} stroke-width={4 * k}
						text-anchor="middle" class="label" class:strong={n === hover || radius(n) > 8} class:dim={dim(n)}>{n.name}</text>
				{/if}
			{/each}
		</svg>
		</div>
		<div class="legend muted small">
			{#each Object.entries(BERRY_COLORS) as [c, col] (c)}<span><i style:background={col}></i>{c}</span>{/each}
			<span><i class="ring-key"></i>In the cellar</span>
			<span><i class="unknown-key"></i>Colour unknown</span>
			<span><i class="ghost-key"></i>{shown ? 'Left out by the filters, or not in your list' : 'Not in your list'}</span>
			<span>Arrows: parent → offspring · size: your wines · wheel to zoom, drag to pan</span>
			{#if zoom > 1}<button class="reset" onclick={() => ((zoom = 1), (pan = { x: 0, y: 0 }))}>Reset view</button>{/if}
		</div>
	</div>
{:else}
	<p class="muted empty">No parentage known yet.</p>
{/if}

<style>
	.frame {
		height: min(70vh, 640px);
	}
	.net svg {
		display: block;
		width: 100%;
		height: 100%;
		cursor: grab;
		touch-action: none;
		user-select: none;
	}
	.edge {
		stroke: var(--border);
		stroke-width: 1.2;
		vector-effect: non-scaling-stroke;
	}
	.edge.on {
		stroke: var(--accent);
		stroke-width: 2;
	}
	.edge.dim {
		opacity: 0.25;
	}
	.tip {
		fill: var(--muted);
	}
	.node circle {
		stroke: var(--surface);
		stroke-width: 1;
		vector-effect: non-scaling-stroke;
	}
	.node.link {
		cursor: pointer;
	}
	.node circle.ghost {
		fill: var(--surface);
		stroke: var(--muted);
		stroke-dasharray: 2 2;
	}
	.node circle.uncoloured {
		fill: var(--surface-2);
		stroke: var(--muted);
	}
	.node circle.ring {
		fill: none;
		stroke: var(--gold, #c9a227);
		stroke-width: 2;
	}
	.node.dim {
		opacity: 0.2;
	}
	.label {
		fill: var(--text);
		paint-order: stroke;
		stroke: var(--surface);
		stroke-linejoin: round;
		pointer-events: none;
	}
	.label.strong {
		font-weight: 700;
	}
	.label.dim {
		opacity: 0.2;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 14px;
		padding: 8px 14px 12px;
		align-items: center;
	}
	.legend i {
		display: inline-block;
		width: 9px;
		height: 9px;
		border-radius: 50%;
		margin-right: 5px;
		vertical-align: 0;
	}
	.legend .ring-key {
		border: 2px solid var(--gold, #c9a227);
		width: 7px;
		height: 7px;
	}
	.legend .unknown-key {
		background: var(--surface-2);
		border: 1px solid var(--muted);
	}
	.legend .ghost-key {
		border: 1px dashed var(--muted);
	}
	.reset {
		border: none;
		background: none;
		color: var(--accent);
		cursor: pointer;
		padding: 0;
		font-size: inherit;
	}
	.empty {
		padding: 16px;
		margin: 0;
	}
</style>

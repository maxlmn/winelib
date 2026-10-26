<script lang="ts">
	import type { Bottle } from '#lib/types.ts';
	import { money as inMain } from '#lib/format.ts';
	import { groupOrder } from '#lib/settings.svelte.ts';

	/** Market value and bottle count by storage group, as two donuts sharing one colour per group. */
	// money: how to show an amount of the main currency (the cellar page's currency); the main currency by default
	let { bottles, money = inMain }: { bottles: Bottle[]; money?: (amount: number) => string } = $props();

	// Fixed categorical slots, in the settings' group order (validated for colour-blind separation, light and dark);
	// a 5th group and beyond share a neutral grey
	const SLOTS = 4;
	const order = $derived.by(() => {
		const known = groupOrder();
		const extra = [...new Set(bottles.map((b) => b.location_group))].filter((g) => !known.includes(g)).sort();
		return [...known, ...extra];
	});
	const slot = (group: string) => Math.min(order.indexOf(group), SLOTS) + 1;

	type Seg = { group: string; value: number; share: number; start: number };
	function segments(value: (b: Bottle) => number): Seg[] {
		const sums = new Map<string, number>();
		for (const b of bottles) sums.set(b.location_group, (sums.get(b.location_group) ?? 0) + value(b));
		const total = [...sums.values()].reduce((a, b) => a + b, 0);
		let start = 0;
		return order
			.filter((g) => (sums.get(g) ?? 0) > 0)
			.map((g) => {
				const v = sums.get(g)!;
				const seg = { group: g, value: v, share: total ? v / total : 0, start };
				start += seg.share;
				return seg;
			});
	}

	const charts = $derived([
		{ title: 'Market value by storage', segs: segments((b) => b.qty * b.market_base), fmt: (v: number) => money(v) },
		{ title: 'Bottles by storage', segs: segments((b) => b.qty), fmt: (v: number) => `${Math.round(v)}` }
	]);

	let hover = $state<string | null>(null);

	const R = 42;
	const C = 2 * Math.PI * R;
	const GAP = 2; // surface gap between segments, in arc length
</script>

<div class="donuts">
	{#each charts as chart}
		{@const total = chart.segs.reduce((a, s) => a + s.value, 0)}
		{@const focus = chart.segs.find((s) => s.group === hover)}
		<figure>
			<figcaption class="muted">{chart.title}</figcaption>
			<div class="body">
				<svg viewBox="0 0 100 100" role="img" aria-label="{chart.title}: {chart.segs.map((s) => `${s.group} ${chart.fmt(s.value)}`).join(', ')}">
					<circle class="track" cx="50" cy="50" r={R} />
					{#each chart.segs as s (s.group)}
						{@const len = Math.max(s.share * C - (chart.segs.length > 1 ? GAP : 0), 0.5)}
						<circle
							class="seg s{slot(s.group)}"
							class:dim={hover && hover !== s.group}
							cx="50"
							cy="50"
							r={R}
							stroke-dasharray="{len} {C - len}"
							stroke-dashoffset={-s.start * C}
							role="presentation"
							onmouseenter={() => (hover = s.group)}
							onmouseleave={() => (hover = null)}
						>
							<title>{s.group}: {chart.fmt(s.value)} ({(s.share * 100).toFixed(1)}%)</title>
						</circle>
					{/each}
					<text x="50" y="49" class="center num">{focus ? `${(focus.share * 100).toFixed(0)}%` : chart.fmt(total)}</text>
					<text x="50" y="61" class="center sub">{focus ? focus.group : 'total'}</text>
				</svg>
				<ul>
					{#each chart.segs as s (s.group)}
						<li class:dim={hover && hover !== s.group} onmouseenter={() => (hover = s.group)} onmouseleave={() => (hover = null)}>
							<span class="key s{slot(s.group)}"></span>
							<span class="name">{s.group}</span>
							<span class="num">{chart.fmt(s.value)}</span>
							<span class="num muted pct">{(s.share * 100).toFixed(0)}%</span>
						</li>
					{/each}
				</ul>
			</div>
		</figure>
	{/each}
</div>

<style>
	.donuts {
		--s1: #2a78d6;
		--s2: #eb6834;
		--s3: #1baf7a;
		--s4: #eda100;
		--s5: #9a9893;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr));
		gap: 12px 28px;
	}
	:global(:root[data-theme='dark']) .donuts {
		--s1: #3987e5;
		--s2: #d95926;
		--s3: #199e70;
		--s4: #c98500;
		--s5: #77757a;
	}
	figure {
		margin: 0;
	}
	figcaption {
		font-size: 12px;
		margin-bottom: 6px;
	}
	.body {
		display: flex;
		align-items: center;
		gap: 16px;
	}
	svg {
		width: 110px;
		height: 110px;
		flex: none;
		transform: rotate(-90deg);
	}
	.track {
		fill: none;
		stroke: var(--surface-2);
		stroke-width: 14;
	}
	.seg {
		fill: none;
		stroke-width: 14;
		transition: opacity 0.15s;
	}
	.s1 {
		stroke: var(--s1);
		background: var(--s1);
	}
	.s2 {
		stroke: var(--s2);
		background: var(--s2);
	}
	.s3 {
		stroke: var(--s3);
		background: var(--s3);
	}
	.s4 {
		stroke: var(--s4);
		background: var(--s4);
	}
	.s5 {
		stroke: var(--s5);
		background: var(--s5);
	}
	.dim {
		opacity: 0.35;
	}
	.center {
		transform: rotate(90deg);
		transform-origin: 50px 50px;
		text-anchor: middle;
		fill: var(--text);
		font-size: 11px;
		font-weight: 650;
	}
	.center.sub {
		font-size: 8px;
		font-weight: 400;
		fill: var(--muted);
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		flex: 1;
		min-width: 0;
		font-size: 13px;
	}
	li {
		display: grid;
		grid-template-columns: 10px minmax(0, 1fr) auto 2.6em;
		align-items: center;
		gap: 8px;
		padding: 3px 0;
		transition: opacity 0.15s;
	}
	.key {
		width: 10px;
		height: 10px;
		border-radius: 3px;
	}
	.name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.pct {
		text-align: right;
	}
</style>

<script lang="ts">
	import type { RegionColors } from '#lib/types.ts';
	import { plural } from '#lib/format.ts';
	import OccasionCard from './OccasionCard.svelte';
	import ShowMore from './ShowMore.svelte';
	import { fmtMonth } from './journal.ts';
	import type { Occasion } from './journal.ts';

	let { occasions, regionColors, inline }: { occasions: Occasion[]; regionColors: RegionColors; inline: boolean } = $props();

	const STEP = 40;
	let limit = $state(STEP);
	// Back to the first step when the filters change the list, not on every URL change (e.g. toggling notes)
	const listKey = $derived(`${occasions.length}|${occasions[0]?.key}|${occasions.at(-1)?.key}`);
	$effect(() => {
		void listKey;
		limit = STEP;
	});

	// Month sections over the cards rendered so far, with the month's totals over all of them. Within a month,
	// grouped by month, then by day (newest first)
	const months = $derived.by(() => {
		const totals = new Map<string, { wines: number; occasions: number }>();
		for (const o of occasions) {
			const t = totals.get(o.date.slice(0, 7)) ?? { wines: 0, occasions: 0 };
			t.wines += o.wines.length;
			t.occasions += 1;
			totals.set(o.date.slice(0, 7), t);
		}
		const sections: { month: string; days: Occasion[][]; wines: number; occasions: number }[] = [];
		for (const o of occasions.slice(0, limit)) {
			const m = o.date.slice(0, 7);
			if (sections.at(-1)?.month !== m) sections.push({ month: m, days: [], ...totals.get(m)! });
			const days = sections.at(-1)!.days;
			if (days.at(-1)?.[0].date === o.date) days.at(-1)!.push(o);
			else days.push([o]);
		}
		return sections;
	});
</script>

{#each months as s (s.month)}
	<section>
		<h3>{fmtMonth(s.month)} <span class="muted num">{plural(s.wines, 'wine')} · {plural(s.occasions, 'occasion')}</span></h3>
		<div class="cards">
			{#each s.days.flat() as o (o.key)}
				<OccasionCard occasion={o} {regionColors} {inline} />
			{/each}
		</div>
	</section>
{/each}
<ShowMore shown={Math.min(limit, occasions.length)} total={occasions.length} step={STEP} onmore={() => (limit += STEP)} />

<style>
	section + section {
		margin-top: 22px;
	}
	h3 {
		font-size: 14px;
		margin: 0 0 10px;
		display: flex;
		align-items: baseline;
		gap: 10px;
	}
	h3 span {
		font-size: 12px;
		font-weight: 400;
	}
	/* A month's occasions in two columns, newest first, left to right (each card says its day). One column on
	   narrow screens */
	.cards {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 12px;
		align-items: start;
	}
	@media (max-width: 900px) {
		.cards {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>

<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { activeCount, filterLocations, filterWines, fromParams, toParams, emptyFilters } from '#lib/filters.ts';
	import { links } from '#lib/links.ts';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import { formatName, wineList } from '#lib/wineList.ts';

	let { data } = $props();

	// Everything lives in the URL, like the cellar's filters: a list can be bookmarked and made again
	const params = $derived(page.url.searchParams);
	const filters = $derived(fromParams(params));
	const title = $derived(params.get('title') ?? 'Wine list');
	const today = new Date().toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
	const subtitle = $derived(params.get('sub') ?? today);
	const leftOut = $derived(new Set(params.getAll('x')));
	const ends = $derived(params.get('ends') !== '0');
	const grapes = $derived(params.get('grapes') === '1');

	const bottles = $derived(filterLocations(filterWines(data.cellar.bottles, filters), filters));
	const sections = $derived(wineList(bottles, leftOut));
	const count = $derived(sections.flatMap((s) => s.regions.flatMap((r) => r.appellations.flatMap((a) => a.lines))).length);
	const filtered = $derived(activeCount(filters) > 0);

	function set(change: (p: URLSearchParams) => void) {
		const p = new URLSearchParams(params.toString());
		change(p);
		goto(`?${p}`, { replace: true, reset: false });
	}
	const setText = (key: string, value: string, fallback: string) =>
		set((p) => (value === fallback ? p.delete(key) : p.set(key, value)));
	const leaveOut = (keys: string[]) => set((p) => keys.forEach((k) => p.append('x', k)));
	const putBack = () => set((p) => p.delete('x'));
	const wholeCellar = () => goto(`?${toParams(emptyFilters(), params)}`, { replace: true, reset: false });
	// Back to the cellar with the same filters, to change the selection
	const cellarHref = $derived(`${links.cellar()}?${toParams(filters)}`);
</script>

<svelte:head><title>{title} · WineLib</title></svelte:head>

<div class="page-head no-print">
	<h1>Wine list</h1>
	<button class="btn primary" onclick={() => window.print()} disabled={!count}>Print or save as PDF</button>
</div>

<div class="controls card no-print">
	<label>
		<span class="label">Title</span>
		<input value={title} onchange={(e) => setText('title', e.currentTarget.value, 'Wine list')} />
	</label>
	<label>
		<span class="label">Under the title</span>
		<input value={subtitle} onchange={(e) => setText('sub', e.currentTarget.value, today)} placeholder="Nothing" />
	</label>
	<div class="toggles">
		<label class="check"><input type="checkbox" checked={ends} onchange={(e) => set((p) => (e.currentTarget.checked ? p.delete('ends') : p.set('ends', '0')))} /> Bottle ends</label>
		<label class="check"><input type="checkbox" checked={grapes} onchange={(e) => set((p) => (e.currentTarget.checked ? p.set('grapes', '1') : p.delete('grapes')))} /> Grapes</label>
	</div>
	<p class="muted scope">
		{#if filtered}
			The wines matching the <a href={cellarHref}>cellar's filters</a> · <button class="link" onclick={wholeCellar}>the whole cellar</button>
		{:else}
			The whole cellar · <a href={links.cellar()}>filter it in the cellar</a> to make a selection
		{/if}
		{#if leftOut.size}
			· {leftOut.size} left out, <button class="link" onclick={putBack}>put back</button>
		{/if}
		<br />Leave a wine out with its ✕, a vintage by clicking it. On a phone, print from the share menu.
	</p>
</div>

<article class="sheet" class:ends>
	<header>
		<h1>{title}</h1>
		{#if subtitle}<p class="subtitle">{subtitle}</p>{/if}
	</header>
	{#if !count}
		<p class="empty">No wines on this list.</p>
	{/if}
	{#each sections as section (section.title)}
		<section>
			<h2>{section.title}</h2>
			{#each section.regions as r (r.region)}
				<div class="region">
					<h3>{r.region || 'No region'}{#if regionLabel(r.region) !== r.region}<span class="country">{regionLabel(r.region).slice(r.region.length + 2)}</span>{/if}</h3>
					{#each r.appellations as a (a.appellation)}
						<!-- the appellation's name, unless it's the region's own (Champagne in Champagne) -->
						{#if a.appellation && a.appellation !== r.region}<h4>{a.appellation}</h4>{/if}
						{#each a.lines as l (l.key)}
							<div class="line">
								{#if ends}<span class="end"><BottleEnd region={data.regionColors[r.region]} color={l.color} format={l.format} size={9} /></span>{/if}
								<div class="wine">
									<span class="producer">{l.producer}</span>{#if l.cuvee}<span class="cuvee">{l.cuvee}</span>{/if}{#if formatName(l.format)}<span class="format">{formatName(l.format)}</span>{/if}{#if grapes && l.grapes.length}<span class="grapes">{l.grapes.join(', ')}</span>{/if}
								</div>
								<div class="vintages">
									{#each l.vintages as v, i (v.key)}{#if i}<span class="sep">·</span>{/if}<button class="vintage" title="Leave {v.vintage} out" onclick={() => leaveOut([v.key])}>{v.vintage}</button>{/each}
								</div>
								<button class="out no-print" title="Leave out of the list" aria-label="Leave {l.producer} {l.cuvee} out" onclick={() => leaveOut(l.vintages.map((v) => v.key))}>✕</button>
							</div>
						{/each}
					{/each}
				</div>
			{/each}
		</section>
	{/each}
</article>

<style>
	.controls {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr));
		gap: 10px 14px;
		padding: 14px 16px;
		margin-bottom: 18px;
		align-items: end;
	}
	.controls label {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.label {
		font-size: 12px;
		color: var(--muted);
	}
	.controls input:not([type]) {
		padding: 7px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
	}
	.toggles {
		display: flex;
		gap: 16px;
		padding-bottom: 7px;
	}
	.controls label.check {
		flex-direction: row;
		align-items: center;
		gap: 6px;
	}
	.scope {
		grid-column: 1 / -1;
		margin: 0;
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

	/* The sheet is paper, whatever the theme: dark ink on white, like the printed page */
	.sheet {
		--ink: #221d1a;
		--ink-soft: #7a716b;
		--rule: #d9d3cd;
		max-width: 210mm;
		margin: 0 auto;
		padding: 20mm 18mm;
		background: #fff;
		color: var(--ink);
		box-shadow: var(--shadow), 0 0 0 1px var(--border);
		border-radius: 4px;
		font-family: 'Iowan Old Style', 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif;
		font-size: 10.5pt;
		line-height: 1.35;
		color-scheme: light;
	}
	header {
		text-align: center;
		margin-bottom: 12mm;
	}
	.sheet h1 {
		font-family: inherit;
		font-size: 26pt;
		font-weight: 400;
		letter-spacing: 0.04em;
		margin: 0;
	}
	.subtitle {
		margin: 4px 0 0;
		color: var(--ink-soft);
		font-style: italic;
	}
	header::after {
		content: '';
		display: block;
		width: 28mm;
		height: 1px;
		margin: 6mm auto 0;
		background: var(--rule);
	}
	section + section {
		margin-top: 9mm;
	}
	h2 {
		font-family: inherit;
		font-size: 11pt;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.22em;
		text-align: center;
		margin: 0 0 4mm;
		break-after: avoid;
	}
	.region + .region {
		margin-top: 5mm;
	}
	h3 {
		font-family: inherit;
		font-size: 10.5pt;
		font-weight: 400;
		font-variant: small-caps;
		letter-spacing: 0.06em;
		border-bottom: 1px solid var(--rule);
		padding-bottom: 1mm;
		margin: 0 0 2mm;
		break-after: avoid;
	}
	.country {
		color: var(--ink-soft);
		margin-left: 0.5em;
	}
	h4 {
		font-family: inherit;
		font-size: 9.5pt;
		font-weight: 400;
		font-style: italic;
		color: var(--ink-soft);
		margin: 2.5mm 0 0.5mm;
		break-after: avoid;
	}
	.line {
		position: relative;
		display: flex;
		align-items: baseline;
		gap: 3mm;
		padding: 0.8mm 0;
		break-inside: avoid;
	}
	.end {
		flex: none;
		width: 4mm;
		display: flex;
		justify-content: center;
		align-self: center;
		margin-top: -0.5mm;
	}
	.wine {
		flex: 1;
		min-width: 0;
	}
	.producer {
		font-weight: 600;
	}
	.cuvee::before {
		content: ' · ';
		color: var(--ink-soft);
	}
	.format,
	.grapes {
		color: var(--ink-soft);
		margin-left: 0.6em;
	}
	.format {
		font-variant: small-caps;
	}
	.grapes {
		font-style: italic;
		font-size: 9.5pt;
	}
	.vintages {
		flex: none;
		max-width: 45%;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.sep {
		color: var(--ink-soft);
		margin: 0 0.35em;
	}
	.vintage {
		border: none;
		background: none;
		padding: 0;
		font: inherit;
		color: inherit;
		cursor: pointer;
	}
	.vintage:hover {
		text-decoration: line-through;
		color: var(--ink-soft);
	}
	.out {
		position: absolute;
		right: -9mm;
		top: 1mm;
		border: none;
		background: none;
		color: var(--ink-soft);
		cursor: pointer;
		opacity: 0;
		padding: 2px 6px;
	}
	.line:hover .out,
	.out:focus-visible {
		opacity: 1;
	}
	@media (hover: none) {
		.out {
			opacity: 0.6;
		}
	}
	.empty {
		text-align: center;
		color: var(--ink-soft);
	}
	@media (max-width: 760px) {
		.sheet {
			padding: 10mm 9mm;
			font-size: 10pt;
		}
		.out {
			right: -7mm;
		}
	}
	@media print {
		.no-print {
			display: none !important;
		}
		.sheet {
			max-width: none;
			padding: 0;
			box-shadow: none;
			border-radius: 0;
		}
	}
</style>

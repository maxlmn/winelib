<script lang="ts">
	import { tick, untrack } from 'svelte';
	import ActionMenu from '#lib/components/ActionMenu.svelte';
	import CriticPills from '#lib/components/CriticPills.svelte';
	import PlaceName from '#lib/components/PlaceName.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import HomeMap from '#lib/components/home/HomeMap.svelte';
	import NoteBox from '#lib/components/tastings/NoteBox.svelte';
	import NoteText from '#lib/components/tastings/NoteText.svelte';
	import { saveEveningNote } from '#lib/api/forms.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { plural, money } from '#lib/format.ts';
	import { labelThumb } from '#lib/pips.ts';
	import { labelTip } from '#lib/labelTip.svelte.ts';
	import OccasionPhoto from '#lib/components/tastings/OccasionPhoto.svelte';
	import { fmtDay, stars, wineName } from '#lib/components/tastings/journal.ts';
	import ShareSticker from '#lib/components/tastings/ShareSticker.svelte';
	import { fmtDate } from '#lib/components/details/wine.ts';

	let { data } = $props();

	// The evening's page: where and when, then each wine poured in order with its note (written here, saved as you
	// type), the tasting opened marked, the evening's photo; over the map: the place (else the opened wine), a wine
	// picked flies it to where the wine comes from
	const t = $derived(data.tasting);
	const w = $derived(t.wine);
	const b = $derived(t.bottle);
	const price = $derived(
		b.price_base ? `${money(b.price_base)}${b.currency && b.currency !== appSettings.currency ? ` (${b.price} ${b.currency})` : ''}` : null
	);
	// the opened tasting's bottle (its size, vendor, price, date: a link to it)
	const bottleLine = $derived([b.format, b.vendor, price, b.purchase_date && `bought ${fmtDate(b.purchase_date)}`].filter(Boolean).join(' · '));
	const where = $derived<[number, number] | null>(t.place?.lat != null && t.place?.lng != null ? [t.place.lng, t.place.lat] : null);
	const placeName = $derived(t.place?.name ?? t.location ?? 'Unknown');

	// the wine on the map: none picked, the place (else the opened wine)
	let picked = $state<{ wine_id: number; region: string | null } | null>(null);
	$effect(() => {
		void t.id;
		untrack(() => (picked = null));
	});
	const focus = $derived(
		picked ? { wineId: picked.wine_id, region: picked.region } : where ? { point: where } : { wineId: w.id, region: w.region }
	);
	let pickTimer: ReturnType<typeof setTimeout> | undefined;
	function pick(o: { wine_id: number; region?: string | null }, wait = 0) {
		clearTimeout(pickTimer);
		const go = () => (picked = { wine_id: o.wine_id, region: o.region ?? null });
		if (wait) pickTimer = setTimeout(go, wait);
		else go();
	}

	// notes shown as text; tapped (or "Add a note"), a box to write in, back to text when left. `written`: the notes
	// saved here since the page loaded (its data has the ones before)
	// the evening's own note (the menu, who came): 0 in `writing` when opened
	const EVENING = 0;
	let writing = $state<number | null>(null);
	let written = $state<Record<number, string>>({});
	$effect(() => {
		void t.id;
		untrack(() => {
			writing = null;
			written = {};
		});
	});
	const write = (id: number) => (writing = id);
	const wrote = (id: number) => (text: string) => {
		written = { ...written, [id]: text };
		if (writing === id) writing = null;
	};
	const evening = $derived(written[EVENING] ?? t.evening?.notes ?? '');
	const noteOf = (o: { id: number; notes?: string | null }) => written[o.id] ?? o.notes ?? '';

	// the opened tasting scrolled to when it's down the evening
	$effect(() => {
		const id = t.id;
		if (t.occasion.findIndex((o) => o.id === id) < 2) return;
		// (after the map has laid the page out: on a phone the cards start under it)
		let timer: ReturnType<typeof setTimeout> | undefined;
		// (the window scrolled, not the app's frame: scrollIntoView moved that too)
		const show = () => {
			const el = document.getElementById(`wine-${id}`);
			if (!el) return;
			const r = el.getBoundingClientRect();
			window.scrollTo({ top: Math.max(0, window.scrollY + r.top - (window.innerHeight - r.height) / 2), behavior: 'smooth' });
		};
		void tick().then(() => (timer = setTimeout(show, 350)));
		return () => clearTimeout(timer);
	});

	// For the share sticker: this wine and your note, the evening's wines in order (no score: the journal's 90 is a
	// default, not one)
	const sticker = $derived({
		wine: { producer: w.producer, cuvee: w.cuvee, vintage: w.vintage, color: w.color, region: w.region, appellation: w.appellation?.name ?? null, notes: t.notes },
		session: t.occasion.map((o) => ({ producer: o.producer, cuvee: o.cuvee, vintage: o.vintage, color: o.color, region: o.region ?? null, appellation: o.appellation ?? null, notes: o.notes ?? '' })),
		when: t.date ? fmtDay(t.date) : '',
		// a friend's home is named after them: "At Claude's"
		where: [t.place?.type === "Friend's Place" ? `At ${t.place.name}’s` : (t.place?.name ?? t.location), t.place?.city].filter(Boolean).join(', '),
		filename: `${[w.producer, w.cuvee, w.vintage].filter(Boolean).join('-')}`.toLowerCase().replace(/[^a-z0-9]+/g, '-')
	});
</script>

<svelte:head><title>{wineName(w)} · {t.date ? fmtDate(t.date) : 'Undated'} · WineLib</title></svelte:head>

<HomeMap full by="tasted" {focus} />

<a class="back muted" href={links.tastings()}>← Tasting notes</a>

<div class="head">
	<div>
		<div class="kind"><Icon name="glass" size={12} />Tasting{t.occasion.length > 1 ? ` · ${plural(t.occasion.length, 'wine')}` : ''}</div>
		<h1>
			{#if t.place}<a href={links.place(t.place.id)}><PlaceName name={t.place.name} type={t.place.type} /></a>{:else}{placeName}{/if}
			{#if t.place?.stars}<span class="stars" title="{t.place.stars} Michelin star{t.place.stars > 1 ? 's' : ''}">{stars(t.place.stars)}</span>{/if}
		</h1>
		<div class="when">
			<span class="num">{t.date ? fmtDay(t.date) : 'Undated'}</span>
			{#if t.place?.city}<span class="muted"> · {[t.place.city, t.place.country].filter(Boolean).join(', ')}</span>{/if}
		</div>
	</div>
	<div class="page-actions">
		<ActionMenu>
			<a class="menu-item" role="menuitem" href={links.newTasting({ place_id: t.place?.id, date: t.date })}><Icon name="glass" size={15} />Add a wine to this evening</a>
			<hr />
			<a class="menu-item" role="menuitem" href={links.editTasting(t.id)}><Icon name="edit" size={15} />Edit this tasting (glasses, order, styles)</a>
			<a class="menu-item" role="menuitem" href={links.editBottle(b.id)}><Icon name="bottle" size={15} />Edit the bottle</a>
		</ActionMenu>
		<ShareSticker {...sticker} />
	</div>
</div>

<!-- the evening's own note: the menu, who came, the occasion (a day at a place: needs both) -->
{#if t.place && t.date}
	<section class="card evening" aria-label="The evening">
		<div class="kind"><Icon name="edit" size={12} />The evening</div>
		{#if writing === EVENING}
			<NoteBox
				id={t.id}
				notes={evening}
				label="The evening's note"
				placeholder="The menu, who came, the occasion…"
				save={(text) => saveEveningNote(t.id, text)}
				onclose={wrote(EVENING)}
			/>
		{:else if evening}
			<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
			<blockquote title="Tap to change the evening's note" onclick={(e) => !(e.target as HTMLElement).closest('a') && write(EVENING)}><NoteText md={evening} /></blockquote>
		{:else}
			<button type="button" class="add-note" onclick={() => write(EVENING)}>+ The menu, who came, the occasion</button>
		{/if}
	</section>
{/if}

<!-- the evening's wines in the order poured, each with its note -->
<ol class="wines">
	{#each t.occasion as o, i (o.id)}
		{@const mine = o.id === t.id}
		<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
		<li
			id="wine-{o.id}"
			class="card wine"
			class:current={mine}
			class:shown={picked?.wine_id === o.wine_id}
			onpointerenter={(e) => e.pointerType === 'mouse' && appSettings.map_follow === 'hover' && pick(o, 180)}
			onclick={(e) => !(e.target as HTMLElement).closest('a, button, textarea, blockquote') && pick(o)}
		>
			<div class="top">
				<span class="seq num muted">{i + 1}</span>
				{#if o.label}
					<img class="label-img" src={labelThumb(o.label.url)} alt="" loading="lazy" decoding="async" use:labelTip={o.label} />
				{:else}
					<span class="end"><BottleEnd region={regionColor(o.region ?? null) ?? FALLBACK_REGION} color={o.color} size={14} title="{regionLabel(o.region ?? null)} · {o.color ?? ''}" /></span>
				{/if}
				<div class="name">
					<a href={links.wine(o.wine_id)}><b>{o.producer}</b>{o.cuvee ? ` ${o.cuvee}` : ''}</a>
					<span class="vintage num">{o.vintage}</span>
					<div class="under muted">
						<span>{[o.appellation, o.region && o.region !== o.appellation ? regionLabel(o.region) : null].filter(Boolean).join(' · ')}</span>
						{#if o.rating}<span class="mine num" title="Your score">{o.rating}</span>{/if}<CriticPills scores={o.scores} />
					</div>
				</div>
				{#if !mine}<a class="open muted" href={links.tasting(o.id)} title="Open this tasting" aria-label="Open this tasting">›</a>{/if}
			</div>
			<div class="note">
				{#if writing === o.id}
					<NoteBox id={o.id} notes={noteOf(o)} label="Note on {o.producer} {o.cuvee}" onclose={wrote(o.id)} />
				{:else if noteOf(o)}
					<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
					<blockquote title="Tap to change the note" onclick={(e) => !(e.target as HTMLElement).closest('a') && write(o.id)}><NoteText md={noteOf(o)} /></blockquote>
				{:else}
					<button type="button" class="add-note" aria-label="Add a note on {o.producer} {o.cuvee}" onclick={() => write(o.id)}>+ Add a note</button>
				{/if}
			</div>
			{#if mine}
				{#if t.styles?.length || t.tags}
					<div class="tags">
						{#each t.styles ?? [] as s (s)}<span class="tag style" title="The wine's style, as you found it">{s}</span>{/each}
						{#each (t.tags ?? '').split(',').map((x) => x.trim()).filter(Boolean) as tag}<span class="tag">{tag}</span>{/each}
					</div>
				{/if}
				{#if bottleLine}<a class="bottle-line muted" href={links.bottle(b.id)}>{bottleLine} ›</a>{/if}
			{/if}
		</li>
	{/each}
</ol>

<!-- the evening's photo: added, replaced or removed here -->
<section class="card photo">
	<OccasionPhoto place={placeName} date={t.date} url={t.photo} alt="{placeName}, {t.date}" />
</section>

{#if t.history.length}
	<section class="card history-card">
		<h2>Other tastings of {w.producer}{w.cuvee ? ` ${w.cuvee}` : ''} <span class="muted num">{t.history.length}, all vintages</span></h2>
		<ul class="history">
			{#each t.history as h (h.id)}
				<li>
					<a class="h-date num" href={links.tasting(h.id)}>{fmtDate(h.date)}</a>
					<span class="h-vintage num">{h.vintage}</span>
					<span class="h-place muted">{h.place ?? ''}</span>
					<a class="h-note" class:muted={!h.notes} href={links.tasting(h.id)}>{h.notes || 'No note'}</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.back {
		font-size: 13px;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		flex-wrap: wrap;
		gap: 14px;
		margin: 10px 0 14px;
	}
	/* what this page is, as on the other detail pages */
	.kind {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--muted);
		margin-bottom: 2px;
	}
	h1 a:hover {
		color: var(--accent);
	}
	h1 .stars {
		margin-left: 8px;
		font-size: 18px;
		vertical-align: middle;
	}
	.when {
		margin-top: 2px;
	}
	.stars {
		color: var(--gold-text);
		letter-spacing: 1px;
	}
	.head .page-actions {
		display: flex;
		flex-direction: row;
		gap: 8px;
		align-items: center;
	}
	/* the wines, a card each */
	.wines {
		list-style: none;
		padding: 0;
		margin: 0 0 12px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.wine {
		padding: 12px 14px 8px;
		cursor: pointer;
		transition:
			box-shadow 0.15s,
			border-color 0.15s;
	}
	.wine.current {
		border-color: var(--accent);
		box-shadow: 0 0 0 1px var(--accent), var(--shadow);
	}
	.wine.shown:not(.current) {
		background: color-mix(in srgb, var(--accent) 6%, var(--surface));
	}
	.top {
		display: flex;
		align-items: flex-start;
		gap: 10px;
	}
	.seq {
		width: 12px;
		font-size: 12px;
		padding-top: 2px;
		text-align: right;
		flex: none;
	}
	.label-img {
		flex: none;
		width: 34px;
		height: 44px;
		object-fit: cover;
		border-radius: 3px;
		border: 2px solid #fff;
		box-shadow:
			0 0 0 1px var(--border),
			0 1px 3px rgb(0 0 0 / 0.2);
		background: #fff;
	}
	.end {
		flex: none;
		padding-top: 3px;
	}
	.name {
		flex: 1;
		min-width: 0;
		font-size: 15px;
		line-height: 1.35;
	}
	.name a {
		color: inherit;
	}
	.name a:hover {
		color: var(--accent);
	}
	.vintage {
		color: var(--muted);
		font-weight: 500;
		margin-left: 4px;
	}
	.under {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		margin-top: 1px;
	}
	.open {
		flex: none;
		font-size: 20px;
		line-height: 1;
		padding: 0 4px;
		text-decoration: none;
	}
	.open:hover {
		color: var(--accent);
	}
	.note {
		margin: 10px 0 0 22px;
	}
	.add-note {
		padding: 2px 0;
		border: none;
		background: none;
		color: var(--muted);
		font: inherit;
		font-size: 13px;
		cursor: pointer;
	}
	.add-note:hover {
		color: var(--accent);
	}
	.evening {
		margin-bottom: 12px;
		padding: 10px 14px 6px;
	}
	.evening .kind {
		margin-bottom: 6px;
	}
	blockquote {
		margin: 0 0 8px;
		padding: 2px 0 2px 12px;
		border-left: 3px solid var(--accent);
		font-size: 15px;
		line-height: 1.55;
		cursor: text;
	}
	.mine {
		padding: 0 6px;
		border-radius: 8px;
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
		background: var(--accent-soft);
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin: 2px 0 6px 22px;
	}
	.tag {
		font-size: 12px;
		padding: 1px 8px;
		border-radius: 10px;
		background: var(--surface-2);
	}
	.tag.style {
		background: none;
		border: 1px solid var(--accent);
		color: var(--accent);
	}
	.bottle-line {
		display: block;
		margin: 0 0 4px 22px;
		font-size: 12px;
		text-decoration: none;
	}
	.bottle-line:hover {
		color: var(--accent);
	}
	section {
		padding: 14px 16px;
		margin-bottom: 12px;
	}
	h2 {
		font-size: 13px;
		margin: 0 0 8px;
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	h2 span {
		font-size: 12px;
		font-weight: 400;
	}
	.history {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.history li {
		display: grid;
		grid-template-columns: auto auto minmax(0, 1fr);
		align-items: baseline;
		gap: 4px 10px;
		padding: 5px 0;
		border-bottom: 1px solid var(--border);
		font-size: 12px;
	}
	.history li:last-child {
		border-bottom: none;
	}
	.h-date {
		color: var(--link);
	}
	.h-date:hover {
		color: var(--accent);
	}
	.h-vintage {
		font-weight: 600;
	}
	.h-place,
	.h-note {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.h-note {
		grid-column: 1 / -1;
		color: inherit;
	}
</style>

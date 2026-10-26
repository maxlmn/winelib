<script lang="ts" module>
	import type { Choice, WineSummary } from '#lib/api/forms.ts';

	/** An import's suggestion drawn as a wine card (a pick whose `wine` is set: e.g. a plug-in's
	 * import of reviews), to tick, edit or point at another wine */
	export interface WinePick {
		key: string;
		/** whose score it is (the critic), and the review's link */
		critic: string;
		link: string | null;
		wine: WineSummary & { appellation_id: number | null; varietal_id: number | null };
		status: string;
		score: string | null;
		review: string;
		notes: string[];
		target: { producer_id: number | null; vintage: string };
	}
	/** The wine as edited in the preview: what the review is given to (that vintage if you have it, else a new one) */
	export interface WineEdit {
		cuvee: string;
		vintage: string;
		type: string | null;
		appellation: Choice | null;
		varietal: Choice | null;
		/** a wine picked with "another wine…": its region, LWIN and vineyard */
		wine: number | null;
		region: string | null;
		/** when that wine is yours and already has another review: replace it (else it's kept) */
		replace: boolean;
	}
	/** what the run posts for an edit */
	export const editBody = (e: WineEdit) => ({
		wine: e.wine,
		cuvee: e.cuvee.trim(),
		vintage: e.vintage.trim() || null,
		type: e.type,
		appellation: e.appellation ? (e.appellation.id ?? { name: e.appellation.name }) : null,
		varietal: e.varietal ? (e.varietal.id ?? { name: e.varietal.name }) : null,
		replace: e.replace
	});
</script>

<script lang="ts">
	import { links } from '#lib/links.ts';
	import Combobox from '#lib/components/forms/Combobox.svelte';
	import WineCard from '#lib/components/forms/WineCard.svelte';
	import { lookup } from '#lib/api/forms.ts';
	import { TYPE_COLORS } from '#lib/colors.ts';

	/** One suggestion as the wine form's card. Edit (cuvée, vintage, colour, appellation, grape) or "Another wine…"
	 * (one of the producer's cuvées as the model) replace it with the edited wine, drawn in another colour. */
	let { pick, edit = $bindable(), onedit }: { pick: WinePick; edit: WineEdit | undefined; onedit: () => void } = $props();

	let mode = $state<'' | 'edit' | 'pick'>('');
	const uid = Math.random().toString(36).slice(2, 8); // the fields' ids
	type Row = { id: number; name: string };
	type WineRow = WineSummary & { appellation_id: number | null; varietal_id: number | null };

	const start = (): WineEdit => ({
		cuvee: pick.wine.cuvee, vintage: pick.wine.vintage ?? '', type: pick.wine.type,
		appellation: pick.wine.appellation ? { id: pick.wine.appellation_id, name: pick.wine.appellation } : null,
		varietal: pick.wine.varietal ? { id: pick.wine.varietal_id, name: pick.wine.varietal } : null,
		wine: pick.wine.id || null, region: pick.wine.region, replace: false
	});
	function editing() {
		if (!edit) {
			edit = start();
			onedit();
		}
		mode = mode === 'edit' ? '' : 'edit';
	}
	// The card shown: the edited wine, else the suggestion
	const shown = $derived<WineSummary>(edit
		? { ...pick.wine, cuvee: edit.cuvee, vintage: edit.vintage || null, type: edit.type,
			appellation: edit.appellation?.name ?? null, varietal: edit.varietal?.name ?? null, region: edit.region }
		: pick.wine);

	// "Another wine…": the producer's cuvées (newest vintage as the model), in the review's vintage
	let query = $state('');
	let cuvees = $state<{ model: WineRow; label: string }[]>([]);
	let timer: ReturnType<typeof setTimeout> | undefined;
	function search() {
		clearTimeout(timer);
		timer = setTimeout(async () => {
			const rows = await lookup<WineRow>('wines', { q: query, producer_id: pick.target.producer_id, limit: 100 });
			const out = new Map<string, { model: WineRow; label: string; vintages: string[] }>();
			for (const w of rows) {
				const k = [w.cuvee, w.appellation, w.varietal, w.type].join('|');
				const c = out.get(k) ?? { model: w, vintages: [],
					label: [w.cuvee || w.appellation || '(plain)', w.cuvee ? w.appellation : null, w.varietal].filter(Boolean).join(' · ') };
				c.vintages.push(w.vintage ?? 'NV');
				out.set(k, c);
			}
			cuvees = [...out.values()].map((c) => ({ model: c.model, label: `${c.label} — ${c.vintages.slice(0, 4).join(', ')}${c.vintages.length > 4 ? '…' : ''}` }));
		}, 150);
	}
	function picking() {
		mode = mode === 'pick' ? '' : 'pick';
		if (mode === 'pick') search();
	}
	function choose(w: WineRow) {
		edit = {
			cuvee: w.cuvee, vintage: edit?.vintage || pick.target.vintage, type: w.type,
			appellation: w.appellation ? { id: w.appellation_id, name: w.appellation } : null,
			varietal: w.varietal ? { id: w.varietal_id, name: w.varietal } : null,
			wine: w.id, region: w.region, replace: false
		};
		onedit();
		mode = ''; // the card shows it; Edit to change the vintage or anything else
	}
	// What the edited wine resolves to: one you have (with this critic's score, if any) or null (created on import)
	let existing = $state<{ id: number; score: string | null; url: string | null } | null | undefined>(undefined);
	let checkTimer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => {
		if (!edit) return void (existing = undefined);
		const p = new URLSearchParams({ producer_id: String(pick.target.producer_id ?? ''), cuvee: edit.cuvee.trim(),
			vintage: edit.vintage.trim(), type: edit.type ?? '', critic: pick.critic });
		for (const [k, c] of [['appellation', edit.appellation], ['varietal', edit.varietal]] as const)
			if (c) c.id ? p.set(k, String(c.id)) : p.set(`${k}_name`, c.name);
		clearTimeout(checkTimer);
		checkTimer = setTimeout(async () => {
			const r = await fetch(`/api/maintenance/wine?${p}`);
			existing = r.ok ? await r.json() : undefined;
		}, 250);
	});
	const sameReview = $derived(!!existing?.url && existing.url === pick.link);

	function reset() {
		edit = undefined;
		mode = '';
	}
</script>

<div class="pick" class:edited={!!edit}>
	<WineCard wine={shown}>
		{#snippet below()}
			<div class="line">
				<span class="status" class:mine={!edit && pick.status.startsWith('Your wine')} class:ed={!!edit}>
					{edit ? 'Edited: your corrections replace the suggestion' : pick.status}
				</span>
				{#if pick.score}<b class="score num">{pick.critic} {pick.score}</b>{/if}
				<span class="muted review">“{pick.review}”</span>
			</div>
			{#if edit && existing !== undefined}
				<div class="resolves">
					{#if existing === null}
						<span>New vintage: created on import</span>
					{:else if sameReview}
						<span>You have it, with this review already: nothing to do</span>
					{:else if existing.score}
						<a href={links.wine(existing.id)} target="_blank" rel="noreferrer">You have it</a>
						<span class="check">with {pick.critic} {existing.score} from another review</span>
						<label class="replace"><input type="checkbox" bind:checked={edit.replace} /> Replace its review</label>
						{#if !edit.replace}<span class="muted">(kept: this review isn't imported)</span>{/if}
					{:else}
						<a href={links.wine(existing.id)} target="_blank" rel="noreferrer">You have it</a>
						<span>without a score: it gets this review</span>
					{/if}
				</div>
			{/if}
			{#if pick.notes.length && !edit}
				<div class="notes">
					{#each pick.notes as n (n)}<span class:check={n.startsWith('check:') || n.startsWith('replaces')}>{n}</span>{/each}
				</div>
			{/if}
		{/snippet}
		{#snippet actions()}
			<button type="button" class="btn small-btn" class:on={mode === 'edit'} onclick={editing}>Edit</button>
			<button type="button" class="btn small-btn" class:on={mode === 'pick'} onclick={picking}>Another wine…</button>
			{#if edit}<button type="button" class="link small" onclick={reset} title="Back to the suggestion">Reset</button>{/if}
			{#if pick.link}<a class="small review-link" href={pick.link} target="_blank" rel="noreferrer">review ↗</a>{/if}
		{/snippet}
	</WineCard>

	{#if mode === 'pick'}
		<div class="panel">
			<input type="search" bind:value={query} oninput={search} placeholder="Search the producer’s wines (cuvée, appellation)" />
			<ul>
				{#each cuvees as c (c.model.id)}
					<li><button type="button" class="link" onclick={() => choose(c.model)}>{c.label}</button></li>
				{:else}
					<li class="muted small">No wine of this producer matches</li>
				{/each}
			</ul>
			<p class="muted small">The review keeps its vintage ({pick.target.vintage || 'NV'}); Edit to change it after.</p>
		</div>
	{:else if mode === 'edit' && edit}
		<div class="panel fields">
			<label>Cuvée <input bind:value={edit.cuvee} placeholder="(plain)" /></label>
			<label class="short">Vintage <input bind:value={edit.vintage} placeholder="NV" /></label>
			<label>Colour
				<select bind:value={edit.type}>
					<option value={null}>?</option>
					{#each Object.keys(TYPE_COLORS) as t (t)}<option value={t}>{t}</option>{/each}
				</select>
			</label>
			<div class="combo">
				<span>Appellation</span>
				<Combobox id="pick-app-{uid}" value={edit.appellation} creatable="appellation" placeholder="Search appellations…"
					search={(q) => lookup<Row>('appellations', { q })} onchange={(c) => edit && (edit.appellation = c)} />
			</div>
			<div class="combo">
				<span>Grape</span>
				<Combobox id="pick-grape-{uid}" value={edit.varietal} creatable="varietal" placeholder="Search grapes…"
					search={(q) => lookup<Row>('varietals', { q, limit: 200 })} onchange={(c) => edit && (edit.varietal = c)} />
			</div>
		</div>
	{/if}
</div>

<style>
	/* An edited suggestion: another colour, it replaces what was suggested */
	.pick.edited :global(.wine) {
		background: color-mix(in srgb, var(--accent) 10%, var(--surface));
		border-color: var(--accent);
	}
	.line {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 8px;
		margin-top: 3px;
		font-size: 12px;
	}
	.status {
		font-size: 11px;
		font-weight: 600;
		padding: 0 7px;
		border-radius: 9px;
		box-shadow: inset 0 0 0 1px var(--border);
	}
	.status.mine {
		color: var(--gold);
		box-shadow: inset 0 0 0 1px var(--gold);
	}
	.status.ed {
		color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
	}
	.score {
		color: var(--accent);
	}
	.review {
		font-style: italic;
	}
	.notes {
		display: flex;
		flex-wrap: wrap;
		gap: 2px 10px;
		margin-top: 2px;
		font-size: 11px;
		color: var(--muted);
	}
	.notes .check,
	.resolves .check {
		color: var(--down);
	}
	.resolves {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 2px 8px;
		margin-top: 3px;
		font-size: 12px;
	}
	.resolves a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.resolves a:hover {
		color: var(--accent);
	}
	.replace {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-weight: 600;
	}
	.small {
		font-size: 12px;
	}
	.small-btn {
		padding: 3px 9px;
		font-size: 12px;
	}
	.small-btn.on {
		border-color: var(--accent);
		color: var(--accent);
	}
	.review-link {
		color: var(--accent);
		align-self: center;
	}
	.panel {
		margin: 6px 0 4px;
		padding: 10px 12px;
		border: 1px dashed var(--accent);
		border-radius: 8px;
		font-size: 12px;
	}
	.panel input,
	.panel select {
		padding: 4px 7px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface);
		color: inherit;
		font: inherit;
	}
	.panel > input {
		width: min(460px, 100%);
	}
	.panel ul {
		list-style: none;
		margin: 6px 0;
		padding: 0;
		max-height: 220px;
		overflow-y: auto;
	}
	.panel li {
		padding: 2px 0;
	}
	.panel p {
		margin: 4px 0 0;
	}
	.fields {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 8px 12px;
		align-items: end;
	}
	.fields label,
	.combo {
		display: flex;
		flex-direction: column;
		gap: 3px;
		color: var(--muted);
	}
	.fields label input,
	.fields label select {
		color: var(--text);
	}
	/* the appellation and grape boxes fill their column instead of overflowing the panel */
	.combo {
		min-width: 0;
	}
	.combo :global(input) {
		width: 100%;
		box-sizing: border-box;
	}
</style>

<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import type { CriticScore, WineAction } from '#lib/api/details.ts';
	import { fmtDate } from './wine.ts';

	/** Every critic's score, one line each, and "Add a score". A plug-in's actions (fetching a critic's score...) are
	 * drawn on their critic's line, which shows even without a score; the others next to Add a score. */
	interface Props {
		wineId: number;
		scores: CriticScore[];
		actions: WineAction[];
	}
	let { wineId, scores, actions }: Props = $props();

	const real = (s: string | null) => !!s && !['-', '0'].includes(s.trim()); // "-": searched, nothing found
	// The critics an action is for, without a score here yet: an empty line first, with its button
	const lines = $derived([
		...[...new Set(actions.map((a) => a.critic).filter((c): c is string => !!c))]
			.filter((c) => !scores.some((s) => s.critic === c))
			.map((critic): CriticScore & { empty?: boolean } => ({ critic, score: null, note: null, url: null, date: null, empty: true })),
		...scores
	]);
	const loose = $derived(actions.filter((a) => !a.critic));

	// An action's state: running (its busy text), then its answer's message
	let acted = $state<Record<string, { busy: boolean; text: string; error?: boolean }>>({});
	$effect(() => {
		void wineId; // another vintage: back to the buttons
		acted = {};
	});
	async function act(a: WineAction) {
		if (a.confirm && !confirm(a.confirm)) return;
		acted[a.id] = { busy: true, text: a.busy ?? '…' };
		try {
			const res = await fetch(a.endpoint, { method: 'POST' });
			const body = await res.json().catch(() => ({}));
			if (!res.ok) return void (acted[a.id] = { busy: false, text: body.detail ?? `Error ${res.status}`, error: true });
			acted[a.id] = { busy: false, text: body.message ?? '' };
			if (body.reload) await invalidateAll();
		} catch {
			acted[a.id] = { busy: false, text: 'The app couldn’t be reached', error: true };
		}
	}
	const busy = $derived(Object.values(acted).some((x) => x.busy));

	const blank = () => ({ critic: '', score: '', note: '', url: '', date: '' });
	let form = $state<ReturnType<typeof blank> | null>(null);
	let editing = $state<string | null>(null); // the critic being edited, null when adding
	let critics = $state<string[]>([]);
	let saving = $state(false);
	let error = $state('');

	async function open(s?: CriticScore) {
		error = '';
		editing = s?.critic ?? null;
		form = s ? { critic: s.critic, score: s.score ?? '', note: s.note ?? '', url: s.url ?? '', date: s.date ?? '' } : blank();
		if (!critics.length) critics = await fetch('/api/lookups/critics').then((r) => (r.ok ? r.json() : [])).catch(() => []);
	}

	async function save() {
		if (!form) return;
		if (!form.critic.trim()) return (error = 'Which critic?');
		saving = true;
		const res = await fetch(`/api/wines/${wineId}/scores`, {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ ...form, date: form.date || null })
		});
		saving = false;
		if (!res.ok) return (error = (await res.json().catch(() => ({}))).detail ?? `Error ${res.status}`);
		form = null;
		await invalidateAll();
	}

	async function remove(critic: string) {
		if (!confirm(`Remove ${critic}’s score?`)) return;
		const res = await fetch(`/api/wines/${wineId}/scores?critic=${encodeURIComponent(critic)}`, { method: 'DELETE' });
		if (res.ok) await invalidateAll();
	}
</script>

{#snippet buttons(list: WineAction[])}
	{#each list as a (a.id)}
		{@const r = acted[a.id]}
		{#if r?.busy}
			<span>{r.text}</span>
		{:else}
			<button class="btn small-btn" disabled={busy} onclick={() => act(a)}>{a.label}</button>
			{#if r?.text}<span class:error={r.error}>{r.text}</span>{/if}
		{/if}
	{/each}
{/snippet}

<section class="card critics">
	<div class="head">
		<h2>Critics</h2>
		<div class="meta muted small">
			{@render buttons(loose)}
			{#if !form}<button class="btn small-btn" onclick={() => open()}>＋ Add a score</button>{/if}
		</div>
	</div>
	{#each lines as s (s.critic)}
		<div class="line">
			<div class="who">
				<span class="label">{s.critic}</span>
				<span class="value num" class:muted={!real(s.score)}>{real(s.score) ? s.score : '–'}</span>
			</div>
			<div class="text">
				{#if s.note}<p>{s.note}</p>{/if}
				<div class="meta muted small">
					{#if s.date}{fmtDate(s.date)}{/if}
					{#if s.url}<a class="link" href={s.url} target="_blank" rel="noreferrer">Review ↗</a>{/if}
					{@render buttons(actions.filter((a) => a.critic === s.critic))}
					{#if !('empty' in s)}
						<button class="link" onclick={() => open(s)}>Edit</button>
						<button class="link" onclick={() => remove(s.critic)}>Remove</button>
					{/if}
				</div>
			</div>
		</div>
	{/each}

	{#if form}
		<div class="form">
			<label>Critic
				<input bind:value={form.critic} list="critics-{wineId}" placeholder="e.g. Vinous, Jancis Robinson" disabled={!!editing} />
				<datalist id="critics-{wineId}">{#each critics as c (c)}<option value={c}></option>{/each}</datalist>
			</label>
			<label class="short">Score <input bind:value={form.score} placeholder="95, 17.5, (93-95)" /></label>
			<label class="short">Date <input type="date" bind:value={form.date} /></label>
			<label class="wide">Link <input type="url" bind:value={form.url} placeholder="https://…" /></label>
			<label class="wide">Note <textarea rows="3" bind:value={form.note}></textarea></label>
			<div class="actions">
				{#if error}<span class="error small">{error}</span>{/if}
				<button class="btn" onclick={() => (form = null)}>Cancel</button>
				<button class="btn primary" disabled={saving} onclick={save}>{saving ? 'Saving…' : editing ? 'Save' : 'Add score'}</button>
			</div>
		</div>
	{/if}
</section>

<style>
	.critics {
		padding: 14px 16px;
	}
	.head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		margin-bottom: 6px;
	}
	h2 {
		margin: 0;
		font-size: 15px;
	}
	.line {
		display: flex;
		gap: 14px;
		padding: 8px 0;
		border-top: 1px solid var(--border);
	}
	.who {
		display: flex;
		flex-direction: column;
		min-width: 110px;
	}
	.label {
		font-size: 12px;
		color: var(--muted);
	}
	.value {
		font-size: 22px;
		font-weight: 650;
	}
	.text {
		flex: 1;
		min-width: 0;
	}
	.text p {
		margin: 0 0 4px;
		font-size: 13px;
		line-height: 1.5;
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 12px;
	}
	.small {
		font-size: 12px;
	}
	.small-btn {
		padding: 3px 9px;
		font-size: 12px;
	}
	.link {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
		font: inherit;
	}
	.link:hover {
		color: var(--accent);
	}
	.form {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
		gap: 8px 12px;
		padding-top: 8px;
		border-top: 1px solid var(--border);
	}
	.form label {
		display: flex;
		flex-direction: column;
		gap: 3px;
		font-size: 12px;
		color: var(--muted);
	}
	.form .wide {
		grid-column: 1 / -1;
	}
	.form input,
	.form textarea {
		padding: 5px 8px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface);
		color: var(--text);
		font: inherit;
	}
	.actions {
		grid-column: 1 / -1;
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: 8px;
	}
	.error {
		color: var(--down);
		margin-right: auto;
	}
</style>

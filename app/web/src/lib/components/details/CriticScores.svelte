<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import type { CriticScore } from '#lib/api/details.ts';
	import { fmtDate } from './wine.ts';

	/** Every critic's score, one line each, and "Add a score". Without a score there's no card, unless `adding` (the
	 * header's Add a critic's score icon): then just its form. (A plug-in's actions, fetching a critic's score, are
	 * among the header's icons too: WineActions.) */
	interface Props {
		wineId: number;
		scores: CriticScore[];
		/** the form open, to add a score (bound: false again once saved or cancelled) */
		adding?: boolean;
	}
	let { wineId, scores, adding = $bindable(false) }: Props = $props();

	const real = (s: string | null) => !!s && !['-', '0'].includes(s.trim()); // "-": searched, nothing found
	const lines = $derived(scores.filter((s) => real(s.score) || s.note || s.url));

	const blank = () => ({ critic: '', score: '', note: '', url: '', date: '' });
	let form = $state<ReturnType<typeof blank> | null>(null);
	let editing = $state<string | null>(null); // the critic being edited, null when adding
	let critics = $state<string[]>([]);
	let saving = $state(false);
	let error = $state('');

	$effect(() => {
		if (adding && !form) open();
	});

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
		adding = false;
		await invalidateAll();
	}

	async function remove(critic: string) {
		if (!confirm(`Remove ${critic}’s score?`)) return;
		const res = await fetch(`/api/wines/${wineId}/scores?critic=${encodeURIComponent(critic)}`, { method: 'DELETE' });
		if (res.ok) await invalidateAll();
	}
</script>

{#if lines.length || form}
<section class="card critics">
	<div class="head">
		<h2>Critics</h2>
		<div class="meta muted small">
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
					<button class="link" onclick={() => open(s)}>Edit</button>
					<button class="link" onclick={() => remove(s.critic)}>Remove</button>
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
				<button class="btn" onclick={() => ((form = null), (adding = false))}>Cancel</button>
				<button class="btn primary" disabled={saving} onclick={save}>{saving ? 'Saving…' : editing ? 'Save' : 'Add score'}</button>
			</div>
		</div>
	{/if}
</section>
{/if}

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

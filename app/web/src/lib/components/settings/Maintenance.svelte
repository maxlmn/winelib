<script lang="ts">
	/** Maintenance scripts (app/api/tasks/) run on the server as background jobs: see app/api/routers/maintenance.py */
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { messageOf, request } from '#lib/api/http.ts';
	import PickList from './PickList.svelte';
	import LieuPeek from './LieuPeek.svelte';
	import PickCard, { editBody } from './PickCard.svelte';
	import UnknownProducers from './UnknownProducers.svelte';
	import type { Unknown } from './UnknownProducers.svelte';
	import type { WineEdit, WinePick } from './PickCard.svelte';
	import type { PickItem } from './PickList.svelte';

	/** A pair that can be merged (similar cuvée names, duplicate producers): keep a or b, the other merges into
	 * it; pick[a|b] is what's posted to task */
	interface MergeOffer {
		task: 'merge_cuvees' | 'merge_producers';
		a: string;
		b: string;
		wines: [number, number];
		pick: { a: object; b: object };
	}
	interface Result {
		summary?: string;
		/** a pick list's flagged kind ("known cuvées"): see PickList */
		flag?: string;
		/** an import's rows whose producer wasn't recognised */
		unknown?: Unknown[];
		/** a button that starts another task (a plug-in's: search every wine again, one login for the lot) */
		bulk?: { task: string; label: string; confirm: string | null } | null;
		/** an import's file: its columns, and which one each field was read from */
		columns?: { headers: string[]; mapping: Record<string, string>; fields: string[]; required: string[] };
		/** a line each; `action`: a button posting to its endpoint (a plug-in's: Clear and search again), whose answer's
		 * message is shown (`ok: false` keeps the button); `pick`: a suggestion to tick before the run (PickList) */
		items?: { label: string; detail: string | null; href: string | null; copies?: Copy[]; merge?: MergeOffer; action?: ItemAction; pick?: PickItem['pick'] }[];
	}
	interface ItemAction {
		label: string;
		endpoint: string;
		busy?: string;
		confirm?: string;
	}
	interface Job {
		task: string;
		title: string;
		commit: boolean;
		params: { limit?: number };
		started: number;
		finished: number | null;
		status: 'running' | 'done' | 'failed' | 'stopped';
		result: Result | null;
		log?: string[];
	}
	interface Task {
		id: string;
		group: string;
		title: string;
		description: string;
		preview: boolean;
		writes: boolean;
		limit: number | null;
		/** what the limit counts: wines, places */
		unit: string | null;
		/** a file to choose (the imports: a CSV), and its critic (Import critic scores) */
		upload: boolean;
		critic: boolean;
		/** what it needs first (an integration, an address): shown instead of its buttons */
		unavailable: string | null;
		last: Job | null;
	}
	interface Backup {
		name: string;
		kind: 'csv' | 'sql' | 'sqlite';
		size: number;
		modified: number;
	}

	let tasks = $state<Task[]>([]);
	// A preview to tick: ticks, and the suggestions drawn as wine cards edited (key -> the wine as corrected)
	let ticked = $state<Record<string, boolean>>({});
	let edits = $state<Record<string, WineEdit | undefined>>({});
	$effect(() => {
		void job?.result?.items; // a new preview: no edits yet
		edits = {};
		acted = {};
	});
	let groups = $state<string[]>([]);
	/** every task's group (hidden ones too): the job's panel opens under it */
	let taskGroups = $state<Record<string, string>>({});
	let job = $state<Job | null>(null);
	let backups = $state<Backup[]>([]);
	let limits = $state<Record<string, number>>({});
	let error = $state('');
	let logEl = $state<HTMLPreElement>();
	/** Pairs picked for merging: item index -> the one to keep */
	let keep = $state<Record<number, 'a' | 'b' | ''>>({});
	const picked = $derived(
		(job?.result?.items ?? []).flatMap((it, i) => (it.merge && keep[i] ? [it.merge.pick[keep[i] as 'a' | 'b']] : []))
	);
	const mergeTask = $derived(job?.result?.items?.find((it) => it.merge)?.merge?.task);

	const running = $derived(job?.status === 'running');

	// Import critic scores: the CSV read in the browser and sent with each preview and the run, its critic, and the
	// columns as recognised (or picked by hand after a preview)
	let uploads = $state<Record<string, { name: string; text: string } | undefined>>({}); // task id -> its file
	let critic = $state('');
	let critics = $state<string[]>([]);
	let columns = $state<Record<string, string>>({});
	$effect(() => {
		columns = { ...(job?.result?.columns?.mapping ?? {}) };
	});
	const FIELD_LABELS: Record<string, string> = { cuvee: 'cuvée' };
	async function choose(task: string, e: Event & { currentTarget: HTMLInputElement }) {
		const file = e.currentTarget.files?.[0];
		uploads[task] = file ? { name: file.name, text: await file.text() } : undefined;
	}
	const uploadBody = (task: string, mapping: Record<string, string> | null) => ({ text: uploads[task]?.text ?? '', critic, mapping });

	async function load() {
		let m, b;
		try {
			[m, b] = await Promise.all([
				request<{ tasks: Task[]; groups: typeof groups; task_groups: typeof taskGroups; job: typeof job }>('/api/maintenance'),
				request<typeof backups>('/api/maintenance/backups')
			]);
		} catch (e) {
			error = `Maintenance couldn’t load: ${messageOf(e)}`;
			return;
		}
		tasks = m.tasks;
		if (tasks.some((t) => t.critic) && !critics.length)
			critics = await fetch('/api/lookups/critics').then((r) => (r.ok ? r.json() : [])).catch(() => []);
		groups = m.groups;
		taskGroups = m.task_groups;
		job = m.job;
		backups = b;
		for (const t of tasks) if (t.limit && !(t.id in limits)) limits[t.id] = t.limit;
		await opened();
	}

	// Opened on one task (links.maintenance, from Needs attention): its preview started, or a report run, unless a job
	// is already running; its card brought into view. Once per link: load() runs again when a job ends, and would
	// start the preview again, and again
	let openedFor: string | null = null;
	async function opened() {
		const id = page.url.searchParams.get('task');
		if (!id || id === openedFor) return;
		openedFor = id;
		const t = tasks.find((x) => x.id === id);
		if (!t) return;
		if (!job || job.status !== 'running') {
			if (t.preview) await start(t, false);
			else if (!t.writes) await start(t, true);
		}
		await tick();
		document.getElementById(`task-${t.id}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
	}

	// While a job runs, follow its log: asked again a second after each answer (never two at once on a slow server);
	// a failed ask is retried, said once
	$effect(() => {
		if (!running) return;
		let timer: ReturnType<typeof setTimeout>;
		let stopped = false;
		const poll = async () => {
			try {
				job = await request<typeof job>('/api/maintenance/job');
				error = '';
				if (job?.status !== 'running') return load();
			} catch (e) {
				error = `Lost track of the job (retrying): ${messageOf(e)}`;
			}
			if (!stopped) timer = setTimeout(poll, 1000);
		};
		timer = setTimeout(poll, 1000);
		return () => {
			stopped = true;
			clearTimeout(timer);
		};
	});
	$effect(() => {
		void job?.log?.length;
		if (logEl) logEl.scrollTop = logEl.scrollHeight;
	});

	async function start(t: Task, commit: boolean) {
		if (commit && t.writes && !confirm(`${t.title}: this changes your data. Run it?`)) return;
		if (t.upload) {
			if (!uploads[t.id]) return (error = 'Choose a CSV file');
			if (t.critic && !critic.trim()) return (error = 'Which critic are these reviews by?');
			return post(t.id, { commit, ...uploadBody(t.id, null) });
		}
		await post(t.id, { commit, limit: limits[t.id] ?? null });
	}

	// A line's action (an item's `action`): its answer's message shown on the line
	let acted = $state<Record<number, { busy: boolean; text: string; done: boolean }>>({});
	const acting = $derived(Object.values(acted).some((x) => x.busy));
	async function act(i: number, a: ItemAction) {
		if (a.confirm && !confirm(a.confirm)) return;
		acted[i] = { busy: true, text: a.busy ?? '…', done: false };
		try {
			const body = await request<{ message?: string; ok?: boolean }>(a.endpoint, { method: 'POST' });
			acted[i] = { busy: false, text: body?.message ?? 'Done', done: body?.ok !== false };
		} catch (e) {
			acted[i] = { busy: false, text: messageOf(e), done: false };
		}
	}

	// A report's button for all its lines at once: another task, run straight away
	async function bulk(b: NonNullable<Result['bulk']>) {
		if (b.confirm && !confirm(b.confirm)) return;
		await post(b.task, { commit: true });
	}

	async function merge(commit: boolean) {
		if (!mergeTask) return;
		const n = picked.length;
		const what = mergeTask === 'merge_producers'
			? `${n} producer${n > 1 ? 's' : ''}? Their wines move to the one kept (or merge into the same wine there), then they're deleted.`
			: `${n} cuvée name${n > 1 ? 's' : ''}? Wines are renamed, or merged into their twin.`;
		if (commit && !confirm(`Merge ${what}`)) return;
		await post(mergeTask, { commit, pairs: picked });
		keep = {};
	}

	async function post(task: string, body: object) {
		error = '';
		try {
			job = await request<typeof job>(`/api/maintenance/${task}`, { method: 'POST', body });
		} catch (e) {
			error = messageOf(e);
		}
	}

	const stop = () => request('/api/maintenance/job/stop', { method: 'POST' }).catch((e) => (error = messageOf(e)));

	const when = (s: number) =>
		new Date(s * 1000).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
	const size = (n: number) => (n > 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1e3))} KB`);
	// A duplicate wine's copies (Duplicate wines' preview): each one's page and what it holds, the one kept first
	type Copy = { href: string; keep: boolean; facts: string };
	const STATUS: Record<Job['status'], string> = { running: 'Running…', done: 'Done', failed: 'Failed', stopped: 'Stopped' };

	onMount(load);
</script>

{#snippet lieuPeek(it: PickItem)}
	<LieuPeek src={String(it.pick.map)} />
{/snippet}

{#snippet cardRow(it: PickItem)}
	<PickCard pick={it.pick as unknown as WinePick} bind:edit={edits[it.pick.key]} onedit={() => (ticked[it.pick.key] = true)} />
{/snippet}

{#snippet jobPanel()}
	{#if job}
	<div class="job">
		<div class="job-head">
			<b>{job.title}{job.commit ? '' : ' · preview'}</b>
			<span class="status" class:bad={job.status === 'failed'} class:ok={job.status === 'done'}>{STATUS[job.status]}</span>
			{#if running}<button class="link" onclick={stop}>Stop</button>{/if}
		</div>
		{#if job.result?.summary}<p class="summary">{job.result.summary}</p>{/if}
		{#if job.result?.columns && !job.commit && !running}
			{@const cols = job.result.columns}
			<div class="columns">
				<span class="muted small">Columns{uploads[job.task] ? ` of ${uploads[job.task]!.name}` : ''}:</span>
				{#each cols.fields as f (f)}
					<label class="small" class:need={cols.required.includes(f) && !columns[f]}>
						{FIELD_LABELS[f] ?? f.replace('_', ' ')}
						<select bind:value={columns[f]}>
							<option value={undefined}>–</option>
							{#each cols.headers as h (h)}<option value={h}>{h}</option>{/each}
						</select>
					</label>
				{/each}
				<button class="btn" disabled={!uploads[job.task]} title={uploads[job.task] ? '' : 'Choose the file again'}
					onclick={() => post(job!.task, uploadBody(job!.task, Object.fromEntries(Object.entries(columns).filter(([, h]) => h))))}>Preview again</button>
			</div>
		{/if}
		{#if job.result?.items?.length && job.result.items[0].pick}
			{#if job.result.unknown}<UnknownProducers unknown={job.result.unknown} />{/if}
			<PickList bind:ticked row={job.result.items[0].pick.wine ? cardRow : undefined} peek={job.task === 'lieux_dits' ? lieuPeek : undefined} items={job.result.items as PickItem[]} verb={job.task === 'lieux_dits' ? 'Link' : 'Import'}
				disabled={running} flag={job.result.flag}
				onrun={(keys) => tasks.find((t) => t.id === job!.task)?.upload
					? post(job!.task, { commit: true, keys, ...uploadBody(job!.task, columns) })
					: post(job!.task, { commit: true, keys, targets: Object.fromEntries(keys.filter((k) => edits[k]).map((k) => [k, editBody(edits[k]!)])) })} />
		{:else if job.result?.items?.length}
			{@const left = job.result.items.filter((it, i) => it.action && !acted[i]?.done).length}
			{#if job.result.bulk && left > 1 && !running}
				{@const b = job.result.bulk}
				<div class="merge-bar">
					<span class="muted small">Each line below on its own, or all at once:</span>
					<button class="btn primary" disabled={acting} onclick={() => bulk(b)}>{b.label} ({left})</button>
				</div>
			{/if}
			<ul class="items">
				{#each job.result.items as it, i (i)}
					<li>
						{#if it.href}<a href={it.href}>{it.label}</a>{:else}{it.label}{/if}
						{#if it.detail}<span class="muted"> · {it.detail}</span>{/if}
						{#if it.copies}
							<ul class="copies">
								{#each it.copies as c (c.href)}
									<li>
										<a href={c.href} title="Open this copy">{c.keep ? 'Kept' : 'Merged into it, then deleted'}</a>
										<span class="muted"> · {c.facts}</span>
									</li>
								{/each}
							</ul>
						{/if}
						{#if it.action && !running}
							{@const r = acted[i]}
							{#if r?.done}
								<span class="act-done">✓ {r.text}</span>
							{:else}
								<button class="link act" disabled={acting} onclick={() => act(i, it.action!)}>{it.action.label}</button>
								{#if r}<span class="muted small"> {r.text}</span>{/if}
							{/if}
						{/if}
						{#if it.merge && !running}
							<select class="keep" bind:value={keep[i]} aria-label="Merge">
								<option value="">Don’t merge</option>
								<option value="a">Keep “{it.merge.a}” ({it.merge.wines[0]})</option>
								<option value="b">Keep “{it.merge.b}” ({it.merge.wines[1]})</option>
							</select>
						{/if}
					</li>
				{/each}
			</ul>
			{#if job.result.items.some((it) => it.merge) && !running}
				<div class="merge-bar">
					<span class="muted small">{picked.length ? `${picked.length} picked` : `Pick the ${mergeTask === 'merge_producers' ? 'producer' : 'name'} to keep for the pairs to merge`}</span>
					<button class="btn" disabled={!picked.length} onclick={() => merge(false)}>Preview merge</button>
					<button class="btn primary" disabled={!picked.length} onclick={() => merge(true)}>Merge selected</button>
				</div>
			{/if}
		{/if}
		{#if job.log?.length}
			<details open={running}>
				<summary class="muted small">Log ({job.log.length} lines)</summary>
				<pre bind:this={logEl}>{job.log.join('\n')}</pre>
			</details>
		{/if}
	</div>
	{/if}
{/snippet}

<section class="card wide maint" id="maintenance">
	<h2>Maintenance</h2>
	<p class="muted intro">Tidy, import and enrich your data, as background jobs. Tasks that change data show a preview first.</p>

	{#if error}<p class="error">{error}</p>{/if}
	{#each groups as g (g)}
		{@const list = tasks.filter((t) => t.group === g)}
		{#if list.length}
			<h3 class="group">{g}</h3>
			<div class="cards">
				{#each list as t (t.id)}
					<div class="task" id="task-{t.id}" class:current={job?.task === t.id}>
						<b>{t.title}</b>
						<p class="muted desc">{t.description}</p>
						{#if t.last}
							<p class="last muted small" class:bad={t.last.status === 'failed'}
								title={t.last.result?.summary ?? ''}>
								Last {t.last.commit ? 'run' : 'preview'} {when(t.last.started)}: {STATUS[t.last.status]}{t.last.result?.summary ? ` · ${t.last.result.summary}` : ''}
							</p>
						{/if}
						{#if t.unavailable}
							<p class="needs small">{t.unavailable}</p>
						{:else if t.upload}
							<input class="file small" type="file" accept=".csv,.tsv,.txt,text/csv" onchange={(e) => choose(t.id, e)} aria-label="CSV file" />
							{#if t.critic}
							<label class="upload small">
								Critic
								<input bind:value={critic} list="maint-critics" placeholder="e.g. Vinous" />
								<datalist id="maint-critics">{#each critics as c (c)}<option value={c}></option>{/each}</datalist>
							</label>
							{/if}
						{/if}
						{#if t.limit}
							<label class="limit" title="How many {t.unit ?? ''}">
								<input type="number" min="1" max="200" bind:value={limits[t.id]} /> {t.unit ?? ''} at most
							</label>
						{/if}
						<div class="actions" class:hidden={t.unavailable}>
							<span class="spacer"></span>
							{#if t.preview}<button class="btn" disabled={running} onclick={() => start(t, false)}>Preview</button>{/if}
							{#if !t.upload}<button class="btn" class:primary={!t.writes} disabled={running} onclick={() => start(t, true)}>Run</button>{/if}
						</div>
					</div>
				{/each}
			</div>
			{#if job && (taskGroups[job.task] ?? groups[groups.length - 1]) === g}{@render jobPanel()}{/if}
			{#if g === 'Backup'}
			<h4>Backups</h4>
			{#if backups.length}
				<ul class="backups">
					{#each backups.slice(0, 12) as b (b.name)}
						<li>
							<a href={`/api/maintenance/backups/${encodeURIComponent(b.name)}`} download>{b.name}</a>
							<span class="muted small">{b.kind === 'sql' ? 'database dump' : b.kind === 'sqlite' ? 'database copy (SQLite)' : 'CSV, zipped'} · {size(b.size)} · {when(b.modified)}</span>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="muted small">No backups in backups/ yet.</p>
			{/if}
			{/if}
		{/if}
	{/each}


</section>

<style>
	/* The full width of the settings grid */
	/* Same frame as the settings page's own sections (their rule is scoped to that page) */
	.maint {
		grid-column: 1 / -1;
		padding: 16px 18px;
	}
	.maint h2 {
		margin: 0 0 4px;
		font-size: 15px;
	}
	.needs {
		margin: 4px 0 0;
		color: var(--muted);
		font-style: italic;
	}
	.actions.hidden {
		display: none;
	}
	.intro {
		margin: 0 0 12px;
		font-size: 13px;
	}
	.group {
		margin: 18px 0 8px;
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--muted);
	}
	/* Up to 4 cards a row, fewer on narrower screens */
	.cards {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(max(220px, calc((100% - 36px) / 4)), 1fr));
		gap: 12px;
	}
	.task {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 12px 14px;
		border: 1px solid var(--border);
		border-radius: 10px;
		background: var(--surface);
		font-size: 13px;
	}
	.task.current {
		border-color: var(--accent);
	}
	.desc {
		margin: 0;
		font-size: 12px;
		line-height: 1.45;
	}
	.last {
		margin: 0;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.desc + .actions,
	.last + .actions {
		margin-top: auto;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		padding-top: 4px;
	}
	.spacer {
		flex: 1;
	}
	h4 {
		margin: 14px 0 6px;
		font-size: 13px;
	}
	.limit {
		margin-top: auto;
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 12px;
		color: var(--muted);
	}
	.limit input {
		width: 56px;
		padding: 4px 6px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface-2);
	}
	.small {
		font-size: 12px;
	}
	.file {
		max-width: 100%;
	}
	.upload {
		display: flex;
		align-items: center;
		gap: 6px;
		color: var(--muted);
	}
	.upload input {
		flex: 1;
		min-width: 0;
		padding: 4px 6px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface-2);
		font: inherit;
	}
	.columns {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 12px;
		margin: 8px 0;
	}
	.columns label {
		display: inline-flex;
		align-items: center;
		gap: 4px;
	}
	.columns select {
		max-width: 160px;
		padding: 3px 4px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface);
		font: inherit;
	}
	.columns .need {
		color: var(--down);
		font-weight: 600;
	}
	.bad {
		color: var(--down);
	}
	.ok {
		color: var(--up);
	}
	.error {
		color: var(--down);
		font-size: 13px;
	}
	.job {
		margin-top: 12px;
		padding: 12px 14px;
		border-radius: 8px;
		background: var(--surface-2);
		font-size: 13px;
	}
	.job-head {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.link {
		margin-left: auto;
		border: none;
		background: none;
		padding: 0;
		color: var(--accent);
		cursor: pointer;
	}
	.summary {
		margin: 8px 0 0;
	}
	.items {
		margin: 8px 0 0;
		padding-left: 18px;
		max-height: 60vh;
		overflow-y: auto;
	}
	.items li {
		padding: 1px 0;
	}
	/* a duplicate's copies under it */
	.copies {
		margin: 2px 0 6px;
		padding-left: 16px;
		font-size: 12px;
	}
	.items a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.items a:hover {
		color: var(--accent);
	}
	pre {
		margin: 6px 0 0;
		max-height: 40vh;
		overflow: auto;
		font-size: 12px;
		white-space: pre-wrap;
	}
	h3 {
		font-size: 13px;
		margin: 16px 0 6px;
	}
	.backups {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.backups li {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 2px 10px;
		padding: 2px 0;
		font-size: 13px;
	}
	.backups a {
		overflow-wrap: anywhere;
	}
	.act {
		margin-left: 6px;
		border: none;
		background: none;
		padding: 0;
		color: var(--accent);
		font-size: 12px;
		cursor: pointer;
		text-decoration: underline;
	}
	.act:disabled {
		color: var(--muted);
		cursor: default;
	}
	.act-done {
		margin-left: 6px;
		font-size: 12px;
		color: var(--up);
	}
	.keep {
		margin-left: 6px;
		max-width: 100%;
		padding: 2px 6px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface);
		font-size: 12px;
	}
	.merge-bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		margin-top: 10px;
	}
	.merge-bar span {
		margin-right: auto;
	}
	.backups a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.backups a:hover {
		color: var(--accent);
	}

</style>

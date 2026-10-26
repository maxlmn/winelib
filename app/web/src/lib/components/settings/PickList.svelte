<script lang="ts" module>
	export interface PickItem {
		label: string;
		detail: string | null;
		href: string | null;
		/** flag: one of a kind the preview names (`flag` prop, e.g. "known cuvées"): filtered or ticked alone; the
		 * rest is for the page's `row` snippet (a plug-in import's card) */
		pick: { key: string; group: string; on: boolean; flag?: boolean; [more: string]: unknown };
	}
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';

	/** A preview's suggestions to tick before running (e.g. a plug-in's import): grouped (by producer),
	 * each group folded with its own checkbox; the run gets the ticked keys. */
	interface Props {
		items: PickItem[];
		/** "Import" ... */
		verb: string;
		disabled?: boolean;
		/** what the flagged suggestions are ("known cuvées"): a filter and "Tick only known cuvées" */
		flag?: string;
		/** draws a suggestion (instead of its label and detail) */
		row?: Snippet<[PickItem]>;
		/** key -> ticked (bindable: a row can tick itself, e.g. once edited) */
		ticked?: Record<string, boolean>;
		onrun: (keys: string[]) => void;
	}
	let { items, verb, disabled = false, flag, row, ticked = $bindable({}), onrun }: Props = $props();

	let open = $state<Record<string, boolean>>({});
	let filter = $state('');
	let onlyDoubts = $state(false);
	let onlyFlagged = $state(false);
	const flagged = $derived(items.filter((it) => it.pick.flag).length);

	// A new preview: its suggestions ticked as proposed
	$effect(() => {
		ticked = Object.fromEntries(items.map((it) => [it.pick.key, it.pick.on]));
		open = {};
	});

	const groups = $derived.by(() => {
		const q = filter.trim().toLowerCase();
		const out = new Map<string, PickItem[]>();
		for (const it of items) {
			if (onlyDoubts && it.pick.on) continue;
			if (onlyFlagged && !it.pick.flag) continue;
			if (q && !`${it.pick.group} ${it.label} ${it.detail ?? ''}`.toLowerCase().includes(q)) continue;
			const g = out.get(it.pick.group) ?? [];
			g.push(it);
			out.set(it.pick.group, g);
		}
		return [...out].sort((a, b) => a[0].localeCompare(b[0]));
	});
	const count = $derived(items.reduce((n, it) => n + (ticked[it.pick.key] ? 1 : 0), 0));
	const shownCount = $derived(groups.reduce((n, [, g]) => n + g.length, 0));

	const tickedIn = (g: PickItem[]) => g.reduce((n, it) => n + (ticked[it.pick.key] ? 1 : 0), 0);
	function setAll(list: PickItem[], on: boolean) {
		const next = { ...ticked };
		for (const it of list) next[it.pick.key] = on;
		ticked = next;
	}
	const onlyTheFlagged = () => (ticked = Object.fromEntries(items.map((it) => [it.pick.key, !!it.pick.flag])));
	const suggested = () => (ticked = Object.fromEntries(items.map((it) => [it.pick.key, it.pick.on])));
	const visible = () => groups.flatMap(([, g]) => g);

	function run() {
		const keys = items.filter((it) => ticked[it.pick.key]).map((it) => it.pick.key);
		if (keys.length && confirm(`${verb} ${keys.length} wine${keys.length > 1 ? 's' : ''}?`)) onrun(keys);
	}
</script>

<div class="bar">
	<input class="filter" type="search" placeholder="Filter producers, cuvées, appellations…" bind:value={filter} />
	<label class="small"><input type="checkbox" bind:checked={onlyDoubts} /> Only those to check</label>
	{#if flag && flagged}<label class="small"><input type="checkbox" bind:checked={onlyFlagged} /> Only {flag} ({flagged})</label>{/if}
	<span class="muted small">{shownCount === items.length ? '' : `${shownCount} shown · `}{count} of {items.length} ticked</span>
	<span class="spacer"></span>
	<button class="link small" onclick={() => setAll(visible(), true)}>Tick {filter || onlyDoubts || onlyFlagged ? 'shown' : 'all'}</button>
	<button class="link small" onclick={() => setAll(visible(), false)}>Untick {filter || onlyDoubts || onlyFlagged ? 'shown' : 'all'}</button>
	<button class="link small" onclick={suggested}>As suggested</button>
	{#if flag && flagged}<button class="link small" onclick={onlyTheFlagged}>Tick only {flag}</button>{/if}
	<button class="btn primary" disabled={disabled || !count} onclick={run}>{verb} {count}</button>
</div>

<ul class="groups">
	{#each groups as [name, list] (name)}
		{@const n = tickedIn(list)}
		<li>
			<div class="group">
				<input
					type="checkbox"
					checked={n === list.length}
					indeterminate={n > 0 && n < list.length}
					onchange={(e) => setAll(list, e.currentTarget.checked)}
					aria-label="All of {name}"
				/>
				<button class="name" onclick={() => (open[name] = !open[name])} aria-expanded={!!open[name]}>
					<span class="chev" class:on={open[name]}>▸</span>
					<b>{name}</b>
					<span class="muted num">{n} of {list.length}</span>
					{#if list.some((it) => !it.pick.on)}<span class="doubt small">{list.filter((it) => !it.pick.on).length} to check</span>{/if}
				</button>
			</div>
			{#if open[name]}
				<ul class="rows">
					{#each list as it (it.pick.key)}
						{#if row}
							<li class="carded">
								<input type="checkbox" bind:checked={ticked[it.pick.key]} aria-label="Tick {it.label}" />
								<div class="card-wrap">{@render row(it)}</div>
							</li>
						{:else}
							<li class:doubtful={!it.pick.on}>
								<label>
									<input type="checkbox" bind:checked={ticked[it.pick.key]} />
									<b>{it.label}</b>
									{#if flag && it.pick.flag}<span class="tag">{flag.split(' ')[0]}</span>{/if}
									{#if it.detail}<span class="muted"> · {it.detail}</span>{/if}
								</label>
								{#if it.href}<a class="small" href={it.href} target="_blank" rel="noreferrer">review ↗</a>{/if}
							</li>
						{/if}
					{/each}
				</ul>
			{/if}
		</li>
	{:else}
		<li class="muted">Nothing matches.</li>
	{/each}
</ul>

<style>
	.bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px 12px;
		margin: 8px 0;
	}
	.filter {
		min-width: 260px;
		padding: 5px 8px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface);
		color: inherit;
		font: inherit;
	}
	.bar label {
		display: inline-flex;
		align-items: center;
		gap: 4px;
	}
	.spacer {
		flex: 1;
	}
	.small {
		font-size: 12px;
	}
	.groups {
		list-style: none;
		margin: 0;
		padding: 0;
		max-height: 70vh;
		overflow-y: auto;
		border-top: 1px solid var(--border);
	}
	.groups > li {
		border-bottom: 1px solid var(--border);
	}
	.group {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 5px 2px;
	}
	.name {
		display: flex;
		align-items: baseline;
		gap: 8px;
		flex: 1;
		background: none;
		border: none;
		padding: 0;
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: pointer;
	}
	.chev {
		display: inline-block;
		transition: transform 0.15s;
		color: var(--muted);
	}
	.chev.on {
		transform: rotate(90deg);
	}
	.doubt {
		color: var(--down);
	}
	.rows {
		list-style: none;
		margin: 0 0 6px;
		padding: 0 0 0 24px;
	}
	.rows li {
		display: flex;
		align-items: baseline;
		gap: 8px;
		padding: 2px 0;
	}
	.rows label {
		flex: 1;
		cursor: pointer;
	}
	.rows a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
		flex: none;
	}
	.rows a:hover {
		color: var(--accent);
	}
	.tag {
		font-size: 10px;
		padding: 0 5px;
		border-radius: 6px;
		background: var(--surface-2);
		border: 1px solid var(--border);
		color: var(--muted);
	}
	/* Rows drawn by the page (a wine card): the checkbox, then the card */
	.rows li.carded {
		align-items: center;
		padding: 4px 0;
	}
	.card-wrap {
		flex: 1;
		min-width: 0;
	}
	.doubtful b {
		color: var(--down);
	}
</style>

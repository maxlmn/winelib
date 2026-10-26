<script lang="ts" generics="T extends { id: number; name: string }">
	import type { Snippet } from 'svelte';
	import { filterNamed } from '#lib/api/forms.ts';
	import type { Choice } from '#lib/api/forms.ts';

	interface Props {
		id: string;
		value: Choice | null;
		/** fetches the options for a query ('' when the field gets focus)... */
		search?: (q: string) => Promise<T[]>;
		/** ...or filters these, for a short list already loaded */
		options?: T[];
		onchange: (value: Choice | null, item?: T) => void;
		placeholder?: string;
		/** offer "Create “…”" for a name that isn't listed (what to create, e.g. "producer") */
		creatable?: string;
		/** an extra last row, e.g. "New wine…" */
		action?: { label: string; run: (q: string) => void };
		hint?: (item: T) => string | null | undefined;
		/** a colour dot before the hint (a region's colour) */
		hintDot?: (item: T) => string | null | undefined;
		row?: Snippet<[T]>;
		invalid?: boolean;
		required?: boolean;
	}

	let { id, value, search, options, onchange, placeholder = '', creatable, action, hint, hintDot, row, invalid = false, required = false }: Props =
		$props();

	type Entry = { kind: 'item'; item: T } | { kind: 'create' } | { kind: 'action' };

	let text = $state('');
	let open = $state(false);
	let focused = $state(false);
	let items = $state<T[]>([]);
	let active = $state(-1);
	let loading = $state(false);
	let listEl = $state<HTMLUListElement>();
	let seq = 0;
	let timer: ReturnType<typeof setTimeout> | undefined;

	const listId = $derived(`${id}-list`);
	const shown = $derived(value?.name ?? '');
	const query = $derived(text === shown ? '' : text.trim());
	const exact = $derived(items.some((i) => i.name.toLowerCase() === query.toLowerCase()));
	const entries = $derived<Entry[]>([
		...items.map((item) => ({ kind: 'item' as const, item })),
		...(creatable && query && !exact && !loading ? [{ kind: 'create' as const }] : []),
		...(action ? [{ kind: 'action' as const }] : [])
	]);

	// Follow the value while the user isn't typing
	$effect(() => {
		const name = shown;
		if (!focused) text = name;
	});

	function show(result: T[], q: string) {
		items = result;
		loading = false;
		active = result.length && q ? 0 : -1;
	}

	function load(q: string, delay = 120) {
		clearTimeout(timer);
		const mine = ++seq;
		if (options) return show(filterNamed(options, q), q); // in memory: no need to wait
		loading = true;
		timer = setTimeout(async () => {
			const rows = (await search?.(q)) ?? [];
			if (mine === seq) show(rows, q);
		}, delay);
	}

	function choose(entry: Entry) {
		if (entry.kind === 'item') {
			onchange({ id: entry.item.id, name: entry.item.name, hint: hint?.(entry.item), dot: hintDot?.(entry.item) }, entry.item);
			text = entry.item.name;
		} else if (entry.kind === 'create') {
			const name = query;
			onchange({ id: null, name });
			text = name;
		} else action?.run(query);
		open = false;
	}

	function oninput() {
		open = true;
		load(text.trim());
	}

	function onfocus(e: FocusEvent) {
		focused = true;
		(e.currentTarget as HTMLInputElement).select();
		open = true;
		load('', 0);
	}

	function onblur() {
		focused = false;
		open = false;
		if (text.trim() === '' && value) onchange(null);
		else text = shown;
	}

	function onkeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
			e.preventDefault();
			if (!open) return oninput();
			const n = entries.length;
			const step = e.key === 'ArrowDown' ? 1 : -1;
			if (n) active = active < 0 && step < 0 ? n - 1 : (active + step + n) % n;
		} else if (e.key === 'Enter') {
			if (open && entries[active]) {
				e.preventDefault();
				choose(entries[active]);
			}
		} else if (e.key === 'Escape' && open) {
			e.preventDefault();
			e.stopPropagation();
			open = false;
			text = shown;
		}
	}

	$effect(() => {
		if (open && active >= 0) listEl?.children[active]?.scrollIntoView({ block: 'nearest' });
	});
</script>

<div class="combo">
	<input
		{id}
		type="text"
		role="combobox"
		autocomplete="off"
		aria-autocomplete="list"
		aria-expanded={open && entries.length > 0}
		aria-controls={listId}
		aria-activedescendant={open && active >= 0 ? `${id}-opt-${active}` : undefined}
		aria-invalid={invalid}
		aria-required={required}
		{placeholder}
		bind:value={text}
		{oninput}
		{onfocus}
		{onblur}
		{onkeydown}
	/>
	{#if value && !focused}
		<span class="tag" class:new={value.id === null}>{#if value.id !== null && value.dot}<span class="hint-dot" style:background={value.dot}></span>{/if}{value.id === null ? 'new' : (value.hint ?? '')}</span>
	{/if}
	{#if open && (entries.length || loading)}
		<ul class="list card" id={listId} role="listbox" bind:this={listEl}>
			{#each entries as entry, i}
				<li
					id="{id}-opt-{i}"
					role="option"
					tabindex="-1"
					aria-selected={i === active}
					class:active={i === active}
					class:extra={entry.kind !== 'item'}
					onmousedown={(e) => (e.preventDefault(), choose(entry))}
					onmousemove={() => (active = i)}
					onkeydown={() => {}}
				>
					{#if entry.kind === 'item'}
						{#if row}{@render row(entry.item)}{:else}
							<span class="name">{entry.item.name}</span>
							{#if hint?.(entry.item)}<span class="muted small">{#if hintDot?.(entry.item)}<span class="hint-dot" style:background={hintDot(entry.item)}></span>{/if}{hint(entry.item)}</span>{/if}
						{/if}
					{:else if entry.kind === 'create'}
						<span>＋ Create {creatable} “<b>{query}</b>”</span>
					{:else if action}
						<span>{action.label}</span>
					{/if}
				</li>
			{/each}
			{#if loading && !items.length}<li class="muted small" role="presentation">Searching…</li>{/if}
		</ul>
	{/if}
</div>

<style>
	.hint-dot {
		display: inline-block;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		margin-right: 4px;
		vertical-align: 0.05em;
	}
	.combo {
		position: relative;
	}
	input {
		padding-right: 58px !important;
	}
	.tag {
		position: absolute;
		right: 10px;
		top: 50%;
		transform: translateY(-50%);
		max-width: 45%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 11px;
		color: var(--muted);
		pointer-events: none;
	}
	.tag.new {
		background: var(--accent-soft);
		color: var(--accent);
		border-radius: 10px;
		padding: 1px 8px;
		font-weight: 600;
	}
	.list {
		position: absolute;
		z-index: 30;
		top: calc(100% + 4px);
		left: 0;
		right: 0;
		margin: 0;
		padding: 4px;
		list-style: none;
		max-height: 300px;
		overflow-y: auto;
	}
	li {
		display: flex;
		align-items: baseline;
		gap: 8px;
		padding: 7px 8px;
		border-radius: 6px;
		cursor: pointer;
	}
	li.active {
		background: var(--accent-soft);
	}
	li.extra {
		color: var(--accent);
		border-top: 1px solid var(--border);
		border-radius: 0 0 6px 6px;
	}
	li.extra + li.extra {
		border-top: none;
	}
	.name {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.small {
		font-size: 12px;
		white-space: nowrap;
	}
</style>

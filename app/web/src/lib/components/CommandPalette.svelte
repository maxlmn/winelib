<script lang="ts">
	import Icon, { isIcon } from '#lib/components/Icon.svelte';
	import { goto } from '$app/navigation';
	import { links } from '#lib/links.ts';
	import { regionColor } from '#lib/regions.svelte.ts';
	import { setTheme, theme } from '#lib/theme.svelte.ts';

	type Kind = 'region' | 'grape' | 'producer' | 'wine' | 'place' | 'appellation' | 'vineyard';
	interface Item {
		key: string;
		title: string;
		sub?: string;
		/** the result's region: its colour as a dot before the sub-line */
		region?: string | null;
		group: string;
		icon: string;
		run: () => void;
	}

	let { open = $bindable(false) }: { open?: boolean } = $props();

	let query = $state('');
	let results = $state<{ kind: Kind; id: number; title: string; sub: string; region?: string | null }[]>([]);
	let active = $state(0);
	let input = $state<HTMLInputElement>();
	let listEl = $state<HTMLDivElement>();

	const KIND = {
		region: { group: 'Regions', icon: 'globe', href: links.region },
		grape: { group: 'Grapes', icon: 'grape', href: links.grape },
		producer: { group: 'Producers', icon: 'person', href: links.producer },
		wine: { group: 'Wines', icon: '◍', href: links.wine },
		place: { group: 'Places', icon: '✦', href: links.place },
		appellation: { group: 'Appellations', icon: 'map', href: links.appellation },
		vineyard: { group: 'Vineyards', icon: '❦', href: links.vineyard }
	} satisfies Record<Kind, { group: string; icon: string; href: (id: number) => string }>;

	const go = (href: string) => () => goto(href);
	const COMMANDS: Omit<Item, 'key'>[] = [
		{ title: 'Cellar', group: 'Pages', icon: '▦', run: go(links.cellar()) },
		{ title: 'Tasting Notes', group: 'Pages', icon: '✎', run: go(links.tastings()) },
		{ title: 'Summary', group: 'Pages', icon: '▤', run: go(links.summary()) },
		{ title: 'Producers', group: 'Pages', icon: 'person', run: go(links.producers()) },
		{ title: 'Places', group: 'Pages', icon: '✦', run: go(links.places()) },
		{ title: 'Map', group: 'Pages', icon: 'map', run: go(links.map()) },
		{ title: 'Settings', group: 'Pages', icon: '⚙', run: go(links.settings()) },
		{ title: 'Add tasting note', group: 'Actions', icon: '+', run: go(links.newTasting()) },
		{ title: 'Add bottle', group: 'Actions', icon: '+', run: go(links.newBottle()) },
		{ title: 'Add wine', group: 'Actions', icon: '+', run: go(links.newWine()) },
		{ title: 'Add producer', group: 'Actions', icon: '+', run: go(links.newProducer()) },
		{ title: 'Add place', group: 'Actions', icon: '+', run: go(links.newPlace()) },
		{ title: 'Add restaurant visit', group: 'Actions', icon: '+', run: go(links.newVisit()) },
		{ title: 'Switch to dark mode', sub: 'Appearance', group: 'Actions', icon: '☾', run: () => setTheme({ mode: 'dark' }) },
		{ title: 'Switch to light mode', sub: 'Appearance', group: 'Actions', icon: '☀', run: () => setTheme({ mode: 'light' }) },
		{ title: 'Follow system theme', sub: 'Appearance', group: 'Actions', icon: '◐', run: () => setTheme({ mode: 'auto' }) }
	];

	const items = $derived.by((): Item[] => {
		const q = query.trim().toLowerCase();
		const commands = COMMANDS.filter((c) => !q || c.title.toLowerCase().includes(q))
			.filter((c) => !(c.icon === '☾' && theme.mode === 'dark') && !(c.icon === '☀' && theme.mode === 'light'))
			.map((c) => ({ ...c, key: `cmd:${c.title}` }));
		const found = results.map((r) => ({
			key: `${r.kind}:${r.id}`,
			title: r.title,
			sub: r.sub,
			region: r.region,
			group: KIND[r.kind].group,
			icon: KIND[r.kind].icon,
			run: go(KIND[r.kind].href(r.id))
		}));
		// With a query, matches first and commands after; without one, just the commands
		return q ? [...found, ...commands.slice(0, 6)] : commands;
	});

	$effect(() => {
		const q = query.trim();
		if (q.length < 2) {
			results = [];
			return;
		}
		const ctrl = new AbortController();
		const t = setTimeout(() => {
			fetch(`/api/search?q=${encodeURIComponent(q)}`, { signal: ctrl.signal })
				.then((r) => r.json())
				.then((d) => (results = d.results))
				.catch(() => {});
		}, 120);
		return () => {
			clearTimeout(t);
			ctrl.abort();
		};
	});

	$effect(() => {
		void items;
		active = 0;
	});

	$effect(() => {
		if (open) {
			query = '';
			results = [];
			queueMicrotask(() => input?.focus());
		}
	});

	function choose(item: Item | undefined) {
		if (!item) return;
		open = false;
		item.run();
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
			e.preventDefault();
			active = (active + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % Math.max(items.length, 1);
			listEl?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' });
		} else if (e.key === 'Enter') {
			e.preventDefault();
			choose(items[active]);
		} else if (e.key === 'Escape') {
			open = false;
		}
	}

	function onGlobalKey(e: KeyboardEvent) {
		const typing = e.target instanceof HTMLElement && e.target.closest('input, textarea, select, [contenteditable]');
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			open = !open;
		} else if (e.key === '/' && !typing && !open) {
			e.preventDefault();
			open = true;
		}
	}

	// Group headers appear where the group changes
	const showGroup = (i: number) => i === 0 || items[i - 1].group !== items[i].group;
</script>

<svelte:window onkeydown={onGlobalKey} />

{#if open}
	<div class="backdrop" role="presentation" onclick={() => (open = false)}></div>
	<div class="palette card" role="dialog" aria-modal="true" aria-label="Search">
		<div class="search">
			<span class="glass">⌕</span>
			<input
				bind:this={input}
				bind:value={query}
				onkeydown={onKey}
				placeholder="Search wines, producers, places… or type a command"
				aria-label="Search"
				role="combobox"
				aria-expanded="true"
				aria-controls="palette-list"
				aria-activedescendant={items[active] ? `palette-${active}` : undefined}
			/>
			<kbd>esc</kbd>
		</div>
		<div class="list" id="palette-list" role="listbox" bind:this={listEl}>
			{#each items as item, i (item.key)}
				{#if showGroup(i)}<div class="group">{item.group}</div>{/if}
				<button
					id="palette-{i}"
					data-index={i}
					role="option"
					aria-selected={i === active}
					class="item"
					class:active={i === active}
					onmousemove={() => (active = i)}
					onclick={() => choose(item)}
				>
					<span class="icon">{#if isIcon(item.icon)}<Icon name={item.icon} />{:else}{item.icon}{/if}</span>
					<span class="title">{item.title}</span>
					{#if item.sub}<span class="sub muted">{#if item.region}<span class="dot" style:background={regionColor(item.region)}></span>{/if}{item.sub}</span>{/if}
				</button>
			{:else}
				<div class="empty muted">{query.trim().length < 2 ? 'Type at least two letters' : 'Nothing found'}</div>
			{/each}
		</div>
		<div class="foot muted"><kbd>↑</kbd><kbd>↓</kbd> to move · <kbd>↵</kbd> to open · <kbd>⌘K</kbd> anywhere</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: color-mix(in srgb, #000 35%, transparent);
		backdrop-filter: blur(2px);
		z-index: 90;
	}
	.palette {
		position: fixed;
		top: 12vh;
		left: 50%;
		transform: translateX(-50%);
		width: min(640px, calc(100vw - 32px));
		z-index: 91;
		overflow: hidden;
		box-shadow: 0 20px 60px #0000003a;
	}
	.search {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 16px;
		border-bottom: 1px solid var(--border);
	}
	.glass {
		color: var(--muted);
		font-size: 18px;
	}
	input {
		flex: 1;
		border: none;
		background: none;
		outline: none;
		font-size: 16px;
	}
	kbd {
		font: 11px ui-monospace, monospace;
		padding: 1px 5px;
		border: 1px solid var(--border);
		border-radius: 4px;
		background: var(--surface-2);
		color: var(--muted);
	}
	.list {
		max-height: min(420px, 60vh);
		overflow-y: auto;
		padding: 6px;
	}
	.group {
		padding: 8px 10px 4px;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--muted);
	}
	.item {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		padding: 8px 10px;
		border: none;
		border-radius: 8px;
		background: none;
		text-align: left;
		cursor: pointer;
	}
	.item.active {
		background: var(--accent-soft);
	}
	.item.active .icon {
		color: var(--accent);
	}
	.icon {
		width: 18px;
		text-align: center;
		color: var(--muted);
	}
	.title {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.sub {
		margin-left: auto;
		padding-left: 12px;
		font-size: 12px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 45%;
	}
	.dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		margin-right: 5px;
		vertical-align: 0.05em;
	}
	.empty {
		padding: 18px;
		text-align: center;
		font-size: 13px;
	}
	.foot {
		display: flex;
		gap: 4px;
		align-items: center;
		padding: 8px 14px;
		border-top: 1px solid var(--border);
		font-size: 12px;
	}
</style>

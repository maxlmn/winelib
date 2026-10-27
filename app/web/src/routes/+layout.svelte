<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import { links } from '#lib/links.ts';
	import { initTheme, setTheme, theme } from '#lib/theme.svelte.ts';
	import type { Mode } from '#lib/theme.svelte.ts';
	import CommandPalette from '#lib/components/CommandPalette.svelte';
	import { warmJournal } from '#lib/api/tastings.ts';
	import { onMount } from 'svelte';
	import Icon, { isIcon } from '#lib/components/Icon.svelte';

	let { children } = $props();

	let searchOpen = $state(false);
	// On a phone the links fold behind a menu button; going to a page folds them again
	let menuOpen = $state(false);
	$effect(() => {
		void page.url.pathname;
		menuOpen = false;
	});
	const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);

	initTheme();

	// The tasting notes are the app's largest page: fetched once the app has settled, so they open at once
	onMount(() => {
		const t = setTimeout(() => ('requestIdleCallback' in window ? requestIdleCallback(warmJournal) : warmJournal()), 1500);
		return () => clearTimeout(t);
	});

	const MODES: { mode: Mode; icon: string; label: string }[] = [
		{ mode: 'auto', icon: '◐', label: 'System theme' },
		{ mode: 'light', icon: '☀', label: 'Light' },
		{ mode: 'dark', icon: '☾', label: 'Dark' }
	];
	const currentMode = $derived(MODES.find((m) => m.mode === theme.mode) ?? MODES[0]);
	const cycleMode = () => setTheme({ mode: MODES[(MODES.indexOf(currentMode) + 1) % MODES.length].mode });

	const nav = [
		{ href: links.home(), label: 'Home', icon: 'grid' },
		{ href: links.cellar(), label: 'Cellar', icon: 'bottle' },
		{ href: links.lists(), label: 'Lists', icon: 'list' },
		{ href: links.tastings(), label: 'Tasting Notes', icon: 'glass' },
		{ href: links.summary(), label: 'Summary', icon: 'chart' },
		{ href: links.producers(), label: 'Producers', icon: 'person' },
		{ href: links.grapes(), label: 'Grapes', icon: 'grape' },
		{ href: links.vintages(), label: 'Vintages', icon: 'calendar' },
		{ href: links.places(), label: 'Places', icon: 'pin' },
		{ href: links.map(), label: 'Map', icon: 'map' }
	];
</script>

<div class="shell">
	<nav>
		<a class="brand" href={links.home()}>🍷 <span>WineLib</span></a>
		<button class="search-btn" onclick={() => (searchOpen = true)}>
			<span>⌕ Search…</span><kbd>{isMac ? '⌘' : 'Ctrl'} K</kbd>
		</button>
		<button class="menu-btn" onclick={() => (menuOpen = !menuOpen)} aria-expanded={menuOpen} aria-label="Menu">
			{menuOpen ? '✕' : '☰'}
		</button>
		<div class="items" class:open={menuOpen}>
		{#each nav as item}
			<a class="item" class:active={item.href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(item.href)} href={item.href}>
				<span class="icon">{#if isIcon(item.icon)}<Icon name={item.icon} size={15} />{:else}{item.icon}{/if}</span><span>{item.label}</span>
			</a>
		{/each}
		<a class="item settings" class:active={page.url.pathname.startsWith(links.help())} href={links.help()}>
			<span class="icon"><Icon name="help" size={15} /></span><span>Help</span>
		</a>
		<a class="item" class:active={page.url.pathname.startsWith(links.settings())} href={links.settings()}>
			<span class="icon"><Icon name="sliders" size={15} /></span><span>Settings</span>
		</a>
		</div>
		<div class="foot">
			<button class="mode" onclick={cycleMode} title="{currentMode.label} (click to change)" aria-label="Theme: {currentMode.label}">
				{currentMode.icon}
			</button>
		</div>
	</nav>
	<main>{@render children()}</main>
</div>

<CommandPalette bind:open={searchOpen} />

<style>
	.shell {
		display: grid;
		grid-template-columns: 200px 1fr;
		min-height: 100vh;
	}
	nav {
		position: sticky;
		top: 0;
		height: 100vh;
		padding: 18px 12px;
		border-right: 1px solid var(--border);
		background: var(--surface);
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.brand {
		font-weight: 700;
		font-size: 17px;
		padding: 4px 10px 14px;
		font-family: var(--heading-font);
	}
	.search-btn {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin: 0 2px 12px;
		padding: 7px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
		color: var(--muted);
		cursor: pointer;
		font-size: 13px;
	}
	.search-btn:hover {
		border-color: var(--accent);
		color: var(--text);
	}
	.search-btn kbd {
		font: 10px ui-monospace, monospace;
		padding: 1px 4px;
		border: 1px solid var(--border);
		border-radius: 4px;
		background: var(--surface);
	}
	.foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.mode {
		width: 30px;
		height: 30px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface);
		color: var(--muted);
		cursor: pointer;
		font-size: 15px;
	}
	.mode:hover {
		color: var(--accent);
		border-color: var(--accent);
	}
	.item {
		display: flex;
		gap: 10px;
		align-items: center;
		padding: 7px 10px;
		border-radius: 8px;
		color: var(--muted);
	}
	.item:hover {
		background: var(--surface-2);
		color: var(--text);
	}
	.item.active {
		background: var(--accent-soft);
		color: var(--accent);
		font-weight: 600;
	}
	.icon {
		width: 16px;
		text-align: center;
	}
	.settings {
		margin-top: auto;
	}
	.items {
		display: contents;
	}
	.menu-btn {
		display: none;
	}
	main {
		padding: 24px 28px 60px;
		min-width: 0;
	}
	@media (max-width: 760px) {
		.shell {
			grid-template-columns: 1fr;
			/* the bar its own height, the page the rest (a short page, an error, mustn't stretch the bar) */
			grid-template-rows: auto 1fr;
		}
		/* A slim bar: the brand, search, theme and the menu button; the links open under it */
		nav {
			z-index: 20;
			height: auto;
			flex-direction: row;
			flex-wrap: wrap;
			align-items: center;
			gap: 8px;
			padding: 8px 16px;
			border-right: none;
			border-bottom: 1px solid var(--border);
		}
		.brand {
			padding: 4px 4px 4px 0;
		}
		.search-btn kbd {
			display: none;
		}
		.search-btn {
			flex: 1;
			margin: 0;
		}
		.menu-btn {
			display: block;
			order: 1;
			width: 34px;
			height: 30px;
			border: 1px solid var(--border);
			border-radius: 8px;
			background: var(--surface);
			color: var(--text);
			cursor: pointer;
			font-size: 15px;
		}
		.items {
			display: none;
			order: 2;
			width: 100%;
			grid-template-columns: 1fr 1fr;
			gap: 2px;
			padding: 6px 0 4px;
		}
		.items.open {
			display: grid;
		}
		.settings {
			margin-top: 0;
		}
		main {
			padding: 16px;
		}
	}
</style>

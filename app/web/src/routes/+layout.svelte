<script lang="ts">
	import '../app.css';
	import Logo from '#lib/components/Logo.svelte';
	import { navigating, page } from '$app/state';
	import { links } from '#lib/links.ts';
	import { initTheme, setTheme, theme } from '#lib/theme.svelte.ts';
	import type { Mode } from '#lib/theme.svelte.ts';
	import AskDialog from '#lib/components/AskDialog.svelte';
	import Lightbox from '#lib/components/Lightbox.svelte';
	import CommandPalette from '#lib/components/CommandPalette.svelte';
	import { warmJournal } from '#lib/api/tastings.ts';
	import { onMount } from 'svelte';
	import Icon, { isIcon } from '#lib/components/Icon.svelte';
	import { DEMO } from '#lib/demo.ts';

	let { children } = $props();

	let searchOpen = $state(false);
	// On a phone the links fold behind a menu button; going to a page folds them again
	let menuOpen = $state(false);
	// The phone's bar height (its menu closed), for what sits under it: a full-size map (DetailMap)
	let navHeight = $state(0);
	$effect(() => {
		if (!menuOpen && navHeight) document.documentElement.style.setProperty('--nav-h', `${navHeight}px`);
	});
	$effect(() => {
		void page.url.pathname;
		menuOpen = false;
	});
	// A phone's bar at the bottom, within the thumb's reach: the pages opened most, a bottle or a tasting added,
	// search. Not on a form (its own Save and Cancel sit there)
	let addOpen = $state(false);
	const onForm = $derived(/\/(new|edit)$/.test(page.url.pathname) || page.url.pathname === '/welcome');
	$effect(() => {
		void page.url.pathname;
		addOpen = false;
	});
	const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);

	initTheme();

	// The tasting notes are the app's largest page: fetched once the app has settled, so they open at once
	onMount(() => {
		document.getElementById('boot')?.remove(); // app.html's first screen
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

<!-- A page that waits for its data: the bar says it's coming (a click showed nothing until it did) -->
{#if navigating.to}<div class="progress" role="progressbar" aria-label="Loading the page"></div>{/if}

<a class="skip" href="#main">Skip to the page</a>
<div class="shell">
	<nav bind:offsetHeight={navHeight} aria-label="Pages">
		<a class="brand" href={links.home()}><Logo size={24} /><span>WineLib</span></a>
		<button class="search-btn" onclick={() => (searchOpen = true)}>
			<span>⌕ Search…</span><kbd>{isMac ? '⌘' : 'Ctrl'} K</kbd>
		</button>
		<button class="menu-btn" onclick={() => (menuOpen = !menuOpen)} aria-expanded={menuOpen} aria-label="Menu">
			{menuOpen ? '✕' : '☰'}
		</button>
		<div class="items" class:open={menuOpen}>
		{#each nav as item}
			{@const here = item.href === links.home() ? page.url.pathname === links.home() : page.url.pathname.startsWith(item.href)}
			<a class="item" class:active={here} aria-current={here ? 'page' : undefined} href={item.href}>
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
	<main id="main" tabindex="-1">
		{#if DEMO}
			<p class="demo">
				The demo: a sample cellar, read-only (nothing you change is kept).
				<a href="https://maxlmn.github.io/winelib/install/">Install WineLib</a> for your own.
			</p>
		{/if}
		{@render children()}
	</main>
</div>

{#if !onForm}
	<div class="tabbar" role="navigation" aria-label="Shortcuts">
		<a class="tab" class:active={page.url.pathname === links.home()} href={links.home()}><Icon name="grid" size={20} /><span>Home</span></a>
		<a class="tab" class:active={page.url.pathname.startsWith(links.cellar())} href={links.cellar()}><Icon name="bottle" size={20} /><span>Cellar</span></a>
		<div class="add">
			{#if addOpen}
				<div class="add-menu">
					<a href={links.newBottle()}><Icon name="bottle" size={16} />Add a bottle</a>
					<a href={links.newTasting()}><Icon name="glass" size={16} />Add a tasting</a>
					<a href={links.newVisit()}><Icon name="pin" size={16} />Add a restaurant visit</a>
				</div>
			{/if}
			<button class="plus" class:open={addOpen} onclick={() => (addOpen = !addOpen)} aria-expanded={addOpen} aria-label="Add">+</button>
		</div>
		<a class="tab" class:active={page.url.pathname.startsWith(links.tastings())} href={links.tastings()}><Icon name="glass" size={20} /><span>Tastings</span></a>
		<button class="tab" onclick={() => (searchOpen = true)}><Icon name="search" size={20} /><span>Search</span></button>
	</div>
{/if}

<CommandPalette bind:open={searchOpen} />
<AskDialog />
<Lightbox />

<style>
	.progress {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		height: 3px;
		z-index: 200;
		background: var(--accent);
		transform-origin: left;
		opacity: 0;
		/* after a moment (a quick page shows none), then towards the end without reaching it */
		animation: progress 8s 0.15s cubic-bezier(0.1, 0.8, 0.2, 1) forwards;
	}
	@keyframes progress {
		0% {
			opacity: 1;
			transform: scaleX(0);
		}
		100% {
			opacity: 1;
			transform: scaleX(0.95);
		}
	}
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
		display: flex;
		align-items: center;
		gap: 8px;
		font-weight: 700;
		font-size: 17px;
		padding: 4px 10px 14px;
		font-family: var(--heading-font);
		color: var(--text);
		text-decoration: none;
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
	.tabbar {
		display: none;
	}
	main {
		padding: 24px 28px 60px;
		min-width: 0;
		outline: none;
	}
	.demo {
		margin: -8px 0 16px;
		padding: 8px 12px;
		border-radius: 8px;
		background: var(--accent-soft);
		font-size: 0.85rem;
	}
	@media (max-width: 760px) {
		.shell {
			grid-template-columns: 1fr;
			/* the bar its own height, the page the rest (a short page, an error, mustn't stretch the bar) */
			grid-template-rows: auto 1fr;
		}
		/* above a page's full-size map (DetailMap), which starts under it */
		:global(html.map-full) nav {
			z-index: 45;
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
		/* the bar at the bottom has Search: the top one keeps the brand, the theme and the menu */
		:global(:root:has(.tabbar)) .search-btn {
			display: none;
		}
		:global(:root:has(.tabbar)) .brand {
			margin-right: auto;
		}
		.mode {
			width: 40px;
			height: 40px;
		}
		.menu-btn {
			display: block;
			order: 1;
			width: 40px;
			height: 40px;
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
			padding: 16px 16px calc(16px + var(--tab-h));
		}
		/* The bar at the bottom: above a page's full-size map and its cards, under the dialogs */
		.tabbar {
			position: fixed;
			left: 0;
			right: 0;
			bottom: 0;
			z-index: 46;
			display: grid;
			grid-template-columns: repeat(5, 1fr);
			align-items: center;
			height: calc(56px + env(safe-area-inset-bottom, 0px));
			padding: 0 4px env(safe-area-inset-bottom, 0px);
			background: var(--surface);
			border-top: 1px solid var(--border);
		}
		.tab {
			display: flex;
			flex-direction: column;
			align-items: center;
			justify-content: center;
			gap: 2px;
			height: 100%;
			border: 0;
			background: none;
			color: var(--muted);
			font: inherit;
			font-size: 11px;
			cursor: pointer;
		}
		.tab.active {
			color: var(--accent);
			font-weight: 600;
		}
		.add {
			position: relative;
			display: grid;
			place-items: center;
		}
		.plus {
			width: 44px;
			height: 44px;
			border: 0;
			border-radius: 50%;
			background: var(--accent);
			color: var(--on-accent);
			font-size: 26px;
			line-height: 1;
			cursor: pointer;
			transition: transform 0.15s;
		}
		.plus.open {
			transform: rotate(45deg);
		}
		.add-menu {
			position: absolute;
			bottom: 54px;
			left: 50%;
			transform: translateX(-50%);
			display: flex;
			flex-direction: column;
			min-width: 210px;
			padding: 6px;
			background: var(--surface);
			border: 1px solid var(--border);
			border-radius: 12px;
			box-shadow: var(--shadow);
		}
		.add-menu a {
			display: flex;
			align-items: center;
			gap: 10px;
			padding: 11px 12px;
			border-radius: 8px;
			color: var(--text);
		}
		.add-menu a:active {
			background: var(--surface-2);
		}
	}
</style>

<script lang="ts" module>
	export interface Tab {
		id: string;
		label: string;
		count?: number;
		/** after the count, small: the cellar's value */
		note?: string;
	}
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	interface Props {
		tabs: Tab[];
		/** shown when the URL names no (valid) tab */
		initial?: string;
		/** extra controls at the right of the tab bar */
		tools?: Snippet;
		/** the bar alone, no card around the content (a page of cards: Settings) */
		plain?: boolean;
		/** the tabs whose content is cards of its own: shown on the page itself, not as boxes in the panel's box
		 * (none by default: a cellar's and a history's are plain rows) */
		cards?: string[];
		children: Snippet<[string]>;
	}

	let { tabs, initial, tools, plain = false, cards = [], children }: Props = $props();

	// The open tab lives in the URL (?tab=), so reloads and links keep it
	const active = $derived.by(() => {
		const asked = page.url.searchParams.get('tab');
		return tabs.find((t) => t.id === asked)?.id ?? initial ?? tabs[0]?.id;
	});

	const open_ = $derived(!plain && cards.includes(active ?? ''));

	function open(id: string) {
		const p = new URLSearchParams(page.url.searchParams.toString());
		p.set('tab', id);
		goto(`?${p}`, { replace: true, reset: false });
	}
</script>

<section class="panel" class:card={!plain && !open_} class:plain class:open={open_}>
	<div class="tabs" role="tablist">
		{#each tabs as t (t.id)}
			<button role="tab" aria-selected={active === t.id} class:on={active === t.id} onclick={() => open(t.id)}>
				{t.label}{#if t.count !== undefined}<span class="count num">{t.count}</span>{/if}{#if t.note}<span class="count num">· {t.note}</span>{/if}
			</button>
		{/each}
		{#if tools}<div class="tools">{@render tools()}</div>{/if}
	</div>
	<div class="body">{@render children(active)}</div>
</section>

<style>
	.panel {
		margin-bottom: 14px;
	}
	.tabs {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 4px;
		padding: 8px 10px 0;
		border-bottom: 1px solid var(--border);
	}
	.tabs button {
		border: none;
		background: none;
		padding: 8px 12px;
		cursor: pointer;
		color: var(--muted);
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
	}
	.tabs button.on {
		color: var(--text);
		border-bottom-color: var(--accent);
		font-weight: 600;
	}
	.count {
		margin-left: 6px;
		font-size: 12px;
		color: var(--muted);
		font-weight: 400;
	}
	.tools {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 4px 2px 6px;
		font-size: 13px;
	}
	.body {
		padding: 16px;
	}
	.plain .tabs {
		padding: 0;
		margin-bottom: 14px;
	}
	.plain .body {
		padding: 0;
	}
	.open .tabs {
		padding: 0;
	}
	.open .body {
		padding: 14px 0 0;
	}
	/* over a page's full-size map the bar needs a ground of its own */
	:global(html.map-full) .open .tabs {
		padding: 4px 10px 0;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: var(--shadow);
	}
</style>

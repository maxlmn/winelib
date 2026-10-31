<script lang="ts">
	import { onMount } from 'svelte';
	import { request } from '#lib/api/http.ts';
	import { links } from '#lib/links.ts';

	/** Settings › Needs attention (GET /api/attention): what the quick Maintenance checks found, warnings first; each
	 * line opens its task in the Maintenance tab with its preview started. Checked again each time the tab opens (a task
	 * run meanwhile fixed some), the tab's count with it (`items`, bound). */
	export interface AttentionItem {
		id: string;
		level: 'warn' | 'info';
		title: string;
		detail: string;
		count: number;
		task: string;
	}
	let { items = $bindable() }: { items: AttentionItem[] | null } = $props();  // null: its checks still running

	onMount(() => {
		request<{ items: AttentionItem[] }>('/api/attention').then((r) => (items = r.items)).catch(() => {});
	});
</script>

<section class="card attention" aria-label="Needs attention">
	<h2>Needs attention</h2>
	{#if items === null}
		<p class="muted intro">Checking…</p>
	{:else if items.length}
		<p class="muted intro">What the quick checks found in your data. Each opens its Maintenance task with a preview, nothing changed until you run it.</p>
		<ul>
			{#each items as it (it.id)}
				<li class={it.level}>
					<span class="dot" aria-hidden="true"></span>
					<a href={links.maintenance(it.task)} title="Open it in Settings › Maintenance, its preview started">
						<b>{it.title}</b>
						<span class="muted detail">{it.detail}</span>
					</a>
					<span class="go" aria-hidden="true">Review →</span>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="muted">All clear: no duplicates, no orphans, nothing missing that a check looks for.</p>
	{/if}
</section>

<style>
	.attention {
		grid-column: 1 / -1;
		padding: 16px 18px;
	}
	.intro {
		margin: 0 0 8px;
		font-size: 13px;
	}
	h2 {
		margin: 0 0 6px;
		font-size: 15px;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		display: flex;
		align-items: baseline;
		gap: 10px;
		padding: 5px 0;
		font-size: 13px;
	}
	li + li {
		border-top: 1px solid var(--border);
	}
	.dot {
		flex: none;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--muted);
		align-self: center;
	}
	.warn .dot {
		background: var(--gold);
	}
	a {
		flex: 1;
		min-width: 0;
		color: inherit;
		text-decoration: none;
		display: flex;
		flex-wrap: wrap;
		gap: 2px 8px;
	}
	a:hover b {
		color: var(--accent);
	}
	.detail {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.go {
		flex: none;
		font-size: 12px;
		color: var(--accent);
	}
</style>

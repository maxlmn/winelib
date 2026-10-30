<script lang="ts">
	import { links } from '#lib/links.ts';

	/** Needs attention (GET /api/attention): what the quick Maintenance checks found, warnings first; each line opens
	 * its task in Settings › Maintenance with its preview started. Nothing shown when all is well. */
	export interface AttentionItem {
		id: string;
		level: 'warn' | 'info';
		title: string;
		detail: string;
		count: number;
		task: string;
	}
	let { items }: { items: AttentionItem[] } = $props();
</script>

{#if items.length}
	<section class="card attention" aria-label="Needs attention">
		<h2>Needs attention</h2>
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
	</section>
{/if}

<style>
	.attention {
		margin-bottom: 14px;
		padding: 12px 16px;
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

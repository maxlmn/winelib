<script lang="ts" module>
	export interface Bar {
		key: string | number;
		label: string;
		count: number;
		color: string;
		href?: string;
	}
</script>

<script lang="ts">
	/** Labelled horizontal bars, each as a share of `total`; the first `limit`, the rest on demand. `pill` shows
	 * each label tinted with its color (regions) */
	let { bars, total, unit, limit = 5, pill = false }: { bars: Bar[]; total: number; unit: string; limit?: number; pill?: boolean } =
		$props();
	let all = $state(false);
	const shown = $derived(all ? bars : bars.slice(0, limit));

	const share = (n: number) => (total ? (n / total) * 100 : 0);
	// Bars are scaled to the largest so short lists stay readable; the label carries the true share
	const peak = $derived(Math.max(1, ...bars.map((b) => b.count)));
</script>

<ul>
	{#each shown as b (b.key)}
		<li title="{b.label}: {b.count} {unit} ({share(b.count).toFixed(1)}%)">
			<div class="line">
				{#if b.href}<a class="name" class:pill href={b.href} style:--c={b.color}>{b.label}</a>{:else}<span class="name" class:pill style:--c={b.color}>{b.label}</span>{/if}
				<span class="muted num">{b.count} <span class="pct">· {share(b.count).toFixed(1)}%</span></span>
			</div>
			<div class="track"><div class="fill" style:width="{(b.count / peak) * 100}%" style:background={b.color}></div></div>
		</li>
	{:else}
		<li class="muted">Nothing yet.</li>
	{/each}
</ul>
{#if bars.length > limit}
	<button class="more" onclick={() => (all = !all)}>{all ? 'Show fewer' : `Show all ${bars.length}`}</button>
{/if}

<style>
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 9px;
	}
	.line {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		font-size: 13px;
		margin-bottom: 3px;
	}
	.name {
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.pill {
		padding: 0 8px;
		border-radius: 10px;
		background: color-mix(in srgb, var(--c) 28%, transparent);
		box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 55%, transparent);
	}
	.more {
		margin-top: 10px;
		padding: 0;
		border: none;
		background: none;
		color: var(--link);
		font-size: 12px;
		cursor: pointer;
	}
	.more:hover {
		color: var(--accent);
	}
	.num {
		white-space: nowrap;
		font-size: 12px;
	}
	.pct {
		opacity: 0.75;
	}
	.track {
		height: 8px;
		border-radius: 4px;
		background: var(--surface-2);
	}
	.fill {
		height: 100%;
		min-width: 3px;
		border-radius: 4px;
		box-shadow: inset 0 0 0 1px #00000024;
	}
</style>

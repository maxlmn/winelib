<script lang="ts" module>
	export interface Stat {
		label: string;
		value: string | number;
		sub?: string;
		/** gold: something you hold in the cellar */
		gold?: boolean;
	}
</script>

<script lang="ts">
	let { items }: { items: Stat[] } = $props();
</script>

<div class="stats">
	{#each items as s (s.label)}
		<div class="stat">
			<div class="label">{s.label}</div>
			<div class="value num" class:gold={s.gold}>{s.value}</div>
			{#if s.sub}<div class="sub muted">{s.sub}</div>{/if}
		</div>
	{/each}
</div>

<style>
	.stats {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
		gap: 10px;
	}
	.stat {
		padding: 10px 14px;
		border-radius: 8px;
		background: var(--surface-2);
	}
	.label {
		font-size: 12px;
		color: var(--muted);
	}
	.value {
		font-size: 20px;
		font-weight: 650;
		letter-spacing: -0.01em;
	}
	.value.gold {
		color: var(--gold);
	}
	.sub {
		font-size: 12px;
	}
</style>

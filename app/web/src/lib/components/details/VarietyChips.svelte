<script lang="ts">
	/** An appellation's authorized varieties as chips: each one its grape in the database, linked (the register's own
	 * spelling in its tooltip when it differs: INAO's "Cinsaut" is Cinsault), or as the register names it when the
	 * database has no such grape; a dot in the berries' colour. The API reads them (varieties.py). */
	import type { Variety } from '#lib/api/details.ts';
	import { links } from '#lib/links.ts';

	let { varieties }: { varieties: Variety[] } = $props();
	const fold = (s: string) => s.normalize('NFKD').replace(/[^\w]/g, '').toLowerCase();
</script>

<div class="chips">
	{#each varieties as v, i (i)}
		<!-- the grape's name, but the register's when it's the grape's and more ("Piquepoul Noir", "Grolleau Gris") -->
		{@const label = v.grape && !fold(v.name).startsWith(fold(v.grape)) ? v.grape : v.name}
		{#if v.grape}
			<a class="chip" href={links.grape(v.grape)} title={label !== v.name ? `${v.name} in the specification` : label !== v.grape ? v.grape : undefined}>
				{#if v.colour}<span class="dot {v.colour}" aria-hidden="true"></span>{/if}{label}
			</a>
		{:else}
			<span class="chip plain" title="No grape of this name in WineLib">
				{#if v.colour}<span class="dot {v.colour}" aria-hidden="true"></span>{/if}{v.name}
			</span>
		{/if}
	{/each}
</div>

<style>
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		margin-top: 8px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 1px 9px;
		border-radius: 10px;
		background: var(--surface-2);
		border: 1px solid var(--border);
		font-size: 12px;
		color: var(--text);
		text-decoration: none;
	}
	a.chip:hover {
		border-color: var(--accent);
		color: var(--link);
	}
	.chip.plain {
		color: var(--muted);
		background: none;
	}
	.dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex: none;
	}
	.white {
		background: #d8c77a;
	}
	.red {
		background: #7a2140;
	}
	:global(html[data-theme='dark']) .red {
		background: #c4506f;
	}
	.grey {
		background: #a7909a;
	}
	.pink {
		background: #e29bb3;
	}
</style>

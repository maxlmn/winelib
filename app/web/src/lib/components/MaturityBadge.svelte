<script lang="ts">
	import { MATURITY_LABEL, windowLabel } from '#lib/maturity.ts';
	import type { Maturity } from '#lib/maturity.ts';

	/** Where a wine stands in its drinking window, as the same small arrow everywhere (cellar, home, wine page):
	 * → ready, ↓ past it, ↗ still too young; the label and the window on hover */
	let {
		maturity,
		from = null,
		to = null,
		left = null
	}: { maturity: Maturity; from?: number | null; to?: number | null; /** years left in the window, for the hover */ left?: number | null } =
		$props();
	const ARROW = { ready: '→', past: '↓', young: '↗' } as const;
	const window = $derived(windowLabel(from, to));
</script>

{#if maturity}
	{@const yearsLeft = maturity === 'ready' && left !== null ? (left === 0 ? 'last year' : left === 1 ? '1 year left' : `${left} years left`) : ''}
	{@const label = [MATURITY_LABEL[maturity], window && `drink ${window}`, yearsLeft].filter(Boolean).join(' · ')}
	<span class="mat {maturity}" title={label} aria-label={label}>{ARROW[maturity]}</span>
{/if}

<style>
	.mat {
		flex: none;
		display: inline-grid;
		place-items: center;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		font-size: 11px;
		font-weight: 700;
		line-height: 1;
		vertical-align: 1px;
	}
	.ready {
		color: var(--up);
		box-shadow: inset 0 0 0 1px currentColor;
	}
	.past {
		color: var(--down);
		box-shadow: inset 0 0 0 1px currentColor;
	}
	.young {
		color: var(--muted);
		box-shadow: inset 0 0 0 1px var(--border);
	}
</style>

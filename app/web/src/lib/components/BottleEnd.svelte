<script lang="ts">
	import { FALLBACK_REGION, typeColor } from '#lib/colors.ts';
	import { endScale } from '#lib/format.ts';

	/** A bottle seen end-on, as in the cellar's rack: its region's color, the wine's color as the cork. `size` is a
	 * 75cl bottle's diameter; with a `format` it follows the volume (a magnum ~1.4x, a half bottle smaller) */
	let {
		region,
		color,
		format = null,
		size = 14,
		title
	}: { region: string | null | undefined; color: string | null | undefined; format?: string | null; size?: number; title?: string } =
		$props();
	const d = $derived(Math.round(size * endScale(format)));
</script>

<span
	class="end"
	{title}
	style:--d="{d}px"
	style:--region={region || FALLBACK_REGION}
	style:--wine={color ? typeColor(color) : 'transparent'}
	aria-hidden={title ? undefined : 'true'}
></span>

<style>
	.end {
		display: inline-block;
		position: relative;
		flex: none;
		width: var(--d);
		height: var(--d);
		border-radius: 50%;
		background: var(--region);
		/* a hairline, so pale regions (England's white) still show on a light page */
		box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--text) 14%, transparent);
		vertical-align: middle;
	}
	.end::after {
		content: '';
		position: absolute;
		inset: 32%;
		border-radius: 50%;
		background: var(--wine);
	}
</style>

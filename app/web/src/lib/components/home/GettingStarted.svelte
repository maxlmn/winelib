<script lang="ts">
	/** The home page of a new installation: what to do first, each step ticked when it's done. Shown while the cellar
	 * and the journal are empty or the maps have no outlines, until it's put away (on this device). */
	import { links } from '#lib/links.ts';
	import { integrations } from '#lib/settings.svelte.ts';

	let { bottles, tastings }: { bottles: number; tastings: number } = $props();

	const KEY = 'winelib-getting-started';
	let hidden = $state(false);
	try {
		hidden = localStorage.getItem(KEY) === 'hidden';
	} catch {
		// private mode: shown
	}
	function hide() {
		hidden = true;
		try {
			localStorage.setItem(KEY, 'hidden');
		} catch {
			// not kept: shown again next time
		}
	}

	const steps = $derived([
		{
			done: integrations.mapCredits.length > 0,
			title: 'Download the map outlines',
			what: 'The appellations, vineyards and lieux-dits on the maps: a download of about 75 MB, once.',
			href: links.maintenance('map_pack'),
			action: 'Download them'
		},
		{
			done: bottles > 0 || tastings > 0,
			title: 'Bring in your cellar',
			what: 'A CellarTracker or Vivino export, or your own spreadsheet: your wines, bottles and tastings.',
			href: links.maintenance('cellar_csv'),
			action: 'Import a file'
		},
		{
			done: bottles > 0,
			title: 'Or add a bottle',
			what: 'Type its name, or fill it from a shop’s page or a photo of the label.',
			href: links.newBottle(),
			action: 'Add a bottle'
		},
		{
			done: false,
			title: 'Find your way around',
			what: 'What each page does, in a few minutes.',
			href: links.help('first-steps'),
			action: 'First steps'
		}
	]);
</script>

{#if !hidden}
	<section class="card start" aria-labelledby="start-title">
		<div class="head">
			<h2 id="start-title">Getting started</h2>
			<button class="link quiet" onclick={hide}>Hide this</button>
		</div>
		<ol>
			{#each steps as s (s.title)}
				<li class:done={s.done}>
					<span class="mark" aria-hidden="true">{#if s.done}✓{/if}</span>
					<div class="text">
						<b>{s.title}</b>{#if s.done}<span class="sr-only"> (done)</span>{/if}
						<span class="muted">{s.what}</span>
					</div>
					{#if !s.done}<a class="btn" href={s.href}>{s.action}</a>{/if}
				</li>
			{/each}
		</ol>
	</section>
{/if}

<style>
	.start {
		margin-bottom: 14px;
		padding: 16px 18px;
	}
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 12px;
		margin-bottom: 8px;
	}
	h2 {
		margin: 0;
		font-size: 17px;
	}
	.quiet {
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		font-size: 12px;
		color: var(--muted);
		cursor: pointer;
	}
	.quiet:hover {
		color: var(--accent);
	}
	ol {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 0;
	}
	li + li {
		border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
	}
	.mark {
		display: grid;
		place-items: center;
		flex: none;
		width: 22px;
		height: 22px;
		border: 1.5px solid var(--border);
		border-radius: 50%;
		color: var(--on-accent);
		font-size: 12px;
		font-weight: 700;
	}
	.done .mark {
		border-color: var(--accent);
		background: var(--accent);
	}
	.text {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-width: 0;
		font-size: 13px;
	}
	.done .text b {
		color: var(--muted);
		font-weight: 500;
		text-decoration: line-through;
	}
	.btn {
		flex: none;
	}
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
	}
	@media (max-width: 560px) {
		li {
			flex-wrap: wrap;
		}
		.btn {
			margin-left: 34px;
		}
	}
</style>

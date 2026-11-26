<script lang="ts">
	/** A vineyard's geology (routers/geology.py): the formations under its outline, a bar in the geological map's own
	 * colours sized by their shares, then each named as the map publishes it; the map and its scale under them.
	 * Nothing shown without an outline or a map there. */
	import { quietly, request } from '#lib/api/http.ts';
	import { links } from '#lib/links.ts';

	type Unit = { notation: string | null; name: string; colour: string | null; share: number; lithology?: string | null; age?: string | null };
	type Geology = { source: 'brgm' | 'macrostrat'; scale: string | null; units: Unit[] };

	let { vineyardId, rev = 0 }: { vineyardId: number; rev?: number } = $props();

	let geology = $state<Geology | null>(null);
	let all = $state(false);
	$effect(() => {
		const id = vineyardId;
		void rev;
		geology = null;
		all = false;
		const abort = new AbortController(); // an answer for an earlier vineyard or outline never lands
		request<Geology | null>(`/api/vineyards/${id}/geology`, { signal: abort.signal })
			.then((g) => (geology = g))
			.catch(quietly);
		return () => abort.abort();
	});

	const SHOWN = 4;
	const pct = (s: number) => (s >= 0.995 ? '100%' : s < 0.01 ? '<1%' : `${Math.round(s * 100)}%`);
	const source = (g: Geology) =>
		g.source === 'brgm'
			? { label: `BRGM geological map, ${g.scale}`, href: 'https://infoterre.brgm.fr' }
			: { label: `Macrostrat, regional map${g.scale ? ` (${g.scale})` : ''}`, href: 'https://macrostrat.org' };
</script>

{#if geology?.units.length}
	{@const g = geology}
	{@const shown = all ? g.units : g.units.slice(0, SHOWN)}
	<section class="geology" aria-label="Geology">
		<div class="head"><span class="muted">Geology</span></div>
		{#if g.source === 'brgm'}
			<div class="bar" aria-hidden="true">
				{#each g.units as u, i (i)}<span style:flex-grow={u.share} style:background={u.colour ?? 'var(--border)'} title={`${pct(u.share)} ${u.name}`}></span>{/each}
			</div>
		{/if}
		<ul>
			{#each shown as u, i (i)}
				<li>
					<span class="sw" style:background={u.colour ?? 'var(--border)'} aria-hidden="true"></span>
					{#if g.source === 'brgm'}<span class="share num">{pct(u.share)}</span>{/if}
					<span class="name">
						<!-- BRGM's notations: some in a symbol font's letters ("pã3" for pγ3), only plain ones shown -->
						{#if u.notation && /^[ -~]+$/.test(u.notation)}<span class="notation">{u.notation}</span>{/if}
						{u.name}{#if u.age && !u.name.includes(u.age)}<span class="muted">, {u.age}</span>{/if}
					</span>
				</li>
			{/each}
		</ul>
		{#if g.units.length > SHOWN}
			<button class="more" onclick={() => (all = !all)}>{all ? 'Fewer' : `${g.units.length - SHOWN} more`}</button>
		{/if}
		<div class="source muted">
			{#if g.source === 'brgm'}Shares of the outline ·{" "}{/if}<a href={source(g).href} target="_blank" rel="noreferrer">{source(g).label}</a>
			· <a href={links.help('geology')}>Reading the geology</a>
		</div>
	</section>
{/if}

<style>
	.geology {
		margin-top: 12px;
		font-size: 13px;
	}
	.head {
		margin-bottom: 6px;
	}
	.bar {
		display: flex;
		height: 10px;
		border-radius: 5px;
		overflow: hidden;
		gap: 1px;
		background: var(--border);
		margin-bottom: 8px;
	}
	.bar span {
		flex-basis: 0;
		min-width: 2px;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	li {
		display: flex;
		align-items: baseline;
		gap: 8px;
		line-height: 1.35;
	}
	.sw {
		flex: none;
		width: 10px;
		height: 10px;
		border-radius: 2px;
		border: 1px solid color-mix(in srgb, var(--text) 15%, transparent);
		transform: translateY(1px);
	}
	.share {
		flex: none;
		width: 34px;
		text-align: right;
		color: var(--muted);
	}
	.notation {
		font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
		font-size: 11px;
		font-weight: 600;
		margin-right: 4px;
	}
	.more {
		margin-top: 4px;
		padding: 0;
		border: none;
		background: none;
		color: var(--link);
		font-size: 12px;
		cursor: pointer;
	}
	.source {
		margin-top: 6px;
		font-size: 11px;
	}
	.source a {
		color: inherit;
		text-decoration: underline;
		text-decoration-color: var(--border);
	}
</style>

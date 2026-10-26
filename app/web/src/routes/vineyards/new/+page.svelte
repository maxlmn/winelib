<script lang="ts">
	import RegionName from '#lib/components/RegionName.svelte';
	import { goto } from '$app/navigation';
	import OutlineEditor from '#lib/components/details/OutlineEditor.svelte';
	import { links } from '#lib/links.ts';

	/** A vineyard drawn from a wine's page: created with its outline and linked to the wine (and its other vintages
	 * without one): routers/outlines.py create_vineyard */
	let { data } = $props();
	const s = $derived(data.start);
	const w = $derived(s.wine);
	// svelte-ignore state_referenced_locally
	let name = $state(data.start.name);
	let village = $state('');

	async function create(geometry: object): Promise<string | null> {
		if (!name.trim()) return 'Give the vineyard a name first';
		const res = await fetch('/api/vineyards', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ wine: w.id, name, village, geometry })
		});
		const body = await res.json().catch(() => ({}));
		if (!res.ok) return typeof body.detail === 'string' ? body.detail : `Error ${res.status}`;
		await goto(links.vineyard(body.id));
		return null;
	}
</script>

<svelte:head><title>New vineyard · WineLib</title></svelte:head>

<header class="card head">
	<div class="kind">New vineyard</div>
	<h1>For <a href={links.wine(w.id)}>{w.producer} {w.cuvee} {w.vintage}</a></h1>
	{#if w.vineyard_id}<p class="warn">This wine already has a vineyard: creating this one links the wine to it instead.</p>{/if}
	<div class="fields">
		<label>Name <input bind:value={name} placeholder="e.g. Les Poyeux" /></label>
		<label>Village <input bind:value={village} placeholder="optional" /></label>
		<div class="muted small">
			{#if s.region}Region <b><RegionName name={s.region} /></b>{/if}{#if s.region && s.appellation}&nbsp;·{/if}{#if s.appellation} the map opens on {s.appellation}{/if}
		</div>
	</div>
	<p class="muted small">
		Draw its outline below, then Create vineyard: it's linked to this wine and to its other vintages that have no
		vineyard.
	</p>
</header>

<OutlineEditor kind="vineyards" {name} wine={w.id} {create} embedded onclose={() => goto(links.wine(w.id))} />

<style>
	.head {
		padding: 16px 20px;
		margin-bottom: 12px;
	}
	.kind {
		font-size: 11px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--muted);
	}
	h1 {
		margin: 2px 0 12px;
		font-size: 20px;
	}
	h1 a:hover {
		color: var(--accent);
	}
	.fields {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 12px 20px;
	}
	label {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
	}
	input {
		padding: 6px 8px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface);
		color: inherit;
		font: inherit;
		min-width: 220px;
	}
	.small {
		font-size: 12px;
	}
	.warn {
		color: var(--down);
		font-size: 13px;
	}
</style>

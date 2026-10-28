<script lang="ts" module>
	/** What to draw: an appellation's or a vineyard's own outline, or a new vineyard for a wine (`wine`) */
	export interface DrawSpec {
		kind: 'appellations' | 'vineyards';
		/** the row whose outline this is; none for a new vineyard drawn from a wine's page */
		id?: number;
		name: string;
		/** a new vineyard for this wine: created with the outline, linked to the wine and its vintages without one */
		wine?: number;
	}
</script>

<script lang="ts">
	import { onMount } from 'svelte';
	import type { Map as MlMap } from 'maplibre-gl';
	import type { Basemap } from '#lib/basemap.ts';

	/** Draw, edit or import an outline (routers/outlines.py) right on a page's map (DetailMap, full size): the map
	 * as it is (its zoom kept), this toolbar over it. Saved as user data, drawn on the maps like the official ones. */
	interface Props {
		map: MlMap;
		spec: DrawSpec;
		basemap: Basemap;
		/** the map has nothing of its own drawn: it moves to the wine's appellation or region (the server's frame) */
		frame?: boolean;
		/** closed: saved true when the outline was saved or removed, or the new vineyard created (its id) */
		onclose: (saved: boolean, created?: number) => void;
	}
	let { map, spec, basemap = $bindable(), frame = false, onclose }: Props = $props();

	type Polygon = { type: 'Polygon'; coordinates: number[][][] };
	type Geometry = Polygon | { type: 'MultiPolygon'; coordinates: number[][][][] };
	interface OutlineReply {
		boundary: string | null;
		custom: Geometry | null;
		official: Geometry | null;
		frame: [number, number, number, number] | null;
		/** a new vineyard: its suggested name (the cuvée) and the wine it's for */
		name?: string;
		wine?: { vineyard_id: number | null };
	}

	let fileInput: HTMLInputElement;
	let draw: import('terra-draw').TerraDraw | null = null;
	let reply = $state<OutlineReply | null>(null);
	let mode = $state<'polygon' | 'select'>('polygon');
	let shapes = $state(0);
	let busy = $state(false);
	let message = $state('');
	// a new vineyard's name and village
	let newName = $state('');
	let village = $state('');

	const polygonsOf = (g: Geometry): number[][][][] => (g.type === 'Polygon' ? [g.coordinates] : g.coordinates);
	// TerraDraw checks coordinate precision: 7 decimals is ~1 cm
	const round = (rings: number[][][]) => rings.map((r) => r.map(([x, y]) => [+x.toFixed(7), +y.toFixed(7)]));

	function add(g: Geometry) {
		if (!draw) return;
		const features = polygonsOf(g).map((rings) => ({
			id: crypto.randomUUID(),
			type: 'Feature' as const,
			geometry: { type: 'Polygon' as const, coordinates: round(rings) },
			properties: { mode: 'polygon' }
		}));
		const results = draw.addFeatures(features);
		const refused = results.filter((r) => !r.valid).length;
		if (refused) message = `${refused} part${refused > 1 ? 's' : ''} couldn’t be edited here (crossing lines or holes) and ${refused > 1 ? 'were' : 'was'} left out`;
		count();
		setMode('select');
	}

	/** An imported file: the map moves to it (drawing keeps the view as it is) */
	function fit(g: Geometry) {
		const pts = polygonsOf(g).flat(2);
		const box = [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))];
		map.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: 60, duration: 0, maxZoom: 17 });
	}

	/** Done: the drawing taken off the map first (the page may then reload or remove its map) */
	function close(saved: boolean, created?: number) {
		draw?.stop();
		draw = null;
		onclose(saved, created);
	}

	const count = () => (shapes = draw ? draw.getSnapshot().filter((f) => f.geometry.type === 'Polygon').length : 0);

	function setMode(m: 'polygon' | 'select') {
		mode = m;
		draw?.setMode(m);
	}

	onMount(() => {
		let stopped = false;
		(async () => {
			const res = await fetch(spec.id === undefined ? `/api/wines/${spec.wine}/new-vineyard` : `/api/${spec.kind}/${spec.id}/outline`);
			reply = res.ok ? await res.json() : null;
			newName = reply?.name ?? spec.name;
			const box = reply?.frame;
			if (frame && box) map.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: 60, duration: 0, maxZoom: 16 });
			const [{ TerraDraw, TerraDrawPolygonMode, TerraDrawSelectMode }, { TerraDrawMapLibreGLAdapter }] = await Promise.all([
				import('terra-draw'),
				import('terra-draw-maplibre-gl-adapter')
			]);
			if (stopped) return;
			const flags = { feature: { draggable: true, coordinates: { midpoints: true, draggable: true, deletable: true } } };
			draw = new TerraDraw({
				adapter: new TerraDrawMapLibreGLAdapter({ map }),
				modes: [new TerraDrawPolygonMode(), new TerraDrawSelectMode({ flags: { polygon: flags } })]
			});
			draw.start();
			draw.on('finish', () => count());
			draw.on('change', () => count());
			if (reply?.custom) add(reply.custom);
			else setMode('polygon');
		})().catch(() => (message = 'The drawing tools couldn’t be loaded'));
		return () => {
			stopped = true;
			draw?.stop();
			draw = null;
		};
	});

	function deleteSelected() {
		if (!draw) return;
		const selected = draw.getSnapshot().filter((f) => f.properties?.selected).map((f) => f.id!);
		if (!selected.length) return (message = 'Click a shape first, then delete it');
		draw.removeFeatures(selected);
		count();
	}

	function clearAll() {
		if (draw && shapes && confirm('Remove every shape drawn here (nothing is saved until you click Save)?')) {
			draw.clear();
			count();
			setMode('polygon');
		}
	}

	async function importFile(e: Event) {
		const file = (e.currentTarget as HTMLInputElement).files?.[0];
		if (!file) return;
		message = '';
		const res = await fetch('/api/outlines/parse', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ filename: file.name, text: await file.text() })
		});
		const body = await res.json().catch(() => ({}));
		if (!res.ok) message = body.detail ?? `Error ${res.status}`;
		else {
			add(body.geometry);
			fit(body.geometry);
		}
		fileInput.value = '';
	}

	async function save() {
		const polygons = (draw?.getSnapshot() ?? []).filter((f) => f.geometry.type === 'Polygon');
		if (!polygons.length) return (message = 'Draw at least one shape (click its corners, click the first one to close it)');
		const geometry: Geometry = { type: 'MultiPolygon', coordinates: polygons.map((f) => (f.geometry as Polygon).coordinates) };
		if (spec.wine !== undefined && !newName.trim()) return (message = 'Give the vineyard a name first');
		busy = true;
		const res = spec.wine !== undefined
			? await fetch('/api/vineyards', {
					method: 'POST',
					headers: { 'content-type': 'application/json' },
					body: JSON.stringify({ wine: spec.wine, name: newName, village, geometry })
				})
			: await fetch(`/api/${spec.kind}/${spec.id}/outline`, {
					method: 'PUT',
					headers: { 'content-type': 'application/json' },
					body: JSON.stringify({ geometry })
				});
		busy = false;
		const body = await res.json().catch(() => ({}));
		if (!res.ok) message = typeof body.detail === 'string' ? body.detail : `Error ${res.status}`;
		else close(true, spec.wine !== undefined ? body.id : undefined);
	}

	async function remove() {
		if (!confirm(`Remove your outline for ${spec.name}?${reply?.official ? ' The official one is drawn again.' : ''}`)) return;
		busy = true;
		const res = await fetch(`/api/${spec.kind}/${spec.id}/outline`, { method: 'DELETE' });
		busy = false;
		if (!res.ok) message = `Error ${res.status}`;
		else close(true);
	}
</script>

<div class="tools-card card" role="toolbar" aria-label="Outline of {spec.name || 'the new vineyard'}">
	<div class="head">
		<b>{spec.wine !== undefined ? 'New vineyard' : `Outline · ${spec.name}`}</b>
		<span class="muted small">{shapes ? `${shapes} shape${shapes > 1 ? 's' : ''}` : 'nothing drawn yet'}</span>
	</div>
	{#if spec.wine !== undefined}
		<div class="fields">
			<label>Name <input bind:value={newName} placeholder="e.g. Les Poyeux" /></label>
			<label>Village <input bind:value={village} placeholder="optional" /></label>
		</div>
		{#if reply?.wine?.vineyard_id}<p class="warn small">This wine already has a vineyard: creating this one links the wine to it instead.</p>{/if}
	{/if}
	<div class="tools">
		<div class="seg">
			<button class:on={mode === 'polygon'} onclick={() => setMode('polygon')}>Draw</button>
			<button class:on={mode === 'select'} onclick={() => setMode('select')}>Edit</button>
		</div>
		<button class="btn" onclick={deleteSelected} disabled={!shapes}>Delete shape</button>
		<button class="btn" onclick={clearAll} disabled={!shapes}>Clear</button>
		<button class="btn" onclick={() => fileInput.click()}>Import file…</button>
		<input bind:this={fileInput} type="file" accept=".geojson,.json,.kml" hidden onchange={importFile} />
		{#if reply?.official && !reply.custom}
			<button class="btn" onclick={() => reply?.official && add(reply.official)}>Start from the official outline</button>
		{/if}
		<div class="seg">
			<button class:on={basemap === 'satellite'} onclick={() => (basemap = 'satellite')}>Satellite</button>
			<button class:on={basemap === 'plain'} onclick={() => (basemap = 'plain')}>Plain</button>
		</div>
	</div>
	<p class="muted small hint">
		{mode === 'polygon'
			? 'Click each corner; click the first point (or press Enter) to close the shape. Several shapes make one outline.'
			: 'Click a shape to select it, drag its points to adjust, drag a middle point to add one, right-click a point to delete it.'}
	</p>
	{#if message}<p class="message">{message}</p>{/if}
	<div class="foot">
		{#if reply?.custom}<button class="btn danger" disabled={busy} onclick={remove}>Remove my outline</button>{/if}
		<span class="spacer"></span>
		<button class="btn" disabled={busy} onclick={() => close(false)}>Cancel</button>
		<button class="btn primary" disabled={busy || !shapes} onclick={save}>{busy ? 'Saving…' : spec.wine !== undefined ? 'Create vineyard' : 'Save outline'}</button>
	</div>
</div>

<style>
	/* Over the full-size map: right of the page's column (desktop), across the top (phone) */
	.tools-card {
		position: absolute;
		top: 14px;
		left: 574px;
		right: 60px;
		max-width: 760px;
		z-index: 3;
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 12px 14px;
		box-shadow: var(--shadow);
	}
	@media (max-width: 760px) {
		.tools-card {
			top: 10px;
			left: 10px;
			right: 54px;
			padding: 10px;
		}
	}
	.head {
		display: flex;
		align-items: baseline;
		gap: 12px;
	}
	.tools,
	.fields {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		align-items: center;
	}
	.fields label {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
	}
	.fields input {
		padding: 5px 8px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface);
		color: inherit;
		font: inherit;
		min-width: 160px;
	}
	.seg button {
		padding: 6px 12px;
	}
	.hint,
	.warn {
		margin: 0;
	}
	.small {
		font-size: 12px;
	}
	.warn,
	.message,
	.danger {
		color: var(--down);
	}
	.message {
		margin: 0;
		font-size: 13px;
	}
	.foot {
		display: flex;
		gap: 8px;
		align-items: center;
	}
	.spacer {
		flex: 1;
	}
</style>

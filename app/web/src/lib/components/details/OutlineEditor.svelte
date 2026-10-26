<script lang="ts">
	import { onMount } from 'svelte';
	import type { Map as MlMap } from 'maplibre-gl';
	import { createMap, setBasemap, isDark } from '#lib/basemap.ts';
	import type { Basemap } from '#lib/basemap.ts';

	/** Draw, edit or import an appellation's / vineyard's own outline (routers/outlines.py): saved as user data,
	 * drawn on the maps like the official outlines. */
	interface Props {
		kind: 'appellations' | 'vineyards';
		/** the row whose outline this is; none for a vineyard drawn from a wine's page (`wine`, `create`) */
		id?: number;
		name: string;
		/** closed: saved true when the outline was saved or removed (the page reloads its map) */
		onclose: (saved: boolean) => void;
		/** a new vineyard for this wine: the map opens on the wine's appellation */
		wine?: number;
		/** saves a new row with the drawn outline instead: an error message, or null when done */
		create?: (geometry: Geometry) => Promise<string | null>;
		/** in the page, not a dialog over it */
		embedded?: boolean;
	}
	let { kind, id, name, onclose, wine, create, embedded = false }: Props = $props();

	type Polygon = { type: 'Polygon'; coordinates: number[][][] };
	type Geometry = Polygon | { type: 'MultiPolygon'; coordinates: number[][][][] };
	interface OutlineReply {
		boundary: string | null;
		custom: Geometry | null;
		official: Geometry | null;
		frame: [number, number, number, number] | null;
	}

	let container: HTMLDivElement;
	let fileInput: HTMLInputElement;
	let map: MlMap | null = null;
	// TerraDraw, loaded with the map (only on this dialog)
	let draw: import('terra-draw').TerraDraw | null = null;
	let reply = $state<OutlineReply | null>(null);
	let mode = $state<'polygon' | 'select'>('polygon');
	let basemap = $state<Basemap>('satellite');
	let shapes = $state(0);
	let busy = $state(false);
	let message = $state('');

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

	function fit(g: Geometry | null, frame: number[] | null) {
		if (!map) return;
		let box = frame;
		if (g) {
			const pts = polygonsOf(g).flat(2);
			box = [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))];
		}
		if (box) map.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: 40, duration: 0, maxZoom: 17 });
	}

	const count = () => (shapes = draw ? draw.getSnapshot().filter((f) => f.geometry.type === 'Polygon').length : 0);

	function setMode(m: 'polygon' | 'select') {
		mode = m;
		draw?.setMode(m);
	}

	onMount(() => {
		let cancelled = false;
		(async () => {
			const res = await fetch(id === undefined ? `/api/wines/${wine}/new-vineyard` : `/api/${kind}/${id}/outline`);
			reply = res.ok ? await res.json() : null;
			map = await createMap(container, basemap);
			if (cancelled) return map.remove();
			const [{ TerraDraw, TerraDrawPolygonMode, TerraDrawSelectMode }, { TerraDrawMapLibreGLAdapter }] = await Promise.all([
				import('terra-draw'),
				import('terra-draw-maplibre-gl-adapter')
			]);
			const flags = { feature: { draggable: true, coordinates: { midpoints: true, draggable: true, deletable: true } } };
			draw = new TerraDraw({
				adapter: new TerraDrawMapLibreGLAdapter({ map }),
				modes: [new TerraDrawPolygonMode(), new TerraDrawSelectMode({ flags: { polygon: flags } })]
			});
			draw.start();
			draw.on('finish', () => count());
			draw.on('change', () => count());
			fit(reply?.custom ?? reply?.official ?? null, reply?.frame ?? null);
			if (reply?.custom) add(reply.custom);
			else setMode('polygon');
		})().catch(() => (message = 'The map couldn’t be loaded'));
		return () => {
			cancelled = true;
			draw?.stop();
			map?.remove();
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
			fit(body.geometry, null);
		}
		fileInput.value = '';
	}

	async function save() {
		const polygons = (draw?.getSnapshot() ?? []).filter((f) => f.geometry.type === 'Polygon');
		if (!polygons.length) return (message = 'Draw at least one shape (click its corners, click the first one to close it)');
		busy = true;
		const geometry: Geometry = { type: 'MultiPolygon', coordinates: polygons.map((f) => (f.geometry as Polygon).coordinates) };
		if (create) {
			message = (await create(geometry)) ?? '';
			busy = false;
			return;
		}
		const res = await fetch(`/api/${kind}/${id}/outline`, {
			method: 'PUT',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ geometry })
		});
		busy = false;
		const body = await res.json().catch(() => ({}));
		if (!res.ok) message = body.detail ?? `Error ${res.status}`;
		else onclose(true);
	}

	async function remove() {
		if (!confirm(`Remove your outline for ${name}?${reply?.official ? ' The official one is drawn again.' : ''}`)) return;
		busy = true;
		const res = await fetch(`/api/${kind}/${id}/outline`, { method: 'DELETE' });
		busy = false;
		if (!res.ok) message = `Error ${res.status}`;
		else onclose(true);
	}

	$effect(() => {
		if (map) setBasemap(map, basemap, isDark());
	});
</script>

<div class="backdrop" class:embedded role="presentation" onclick={(e) => !embedded && e.target === e.currentTarget && onclose(false)}>
	<div class="dialog card" role={embedded ? 'region' : 'dialog'} aria-modal={embedded ? undefined : true} aria-label="Outline of {name || 'the new vineyard'}">
		<div class="head">
			<h2>Outline{name ? ` · ${name}` : ''}</h2>
			<span class="muted small">{shapes ? `${shapes} shape${shapes > 1 ? 's' : ''}` : 'nothing drawn yet'}</span>
		</div>
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
			<select bind:value={basemap} aria-label="Background">
				<option value="satellite">Satellite</option>
				<option value="plain">Plain</option>
				<option value="topo">Terrain</option>
			</select>
		</div>
		<p class="muted small hint">
			{mode === 'polygon'
				? 'Click each corner; click the first point (or press Enter) to close the shape. Several shapes make one outline.'
				: 'Click a shape to select it, drag its points to adjust, drag a middle point to add one, right-click a point to delete it.'}
		</p>
		<div class="map" bind:this={container}></div>
		{#if message}<p class="message">{message}</p>{/if}
		<div class="foot">
			{#if reply?.custom}<button class="btn danger" disabled={busy} onclick={remove}>Remove my outline</button>{/if}
			<span class="spacer"></span>
			<button class="btn" disabled={busy} onclick={() => onclose(false)}>Cancel</button>
			<button class="btn primary" disabled={busy || !shapes} onclick={save}>{busy ? 'Saving…' : create ? 'Create vineyard' : 'Save outline'}</button>
		</div>
	</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 50;
		background: rgb(0 0 0 / 45%);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 16px;
	}
	.backdrop.embedded {
		position: static;
		background: none;
		padding: 0;
		display: block;
	}
	.dialog {
		width: min(1100px, 100%);
		max-height: 100%;
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 14px;
		overflow: auto;
	}
	.head {
		display: flex;
		align-items: baseline;
		gap: 12px;
	}
	h2 {
		margin: 0;
		font-size: 16px;
	}
	.tools {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		align-items: center;
	}
	.seg button {
		padding: 6px 12px;
	}
	.hint {
		margin: 0;
	}
	.small {
		font-size: 12px;
	}
	.map {
		height: min(62vh, 640px);
		min-height: 320px;
		border-radius: 8px;
		overflow: hidden;
	}
	.message {
		margin: 0;
		color: var(--down);
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
	.danger {
		color: var(--down);
	}
</style>

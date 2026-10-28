<script lang="ts">
	import { onMount } from 'svelte';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import type { GeoJSONSource, Map as MlMap } from 'maplibre-gl';
	import { createMap } from '#lib/basemap.ts';
	import { accentColor } from '#lib/theme.svelte.ts';

	interface Props {
		lat?: number | null;
		lng?: number | null;
		/** the place's name, when a pasted Google Maps link has one */
		onname?: (name: string) => void;
		/** what to look up on OpenStreetMap: the place's name, city and country */
		query?: string;
	}
	let { lat = $bindable(null), lng = $bindable(null), onname, query = '' }: Props = $props();

	// Search OpenStreetMap (GET /api/lookups/geocode): pick a match to place the pin
	type Hit = { name: string; address: string; lat: number; lng: number; category: string; type: string };
	let hits = $state<Hit[] | null>(null);
	let searching = $state(false);
	let searchError = $state('');
	async function searchOsm() {
		if (!query.trim() || searching) return;
		searching = true;
		searchError = '';
		try {
			const res = await fetch(`/api/lookups/geocode?q=${encodeURIComponent(query)}`);
			const body = await res.json().catch(() => []);
			if (!res.ok) throw new Error(body.detail ?? `Error ${res.status}`);
			hits = body;
		} catch (e) {
			searchError = e instanceof Error ? e.message : String(e);
			hits = null;
		} finally {
			searching = false;
		}
	}
	function pick(h: Hit) {
		place([h.lat, h.lng]);
		hits = null;
	}

	// The device's position (phone GPS, or the laptop's estimate). Browsers only allow it on secure pages
	// (HTTPS, or localhost): not on a plain http:// address from another machine
	const canLocate = typeof window !== 'undefined' && window.isSecureContext && 'geolocation' in navigator;
	let locating = $state(false);
	let locateError = $state('');
	function useMyLocation() {
		if (!canLocate || locating) return;
		locating = true;
		locateError = '';
		navigator.geolocation.getCurrentPosition(
			(pos) => {
				locating = false;
				place([pos.coords.latitude, pos.coords.longitude]);
				note = `Your current position (±${Math.round(pos.coords.accuracy)} m): adjust the pin if needed.`;
			},
			(err) => {
				locating = false;
				locateError = err.code === err.PERMISSION_DENIED ? 'Location access was denied: allow it for this site in the browser.' : 'Couldn’t get your position.';
			},
			{ enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
		);
	}

	let container: HTMLDivElement;
	let map = $state<MlMap>();
	let paste = $state('');
	let pasteError = $state('');
	let resolving = $state(false);
	let note = $state(''); // e.g. the pin came from the address, not from Google

	const round = (n: number) => Math.round(n * 1e6) / 1e6;
	const valid = (a: number, b: number) => Math.abs(a) <= 90 && Math.abs(b) <= 180;

	/** "47.02, 4.84", or a Google Maps link (…/@47.02,4.84,17z or …!3d47.02!4d4.84). */
	export function parseCoordinates(text: string): [number, number] | null {
		const patterns = [/!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/, /@(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)/, /(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)/];
		for (const re of patterns) {
			const m = text.match(re);
			if (m && valid(+m[1], +m[2])) return [+m[1], +m[2]];
		}
		return null;
	}

	function set(a: number, b: number) {
		lat = round(a);
		lng = round(b);
		// Map clicks aren't form input: tell the form it changed (for the unsaved-changes guard)
		container.dispatchEvent(new Event('change', { bubbles: true }));
	}

	function place(c: [number, number]) {
		set(c[0], c[1]);
		map?.flyTo({ center: [c[1], c[0]], zoom: Math.max(map.getZoom(), 14) });
		paste = '';
	}

	const isGoogleLink = (text: string) => /^https?:\/\/(maps\.app\.goo\.gl|goo\.gl|([a-z]+\.)?google\.[a-z.]+)\//i.test(text);

	async function applyPaste() {
		const text = paste.trim();
		if (!text || resolving) return;
		pasteError = '';
		note = '';
		const c = parseCoordinates(text);
		// A full link with coordinates is read here; anything else from Google (short share links) by the server
		if (c && (!isGoogleLink(text) || /[@!]/.test(text))) return place(c);
		if (!isGoogleLink(text)) return void (pasteError = 'Couldn’t find coordinates in that');
		resolving = true;
		try {
			const res = await fetch(`/api/lookups/map-link?url=${encodeURIComponent(text)}`);
			const body = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Error ${res.status}`);
			place([body.lat, body.lng]);
			if (body.name) onname?.(body.name);
			if (body.approximate) note = 'Approximate position, found from the address: check the pin and click the map to adjust it.';
		} catch (e) {
			pasteError = e instanceof Error ? e.message : String(e);
		} finally {
			resolving = false;
		}
	}

	onMount(() => {
		let m: MlMap | undefined;
		// left before the map was ready (a quick click on): the map made afterwards is removed at once, not leaked
		let gone = false;
		(async () => {
			const has = lat !== null && lng !== null;
			m = await createMap(container, 'plain', { center: has ? [lng!, lat!] : [20, 25], zoom: has ? 14 : 1.4 });
			if (gone) return m.remove();
			m.addSource('pin', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
			m.addLayer({
				id: 'pin', type: 'circle', source: 'pin',
				paint: { 'circle-radius': 8, 'circle-color': accentColor(), 'circle-stroke-color': '#fff', 'circle-stroke-width': 2.5 }
			});
			m.getCanvas().style.cursor = 'crosshair';
			m.on('click', (e) => set(e.lngLat.lat, e.lngLat.lng));
			map = m;
		})();
		return () => {
			gone = true;
			m?.remove();
		};
	});

	$effect(() => {
		if (!map) return;
		const features = lat !== null && lng !== null
			? [{ type: 'Feature' as const, properties: {}, geometry: { type: 'Point' as const, coordinates: [lng, lat] } }]
			: [];
		(map.getSource('pin') as GeoJSONSource).setData({ type: 'FeatureCollection', features });
	});
</script>

<div class="picker">
	<div class="map" bind:this={container}></div>
	<div class="row">
		<input
			class="paste"
			placeholder="Paste “47.0236, 4.8389” or a Google Maps link…"
			bind:value={paste}
			onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), applyPaste())}
			onpaste={() => setTimeout(applyPaste)}
			onblur={applyPaste}
			disabled={resolving}
			aria-label="Paste coordinates"
		/>
		<button
			type="button"
			class="btn"
			disabled={!canLocate || locating}
			onclick={useMyLocation}
			title={canLocate ? 'Put the pin where you are now' : 'Browsers only share your location with secure (https) pages'}
		>
			{locating ? 'Locating…' : '◎ My location'}
		</button>
		<button type="button" class="btn" disabled={!query.trim() || searching} onclick={searchOsm} title="Look up “{query}” on OpenStreetMap">
			{searching ? 'Searching…' : 'Search OpenStreetMap'}
		</button>
		{#if lat !== null || lng !== null}
			<button type="button" class="btn" onclick={() => ((lat = null), (lng = null), container.dispatchEvent(new Event('change', { bubbles: true })))}>
				Clear
			</button>
		{/if}
	</div>
	{#if searchError}<p class="hint error">{searchError}</p>{/if}
	{#if locateError}<p class="hint error">{locateError}</p>{/if}
	{#if !canLocate}
		<p class="hint muted">“My location” needs the app opened over https (e.g. behind a reverse proxy, or through Tailscale): browsers don’t share your position with http pages.</p>
	{/if}
	{#if hits}
		{#if hits.length}
			<ul class="hits">
				{#each hits as h, i (i)}
					<li>
						<button type="button" class="hit" onclick={() => pick(h)}>
							<b>{h.name}</b> <span class="muted">{h.type.replace(/_/g, ' ')} · {h.address}</span>
						</button>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="hint muted">Nothing on OpenStreetMap for “{query}”: click the map or paste a Google Maps link.</p>
		{/if}
	{/if}
	<p class="hint muted" class:error={!!pasteError}>
		{resolving ? 'Looking up that link…' : pasteError || note || 'Click the map to place the pin, or paste coordinates or a Google Maps link (short share links work too).'}
	</p>
</div>

<style>
	.picker {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-bottom: 14px;
	}
	.map {
		position: relative;
		height: 260px;
		border-radius: 8px;
		overflow: hidden;
		border: 1px solid var(--border);
	}
	.row {
		display: flex;
		gap: 8px;
	}
	.row {
		flex-wrap: wrap;
	}
	.paste {
		flex: 1 1 220px;
		min-width: 0;
	}
	.hits {
		list-style: none;
		margin: 0;
		padding: 0;
		border: 1px solid var(--border);
		border-radius: 8px;
		max-height: 200px;
		overflow-y: auto;
	}
	.hit {
		display: block;
		width: 100%;
		padding: 6px 10px;
		border: none;
		border-bottom: 1px solid var(--border);
		background: none;
		text-align: left;
		font-size: 13px;
		cursor: pointer;
	}
	.hit:hover {
		background: var(--surface-2);
	}
	.hint {
		margin: 0;
		font-size: 12px;
	}
	.hint.error {
		color: var(--down);
	}
</style>

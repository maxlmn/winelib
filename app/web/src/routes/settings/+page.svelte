<script lang="ts">
	import { beforeNavigate } from '$app/navigation';
	import { messageOf, request } from '#lib/api/http.ts';
	import Maintenance from '#lib/components/settings/Maintenance.svelte';
	import Attention, { type AttentionItem } from '#lib/components/settings/Attention.svelte';
	import Tabs from '#lib/components/details/Tabs.svelte';
	import { page } from '$app/state';
	import { appSettings, configured, integrations, setSettings } from '#lib/settings.svelte.ts';
	import type { AppSettings, StorageGroup } from '#lib/settings.svelte.ts';
	import { PALETTES, setTheme, theme } from '#lib/theme.svelte.ts';
	import { mapView } from '#lib/mapView.svelte.ts';
	import type { Font, Mode, Palette } from '#lib/theme.svelte.ts';
	import { links } from '#lib/links.ts';

	const MODES: [Mode, string][] = [['auto', '◐ System'], ['light', '☀ Light'], ['dark', '☾ Dark']];
	const FONTS: [Font, string][] = [['sans', 'Modern'], ['serif', 'Classic']];

	let { data } = $props();
	// What needs attention: filled in when its checks are done (the page doesn't wait for them)
	let attention = $state<AttentionItem[] | null>(null);
	$effect(() => {
		let current = true;
		attention = null;
		data.attention.then((items) => current && (attention = items));
		return () => (current = false);
	});

	const clone = (s: AppSettings): AppSettings => JSON.parse(JSON.stringify(s));

	let draft = $state<AppSettings>(clone(appSettings));
	// The critics with scores in the database, and the current choice even before it has any
	const critics = $derived(data.critics.includes(draft.preferred_critic) ? data.critics : [draft.preferred_critic, ...data.critics]);
	// Currencies edited as rows, so renaming a code doesn't reorder or drop the row
	let rates = $state(toRows(appSettings.exchange_rates, appSettings.currency));
	let newKeyword = $state('');
	let saving = $state(false);
	let error = $state('');
	let saved = $state(false);

	function toRows(r: Record<string, number>, main: string) {
		return Object.entries(r)
			.filter(([code]) => code !== main)
			.map(([code, rate]) => ({ code, rate }));
	}

	// Another main currency: the rates are restated in it (the old main currency becomes a row)
	function setMain(code: string) {
		const row = rates.find((r) => r.code.trim().toUpperCase() === code);
		if (!row || !row.rate) return;
		const by = row.rate;
		rates = [{ code: draft.currency, rate: +(1 / by).toFixed(4) },
			...rates.filter((r) => r !== row).map((r) => ({ code: r.code, rate: +(r.rate / by).toFixed(4) }))];
		draft.currency = code;
	}

	const payload = $derived<AppSettings>({
		...draft,
		exchange_rates: { [draft.currency]: 1, ...Object.fromEntries(rates.filter((r) => r.code.trim()).map((r) => [r.code.trim().toUpperCase(), r.rate])) }
	});
	// compared whatever the keys' order (the saved settings come back in the server's order: not a change)
	const canon = (v: unknown): unknown =>
		Array.isArray(v) ? v.map(canon) : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b)).map(([k, x]) => [k, canon(x)])) : v;
	const dirty = $derived(
		JSON.stringify(canon(payload)) !== JSON.stringify(canon({ ...appSettings, exchange_rates: { [appSettings.currency]: 1, ...appSettings.exchange_rates } }))
	);

	beforeNavigate((nav) => {
		// another tab of this page keeps the draft: only leaving Settings asks
		if (nav.to?.url.pathname === page.url.pathname) return;
		if (dirty && !saving && !confirm('Discard unsaved settings?')) nav.cancel();
	});

	// Live preview: which group each cellar location falls in with the draft rules (same logic as the API)
	function groupFor(loc: string): { group: string; capacity: number | null } {
		const matches = draft.storage_groups.filter((g) => g.prefix && loc.startsWith(g.prefix));
		const g = matches.sort((a, b) => b.prefix.length - a.prefix.length)[0];
		return g ? { group: g.name, capacity: loc === g.name ? null : g.capacity } : { group: draft.other_group, capacity: null };
	}
	const preview = $derived.by(() => {
		const groups = new Map<string, { loc: string; capacity: number | null }[]>();
		for (const loc of data.locations) {
			const { group, capacity } = groupFor(loc);
			groups.set(group, [...(groups.get(group) ?? []), { loc, capacity }]);
		}
		const order = [...draft.storage_groups.map((g) => g.name), draft.other_group];
		return [...groups].sort(([a], [b]) => order.indexOf(a) - order.indexOf(b));
	});
	const localPreview = $derived(
		data.locations.filter((l) => !draft.non_local_keywords.some((k) => k && l.includes(k)))
	);

	function addKeyword() {
		const k = newKeyword.trim();
		if (k && !draft.non_local_keywords.includes(k)) draft.non_local_keywords.push(k);
		newKeyword = '';
	}

	function moveGroup(i: number, by: number) {
		const g = draft.storage_groups;
		[g[i], g[i + by]] = [g[i + by], g[i]];
	}

	function reset(to: AppSettings) {
		draft = clone(to);
		rates = toRows(to.exchange_rates, to.currency);
		error = '';
	}

	async function loadDefaults() {
		try {
			reset(await request<AppSettings>('/api/settings/defaults'));
		} catch (e) {
			error = messageOf(e);
		}
	}

	async function save() {
		saving = true;
		error = '';
		try {
			// the server's message per field ("Exchange rates: ..."), or "couldn't reach" when the app is down
			const body = await request<AppSettings>('/api/settings', { method: 'PUT', body: payload });
			setSettings(body);
			reset(body);
			saved = true;
			setTimeout(() => (saved = false), 2500);
		} catch (e) {
			error = messageOf(e);
		} finally {
			saving = false;
		}
	}

	const newGroup = (): StorageGroup => ({ name: '', prefix: '', capacity: null });
</script>

<svelte:head><title>Settings · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Settings</h1>
	<span class="muted">Shared with everyone using the app. Changes apply as soon as you save.</span>
</div>

<!-- The settings themselves, the Maintenance tasks, what needs attention: one tab each (?tab=); an old link to
     #maintenance, or one naming a task, opens Maintenance -->
<Tabs plain
	tabs={[
		{ id: 'settings', label: 'Settings' },
		{ id: 'maintenance', label: 'Maintenance' },
		{ id: 'attention', label: 'Needs attention', count: attention?.length || undefined }
	]}
	initial={page.url.searchParams.get('task') || page.url.hash === '#maintenance' ? 'maintenance' : 'settings'}
>
	{#snippet children(tab)}
{#if tab === 'maintenance'}
	<div class="grid"><Maintenance /></div>
{:else if tab === 'attention'}
	<div class="grid"><Attention items={attention} /></div>
{:else}
<div class="grid">
	<section class="card wide appearance">
		<div class="title-row">
			<h2>Appearance</h2>
			<span class="badge-device muted">This device only · applies instantly</span>
		</div>
		<div class="appearance-grid">
			<div class="field">
				<span>Mode</span>
				<div class="seg">
					{#each MODES as [mode, label]}
						<button class:on={theme.mode === mode} onclick={() => setTheme({ mode })}>{label}</button>
					{/each}
				</div>
			</div>
			<div class="field">
				<span>Palette</span>
				<div class="swatches">
					{#each Object.entries(PALETTES) as [id, p] (id)}
						<button
							class="swatch"
							class:on={theme.palette === id}
							onclick={() => setTheme({ palette: id as Palette })}
							aria-pressed={theme.palette === id}
						>
							<span class="chip-color" style:--l={p.light} style:--d={p.dark}></span>
							{p.name}
						</button>
					{/each}
				</div>
			</div>
			<div class="field">
				<span>Maps</span>
				<div class="seg" style:align-self="flex-start">
					<button class:on={!mapView.always} onclick={() => (mapView.always = false)}>In the page</button>
					<button class:on={mapView.always} onclick={() => (mapView.always = true)}>Always full size</button>
				</div>
				<small class="muted">Full size: a page's map fills the window, its details over it (⤢ on any map does it once)</small>
			</div>
			<div class="field">
				<span>Headings</span>
				<div class="fonts">
					{#each FONTS as [font, label]}
						<button class="font" class:on={theme.font === font} data-font-preview={font} onclick={() => setTheme({ font })}>
							<b>Aa</b><small>{label}</small>
						</button>
					{/each}
				</div>
			</div>
		</div>
	</section>

	<section class="card">
		<h2>Currencies</h2>
		<p class="muted">Every total, value and chart is in the main currency; prices in another are converted with these rates.</p>
		<label class="field">
			<span>Main currency</span>
			<select value={draft.currency} onchange={(e) => setMain(e.currentTarget.value)}>
				<option value={draft.currency}>{draft.currency}</option>
				{#each rates.filter((r) => r.code.trim()) as r (r.code)}<option value={r.code.trim().toUpperCase()}>{r.code.trim().toUpperCase()}</option>{/each}
			</select>
		</label>
		<table>
			<thead><tr><th>Currency</th><th>1 unit =</th><th></th></tr></thead>
			<tbody>
				<tr><td><span class="code">{draft.currency}</span></td><td class="muted">1 {draft.currency} (main)</td><td></td></tr>
				{#each rates as r, i (i)}
					<tr>
						<td><input class="short upper" bind:value={r.code} maxlength="3" placeholder="EUR" aria-label="Currency code" /></td>
						<td><input class="short num" type="number" step="0.01" min="0.0001" bind:value={r.rate} aria-label="Rate in {draft.currency}" /> {draft.currency}</td>
						<td><button class="icon-btn" onclick={() => rates.splice(i, 1)} aria-label="Remove {r.code}">✕</button></td>
					</tr>
				{/each}
			</tbody>
		</table>
		<button class="link" onclick={() => rates.push({ code: '', rate: 1 })}>+ Add currency</button>
	</section>

	<section class="card">
		<h2>Local totals</h2>
		<p class="muted">The Cellar page shows a second set of totals for bottles kept locally.</p>
		<label class="field">
			<span>Label</span>
			<input class="short" bind:value={draft.local_label} placeholder="Local" />
		</label>
		<div class="field">
			<span>Not local: locations containing</span>
			<div class="chips">
				{#each draft.non_local_keywords as k, i (k)}
					<button class="chip" onclick={() => draft.non_local_keywords.splice(i, 1)}>{k} ✕</button>
				{/each}
				<input
					class="chip-input"
					bind:value={newKeyword}
					placeholder="Add…"
					onkeydown={(e) => e.key === 'Enter' && addKeyword()}
					onblur={addKeyword}
				/>
			</div>
		</div>
		<p class="preview muted">
			Counted as {draft.local_label || 'local'}: <span class="num">{localPreview.length}</span> of {data.locations.length} locations
		</p>
	</section>

	{#if configured('bordeaux_index')}
	<section class="card">
		<h2>Bordeaux Index</h2>
		<p class="muted">The Cellar page's Bordeaux Index tab reconciles your BI portfolio with the app's bottles held at BI.</p>
		<label class="field">
			<span>BI stock: locations containing</span>
			<input class="short" bind:value={draft.bi_location} placeholder="e.g. the warehouse's name" />
		</label>
		<p class="preview muted">
			Reconciled with your BI portfolio:
			<span class="num">{draft.bi_location.trim() ? data.locations.filter((l) => l.toLowerCase().includes(draft.bi_location.trim().toLowerCase())).length : 0}</span>
			of {data.locations.length} locations
		</p>
	</section>
	{/if}

	<section class="card wide">
		<h2>Storage</h2>
		<p class="muted">
			Groups for the shelf map and cards. A location belongs to the group with the longest matching prefix; capacity is
			bottles per bin (a location named exactly like its group has none).
		</p>
		<table>
			<thead><tr><th></th><th>Group</th><th>Prefix</th><th>Bottles per bin</th><th></th></tr></thead>
			<tbody>
				{#each draft.storage_groups as g, i (i)}
					<tr>
						<td class="order">
							<button class="icon-btn" disabled={i === 0} onclick={() => moveGroup(i, -1)} aria-label="Move up">↑</button>
							<button class="icon-btn" disabled={i === draft.storage_groups.length - 1} onclick={() => moveGroup(i, 1)} aria-label="Move down">↓</button>
						</td>
						<td><input bind:value={g.name} placeholder="Home" aria-label="Group name" /></td>
						<td><input class="short" bind:value={g.prefix} placeholder="H" aria-label="Prefix" /></td>
						<td>
							<input
								class="short num"
								type="number"
								min="1"
								value={g.capacity ?? ''}
								oninput={(e) => (g.capacity = e.currentTarget.value ? +e.currentTarget.value : null)}
								placeholder="none"
								aria-label="Capacity"
							/>
						</td>
						<td><button class="icon-btn" onclick={() => draft.storage_groups.splice(i, 1)} aria-label="Remove group">✕</button></td>
					</tr>
				{/each}
				<tr>
					<td></td>
					<td><input bind:value={draft.other_group} aria-label="Other locations group" /></td>
					<td colspan="3" class="muted">every other location</td>
				</tr>
			</tbody>
		</table>
		<button class="link" onclick={() => draft.storage_groups.push(newGroup())}>+ Add group</button>

		<h3>Preview with your current locations</h3>
		<div class="preview-groups">
			{#each preview as [group, locs] (group)}
				<div class="pg">
					<b>{group}</b> <span class="muted num">{locs.length}</span>
					<div class="locs">
						{#each locs as l (l.loc)}<span class="loc" title={l.capacity ? `${l.capacity} bottles` : 'no capacity'}>{l.loc}{#if l.capacity}<small class="muted">/{l.capacity}</small>{/if}</span>{/each}
					</div>
				</div>
			{/each}
		</div>
	</section>

	<section class="card">
		<h2>Map</h2>
		<label class="field">
			<span>Background</span>
			<select bind:value={draft.map_default_basemap}>
				<option value="plain">Plain</option>
				<option value="satellite">Satellite</option>
			</select>
		</label>
	</section>

	<section class="card">
		<h2>Critics</h2>
		<p class="muted">Lists sort by this critic's score, and the vintage pages rank wines by it.</p>
		<label class="field">
			<span>Preferred critic</span>
			<select bind:value={draft.preferred_critic}>
				{#each critics as c (c)}<option value={c}>{c}</option>{/each}
			</select>
		</label>
	</section>

	<section class="card wide">
		<h2>Your data</h2>
		<p class="muted">Everything in the database, to keep or take elsewhere: every table, your cellar, tastings, scores,
			places, outlines and settings, with the reference data.</p>
		<div class="downloads">
			<a class="btn" href="/api/export.json" download>Download as JSON</a>
			<a class="btn" href="/api/export.zip" download>Download as CSV (zip)</a>
		</div>
	</section>

	<section class="card wide">
		<h2>Map outlines</h2>
		{#if integrations.mapCredits.length}
			<p class="muted">The map's outlines and where they come from:</p>
			<ul class="credits">
				{#each integrations.mapCredits as c (c.source)}
					<li>
						{#if c.url}<a href={c.url} target="_blank" rel="noreferrer">{c.credit ?? c.source}</a>{:else}{c.credit ?? c.source}{/if}
						<span class="muted small"> · {c.licence}{c.rows ? ` · ${c.rows} outlines` : ''}</span>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="muted">No downloaded outlines: Maintenance › Map outlines downloads them (built ones aren't listed here).</p>
		{/if}
		<p class="muted small">Every source of the regions, appellations, grapes and outlines, and their licences:
			<a href={links.about()}>About the data</a>.</p>
	</section>

	<section class="card wide">
		<h2>Integrations</h2>
		<p class="muted">Optional connections, set up with keys in <code>.secrets.env</code> (restart the app after adding one).</p>
		<ul class="integrations">
			{#each integrations.list as i (i.id)}
				<li>
					<div><b>{i.name}</b> <span class="state" class:on={i.configured}>{i.configured ? 'Set up' : 'Not set up'}</span></div>
					<div class="muted small">{i.what}</div>
					{#if !i.configured}<div class="muted small">Needs: {i.needs}</div>{/if}
				</li>
			{/each}
			{#each integrations.plugins as p (p.name)}
				<li>
					<div><b>Plug-in: {p.name}</b> <span class="state" class:on={p.ok}>{p.ok ? 'Loaded' : 'Failed'}</span></div>
					{#if p.error}<div class="muted small">{p.error}</div>{/if}
				</li>
			{/each}
		</ul>
	</section>
</div>
{/if}
	{/snippet}
</Tabs>

<div class="bar card" class:show={dirty || saved || error}>
	{#if error}
		<span class="error">{error}</span>
	{:else if saved && !dirty}
		<span class="ok">Saved ✓</span>
	{:else}
		<span class="muted">Unsaved changes</span>
	{/if}
	<span class="spacer"></span>
	<button class="link" onclick={loadDefaults}>Reset to defaults</button>
	<button class="btn" disabled={!dirty} onclick={() => reset(appSettings)}>Discard</button>
	<button class="btn primary" disabled={!dirty || saving} onclick={save}>{saving ? 'Saving…' : 'Save'}</button>
</div>

<style>
	.page-head {
		align-items: baseline;
		justify-content: flex-start;
	}
	.grid {
		display: grid;
		/* min(): never wider than a phone screen */
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
		gap: 14px;
		padding-bottom: 80px;
	}
	section {
		padding: 16px 18px;
	}
	.wide {
		grid-column: 1 / -1;
	}
	h2 {
		margin: 0 0 4px;
		font-size: 15px;
	}
	h3 {
		margin: 18px 0 8px;
		font-size: 13px;
	}
	section > p {
		margin: 0 0 12px;
		font-size: 13px;
	}
	table {
		border-collapse: collapse;
		margin-bottom: 6px;
	}
	th {
		text-align: left;
		font-weight: 500;
		font-size: 12px;
		color: var(--muted);
		padding: 0 8px 6px 0;
	}
	td {
		padding: 3px 8px 3px 0;
		font-size: 13px;
	}
	input,
	select {
		padding: 6px 8px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface-2);
		min-width: 0;
	}
	input:focus,
	select:focus {
		outline: none;
		border-color: var(--accent);
	}
	.short {
		width: 90px;
	}
	.upper {
		text-transform: uppercase;
	}
	.code {
		font-weight: 600;
	}
	.icon-btn {
		border: none;
		background: none;
		color: var(--muted);
		cursor: pointer;
		padding: 2px 5px;
	}
	.icon-btn:hover:not(:disabled) {
		color: var(--accent);
	}
	.icon-btn:disabled {
		opacity: 0.3;
		cursor: default;
	}
	.order {
		white-space: nowrap;
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		color: var(--accent);
		cursor: pointer;
		font-size: 13px;
	}
	.credits {
		margin: 0;
		padding-left: 18px;
		font-size: 13px;
		line-height: 1.7;
	}
	.credits a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.credits a:hover {
		color: var(--accent);
	}
	.downloads {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.integrations {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
		gap: 10px 18px;
	}
	.integrations li {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}
	.integrations .small {
		font-size: 12px;
	}
	.state {
		font-size: 11px;
		padding: 0 7px;
		border-radius: 9px;
		box-shadow: inset 0 0 0 1px var(--border);
		color: var(--muted);
	}
	.state.on {
		color: var(--up);
		box-shadow: inset 0 0 0 1px var(--up);
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 5px;
		margin-bottom: 12px;
		font-size: 13px;
	}
	.field > span {
		color: var(--muted);
		font-size: 12px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		align-items: center;
	}
	.chip {
		border: none;
		border-radius: 12px;
		padding: 3px 10px;
		background: var(--accent-soft);
		color: var(--accent);
		font-size: 12px;
		cursor: pointer;
	}
	.chip-input {
		width: 110px;
		padding: 3px 8px;
		border-radius: 12px;
		font-size: 12px;
	}
	.preview {
		font-size: 12px;
		margin: 0;
	}
	.preview-groups {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
		gap: 10px;
	}
	.pg {
		padding: 10px 12px;
		border-radius: 8px;
		background: var(--surface-2);
		font-size: 13px;
	}
	.locs {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: 6px;
	}
	.loc {
		padding: 1px 6px;
		border-radius: 4px;
		background: var(--surface);
		border: 1px solid var(--border);
		font-size: 11px;
	}
	.bar {
		position: fixed;
		left: 50%;
		bottom: 16px;
		transform: translate(-50%, 140%);
		display: flex;
		align-items: center;
		gap: 12px;
		width: min(720px, calc(100vw - 32px));
		padding: 10px 14px;
		transition: transform 0.2s;
		z-index: 40;
	}
	.bar.show {
		transform: translate(-50%, 0);
	}
	.spacer {
		flex: 1;
	}
	.error {
		color: var(--down);
		font-size: 13px;
	}
	.ok {
		color: var(--up);
		font-weight: 600;
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.title-row {
		display: flex;
		align-items: baseline;
		gap: 12px;
		margin-bottom: 12px;
	}
	.badge-device {
		font-size: 12px;
	}
	.appearance-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 18px 40px;
	}
	.appearance .field {
		margin: 0;
	}
	.seg button {
		padding: 7px 14px;
		font-size: 13px;
	}
	.swatches,
	.fonts {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.swatch,
	.font {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 6px 12px 6px 8px;
		border: 1px solid var(--border);
		border-radius: 20px;
		background: var(--surface);
		cursor: pointer;
		font-size: 13px;
	}
	.swatch.on,
	.font.on {
		border-color: var(--accent);
		box-shadow: 0 0 0 2px var(--accent-soft);
	}
	/* Each swatch shows its light and dark shade */
	.chip-color {
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: linear-gradient(135deg, var(--l) 0 50%, var(--d) 50%);
		box-shadow: inset 0 0 0 1px #0000001a;
	}
	.font {
		border-radius: 8px;
		padding: 6px 12px;
		gap: 6px;
	}
	.font b {
		font-size: 18px;
	}
	.font[data-font-preview='serif'] b {
		font-family: 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif;
	}
	/* On a phone: cards shrink with the screen (grid items don't by default), wide tables scroll inside them */
	.grid > :global(*) {
		min-width: 0;
	}
	table {
		display: block;
		max-width: 100%;
		overflow-x: auto;
	}
</style>

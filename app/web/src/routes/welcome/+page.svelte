<script lang="ts">
	import { links } from '#lib/links.ts';
	import { goto } from '$app/navigation';
	import { appSettings, setSettings } from '#lib/settings.svelte.ts';
	import type { AppSettings, StorageGroup } from '#lib/settings.svelte.ts';

	/** First start: the few settings a new cellar needs (all changeable later in Settings). */
	let { data } = $props();

	const COMMON = ['EUR', 'USD', 'GBP', 'CHF', 'AUD', 'CAD', 'SGD', 'HKD', 'JPY', 'NZD', 'ZAR', 'SEK', 'DKK', 'NOK'];
	let currency = $state(appSettings.currency);
	let groups = $state<StorageGroup[]>([]);
	let otherGroup = $state(appSettings.other_group);
	let critic = $state('');
	let saving = $state(false);
	let error = $state('');

	// The default rates are in euros: restated in the main currency when it's one of them, else only it (add the
	// others in Settings)
	function rates(main: string): Record<string, number> {
		const base = appSettings.exchange_rates;
		if (!(main in base)) return { [main]: 1 };
		return Object.fromEntries(Object.entries(base).map(([c, r]) => [c, +(r / base[main]).toFixed(4)]));
	}

	async function save(skip = false) {
		error = '';
		saving = true;
		const body: AppSettings = skip
			? { ...appSettings }
			: {
					...appSettings,
					currency,
					exchange_rates: rates(currency),
					storage_groups: groups.filter((g) => g.name.trim() && g.prefix.trim()),
					other_group: otherGroup.trim() || 'Cellar',
					preferred_critic: critic.trim()
				};
		const res = await fetch('/api/settings', {
			method: 'PUT',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify(body)
		});
		saving = false;
		if (!res.ok) return (error = (await res.json().catch(() => ({}))).detail?.[0]?.msg ?? `Error ${res.status}`);
		setSettings(await res.json());
		goto(links.home());
	}
</script>

<svelte:head><title>Welcome · WineLib</title></svelte:head>

<div class="welcome">
	<h1>Welcome to WineLib</h1>
	<p class="muted">A few settings to start your cellar. Everything here can be changed later in Settings.</p>

	<section class="card">
		<h2>Main currency</h2>
		<p class="muted">Totals and values are shown in it; bottles bought in another are converted.</p>
		<select bind:value={currency}>
			{#each COMMON as c (c)}<option value={c}>{c}</option>{/each}
		</select>
	</section>

	<section class="card">
		<h2>Where you keep bottles</h2>
		<p class="muted">
			Optional. A storage group gathers the locations starting with its prefix (H1, H2… for Home), for the shelf
			map and the cellar's cards; bottles per bin lets the shelf map show how full each bin is.
		</p>
		{#each groups as g, i (i)}
			<div class="row">
				<input bind:value={g.name} placeholder="Home" aria-label="Group name" />
				<input class="short" bind:value={g.prefix} placeholder="H" aria-label="Prefix" />
				<input class="short" type="number" min="1" placeholder="per bin" aria-label="Bottles per bin"
					value={g.capacity ?? ''} oninput={(e) => (g.capacity = e.currentTarget.value ? +e.currentTarget.value : null)} />
				<button class="icon-btn" onclick={() => groups.splice(i, 1)} aria-label="Remove group">✕</button>
			</div>
		{/each}
		<button class="link" onclick={() => groups.push({ name: '', prefix: '', capacity: null })}>+ Add a storage group</button>
		<label class="field">
			<span>Every other location goes in</span>
			<input bind:value={otherGroup} placeholder="Cellar" />
		</label>
	</section>

	<section class="card">
		<h2>Preferred critic</h2>
		<p class="muted">Optional. Lists sort by this critic's score; without one, the first critic you add scores for.</p>
		<input bind:value={critic} list="welcome-critics" placeholder="e.g. Vinous" />
		<datalist id="welcome-critics">{#each data.critics as c (c)}<option value={c}></option>{/each}</datalist>
	</section>

	<div class="actions">
		{#if error}<span class="error">{error}</span>{/if}
		<button class="link" disabled={saving} onclick={() => save(true)}>Skip for now</button>
		<button class="btn primary" disabled={saving} onclick={() => save()}>{saving ? 'Saving…' : 'Start'}</button>
	</div>
</div>

<style>
	.welcome {
		max-width: 640px;
		margin: 0 auto;
		padding-bottom: 60px;
	}
	h1 {
		margin: 8px 0 4px;
	}
	section {
		padding: 16px 18px;
		margin-top: 14px;
	}
	h2 {
		margin: 0 0 4px;
		font-size: 15px;
	}
	section > p {
		margin: 0 0 12px;
		font-size: 13px;
	}
	input,
	select {
		padding: 6px 8px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface-2);
		min-width: 0;
		font: inherit;
	}
	.short {
		width: 90px;
	}
	.row {
		display: flex;
		gap: 8px;
		align-items: center;
		margin-bottom: 6px;
	}
	.row input:first-child {
		flex: 1;
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 5px;
		margin-top: 12px;
		font-size: 13px;
	}
	.field > span {
		color: var(--muted);
		font-size: 12px;
	}
	.icon-btn {
		border: none;
		background: none;
		color: var(--muted);
		cursor: pointer;
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		color: var(--accent);
		cursor: pointer;
		font-size: 13px;
	}
	.actions {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: 14px;
		margin-top: 18px;
	}
	.error {
		color: var(--down);
		margin-right: auto;
	}
</style>

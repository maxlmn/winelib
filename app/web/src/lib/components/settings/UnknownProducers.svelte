<script lang="ts" module>
	/** Reviews whose producer wasn't recognised, by the name to give one of yours as an alias (routers/maintenance.py) */
	export interface Unknown {
		alias: string;
		reviews: number;
		examples: string[];
		/** when several producers fit: those */
		fits: { id: number; name: string }[];
	}
</script>

<script lang="ts">
	import Combobox from '#lib/components/forms/Combobox.svelte';
	import { lookup } from '#lib/api/forms.ts';
	import type { Choice } from '#lib/api/forms.ts';
	import { plural } from '#lib/format.ts';

	/** "This is…": a producer of yours gets the name as an alias ("Also known as"); the next preview matches them. */
	let { unknown }: { unknown: Unknown[] } = $props();

	let open = $state(false);
	let aliases = $state<Record<string, string>>({});
	let chosen = $state<Record<string, Choice | null>>({});
	let saved = $state<Record<string, string>>({});
	let errors = $state<Record<string, string>>({});
	$effect(() => {
		aliases = Object.fromEntries(unknown.map((u) => [u.alias, u.alias]));
		chosen = {};
		saved = {};
		errors = {};
	});
	const reviews = $derived(unknown.reduce((n, u) => n + u.reviews, 0));

	async function save(u: Unknown, producer: { id: number | null; name: string }) {
		errors[u.alias] = '';
		const alias = (aliases[u.alias] ?? '').trim();
		if (!producer.id || !alias) return (errors[u.alias] = 'Pick one of your producers and a name');
		const res = await fetch(`/api/producers/${producer.id}/aliases`, {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ alias })
		});
		if (res.ok) saved[u.alias] = producer.name;
		else errors[u.alias] = (await res.json().catch(() => ({}))).detail ?? `Error ${res.status}`;
	}
</script>

{#if unknown.length}
	<details class="unknown" bind:open>
		<summary>
			<b>Producers not recognised</b>
			<span class="muted small">{plural(reviews, 'review')} under {plural(unknown.length, 'name')}: give one of yours the name, then Preview again</span>
		</summary>
		{#if open}
			<ul>
				{#each unknown as u, i (u.alias)}
					<li>
						<div class="head">
							<input class="alias" bind:value={aliases[u.alias]} aria-label="Name to recognise" title="Matched at the start of a review’s name" />
							<span class="muted small">{plural(u.reviews, 'review')}</span>
							{#if saved[u.alias]}
								<span class="ok small">✓ now an alias of {saved[u.alias]}: Preview again to match these</span>
							{:else}
								{#if u.fits.length}
									<span class="small muted">It is</span>
									{#each u.fits as f (f.id)}
										<button type="button" class="btn small-btn" onclick={() => save(u, f)}>{f.name}</button>
									{/each}
									<span class="small muted">or</span>
								{:else}
									<span class="small muted">It is</span>
								{/if}
								<div class="pick">
									<Combobox id="unknown-{i}" value={chosen[u.alias] ?? null} placeholder="One of your producers…"
										search={(q) => lookup<{ id: number; name: string }>('producers', { q })}
										onchange={(c) => (chosen[u.alias] = c)} />
								</div>
								<button type="button" class="btn small-btn" disabled={!chosen[u.alias]?.id}
									onclick={() => chosen[u.alias] && save(u, chosen[u.alias]!)}>Save</button>
							{/if}
							{#if errors[u.alias]}<span class="err small">{errors[u.alias]}</span>{/if}
						</div>
						<div class="examples muted small">{u.examples.map((e) => `“${e}”`).join(' · ')}</div>
					</li>
				{/each}
			</ul>
		{/if}
	</details>
{/if}

<style>
	.unknown {
		margin: 8px 0;
		padding: 8px 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface);
	}
	summary {
		cursor: pointer;
		display: flex;
		gap: 10px;
		align-items: baseline;
		flex-wrap: wrap;
	}
	ul {
		list-style: none;
		margin: 8px 0 0;
		padding: 0;
		max-height: 50vh;
		overflow-y: auto;
	}
	li {
		padding: 6px 0;
		border-top: 1px solid var(--border);
	}
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 8px;
	}
	.alias {
		width: 220px;
		padding: 3px 7px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface-2);
		color: inherit;
		font: inherit;
		font-weight: 600;
	}
	.pick {
		width: 240px;
	}
	.pick :global(input) {
		width: 100%;
		box-sizing: border-box;
	}
	.small {
		font-size: 12px;
	}
	.small-btn {
		padding: 3px 9px;
		font-size: 12px;
	}
	.examples {
		margin-top: 2px;
		font-style: italic;
	}
	.ok {
		color: var(--up);
	}
	.err {
		color: var(--down);
	}
</style>

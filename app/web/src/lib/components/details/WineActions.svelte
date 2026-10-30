<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import type { WineAction } from '#lib/api/details.ts';
	import Icon from '#lib/components/Icon.svelte';

	/** A plug-in's actions on a wine (Fetch from Robert Parker, Search again), as icon buttons among the header's: what
	 * each does on hover; while it runs its busy text, then its answer's message beside them. */
	let { wineId, actions }: { wineId: number; actions: WineAction[] } = $props();

	let state = $state<{ id: string; busy: boolean; text: string; error?: boolean } | null>(null);
	$effect(() => {
		void wineId; // another vintage: back to the buttons
		state = null;
	});

	async function act(a: WineAction) {
		if (a.confirm && !confirm(a.confirm)) return;
		state = { id: a.id, busy: true, text: a.busy ?? '…' };
		try {
			const res = await fetch(a.endpoint, { method: 'POST' });
			const body = await res.json().catch(() => ({}));
			if (!res.ok) return void (state = { id: a.id, busy: false, text: body.detail ?? `Error ${res.status}`, error: true });
			state = { id: a.id, busy: false, text: body.message ?? '' };
			if (body.reload) await invalidateAll();
		} catch {
			state = { id: a.id, busy: false, text: 'The app couldn’t be reached', error: true };
		}
	}
</script>

{#each actions as a (a.id)}
	<button class="btn icon" class:busy={state?.id === a.id && state.busy} disabled={!!state?.busy} onclick={() => act(a)}
		title={a.label} aria-label={a.label}><Icon name="search" size={15} /></button>
{/each}
{#if state?.text}<span class="said small" class:muted={!state.error} class:error={state.error} role="status">{state.text}</span>{/if}

<style>
	.busy {
		animation: pulse 1.2s ease-in-out infinite;
	}
	@keyframes pulse {
		50% {
			opacity: 0.45;
		}
	}
	.said {
		align-self: center;
		max-width: 260px;
	}
	.error {
		color: var(--down);
	}
</style>

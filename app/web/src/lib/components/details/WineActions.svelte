<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import type { WineAction } from '#lib/api/details.ts';
	import Icon from '#lib/components/Icon.svelte';

	/** A plug-in's actions on a wine (Fetch from Robert Parker, Search again), as items of the page's ⋯ menu. While
	 * one runs, `said` is its busy text, then its answer's message: the page shows it beside the menu (bound). */
	interface Props {
		wineId: number;
		actions: WineAction[];
		said?: { text: string; busy: boolean; error?: boolean } | null;
	}
	let { wineId, actions, said = $bindable(null) }: Props = $props();

	$effect(() => {
		void wineId; // another vintage: nothing said
		said = null;
	});

	async function act(a: WineAction) {
		if (a.confirm && !confirm(a.confirm)) return;
		said = { busy: true, text: a.busy ?? '…' };
		try {
			const res = await fetch(a.endpoint, { method: 'POST' });
			const body = await res.json().catch(() => ({}));
			if (!res.ok) return void (said = { busy: false, text: body.detail ?? `Error ${res.status}`, error: true });
			said = { busy: false, text: body.message ?? '' };
			if (body.reload) await invalidateAll();
		} catch {
			said = { busy: false, text: 'The app couldn’t be reached', error: true };
		}
	}
</script>

{#each actions as a (a.id)}
	<button class="menu-item" role="menuitem" disabled={!!said?.busy} onclick={() => act(a)}><Icon name="search" size={15} />{a.label}</button>
{/each}

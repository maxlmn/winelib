<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { DEMO } from '#lib/demo.ts';
	import { links } from '#lib/links.ts';

	// The server out of reach (no network, the NAS asleep, Tailscale off): say so, not a bare "500 Internal Error".
	// The browser says "online" on a network that doesn't lead to the server, so the server itself is asked.
	let unreachable = $state(typeof navigator !== 'undefined' && !navigator.onLine);
	onMount(() => {
		if (unreachable || DEMO || page.status < 500) return;
		fetch('/api/health', { cache: 'no-store' })
			.then((r) => (unreachable = !r.ok))
			.catch(() => (unreachable = true));
	});
	const failed = $derived(page.status >= 500);
</script>

<svelte:head><title>{unreachable ? 'Out of reach' : page.status} · WineLib</title></svelte:head>

<div class="err card">
	{#if unreachable}
		<div class="code small">Can’t reach WineLib</div>
		<p>Your WineLib server isn’t answering. Check that it’s running and that this device is on its network (or Tailscale), then try again.</p>
		<button class="btn primary" onclick={() => location.reload()}>Try again</button>
	{:else}
		<div class="code">{page.status}</div>
		<p>{page.status === 404 ? 'This page doesn’t exist.' : (page.error?.message ?? 'Something went wrong.')}</p>
		<div class="actions">
			{#if failed}<button class="btn primary" onclick={() => location.reload()}>Try again</button>{/if}
			<a class="btn" href={links.cellar()}>Back to the cellar</a>
		</div>
	{/if}
</div>

<style>
	.err {
		max-width: 420px;
		margin: 80px auto;
		padding: 28px;
		text-align: center;
	}
	.code {
		font-size: 42px;
		font-weight: 700;
		color: var(--accent);
	}
	.code.small {
		font-size: 24px;
	}
	p {
		color: var(--muted);
	}
	.actions {
		display: flex;
		justify-content: center;
		flex-wrap: wrap;
		gap: 8px;
	}
</style>

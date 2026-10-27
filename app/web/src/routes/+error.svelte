<script lang="ts">
	import { page } from '$app/state';
	import { links } from '#lib/links.ts';

	// No network (the installed app opened offline, or the server out of reach): say so, not a bare 500
	const offline = typeof navigator !== 'undefined' && !navigator.onLine;
</script>

<svelte:head><title>{offline ? 'Offline' : page.status} · WineLib</title></svelte:head>

<div class="err card">
	{#if offline}
		<div class="code">Offline</div>
		<p>WineLib can’t reach your server. Check the connection (or Tailscale), then try again.</p>
		<button class="btn" onclick={() => location.reload()}>Try again</button>
	{:else}
		<div class="code">{page.status}</div>
		<p>{page.status === 404 ? 'This page doesn’t exist.' : (page.error?.message ?? 'Something went wrong.')}</p>
		<a class="btn" href={links.cellar()}>Back to the cellar</a>
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
	p {
		color: var(--muted);
	}
</style>

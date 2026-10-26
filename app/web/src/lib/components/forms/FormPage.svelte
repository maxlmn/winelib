<script lang="ts">
	import './forms.css';
	import type { Snippet } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import ConfirmDialog from './ConfirmDialog.svelte';
	import { FormError } from '#lib/api/forms.ts';

	interface Props {
		title: string;
		subtitle?: string;
		saveLabel?: string;
		/** where Cancel goes when there's no history to go back to */
		fallback: string;
		/** saves and returns the URL to open next; a FormError shows in the form */
		onsave: () => Promise<string>;
		/** for edit pages: what deleting means, and the delete itself (returns the URL to open next) */
		remove?: { what: string; message: string; blocked?: boolean; run: () => Promise<string> };
		/** per-field messages from the last failed save */
		fieldErrors?: Record<string, string>;
		children: Snippet;
	}

	let { title, subtitle, saveLabel = 'Save', fallback, onsave, remove, fieldErrors = $bindable({}), children }: Props = $props();

	let error = $state('');
	let busy = $state(false);
	let confirming = $state(false);
	let formEl = $state<HTMLFormElement>();
	// Any edit marks the form dirty, so leaving asks first; saving or deleting clears it
	let dirty = $state(false);

	beforeNavigate((nav) => {
		// Leaving the page entirely (tab close, typed URL) gets the browser's own prompt via beforeunload
		if (dirty && !nav.willUnload && !confirm('Leave without saving? Your changes will be lost.')) nav.cancel();
	});

	function onBeforeUnload(e: BeforeUnloadEvent) {
		if (dirty) e.preventDefault();
	}

	function onKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !busy) {
			e.preventDefault();
			formEl?.requestSubmit();
		}
	}

	async function run(action: () => Promise<string>) {
		busy = true;
		error = '';
		let next: string;
		try {
			next = await action();
			fieldErrors = {};
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			fieldErrors = e instanceof FormError ? e.fields : {};
			confirming = false;
			window.scrollTo({ top: 0, behavior: 'smooth' });
			busy = false;
			return;
		}
		// Saved: a failed client-side navigation must not look like a failed save
		dirty = false;
		await goto(next, { replace: true }).catch(() => location.replace(next));
		busy = false;
	}

	// Editing the form retires the per-field messages (and the banner listing them)
	function clearFieldErrors() {
		dirty = true;
		if (!Object.keys(fieldErrors).length) return;
		fieldErrors = {};
		error = '';
	}

	function cancel() {
		if (history.length > 1) history.back();
		else goto(fallback);
	}
</script>

<svelte:head><title>{title} · WineLib</title></svelte:head>
<svelte:window onbeforeunload={onBeforeUnload} onkeydown={onKeydown} />

<form
	class="form"
	novalidate
	bind:this={formEl}
	onsubmit={(e) => (e.preventDefault(), run(onsave))}
	oninput={clearFieldErrors}
	onchange={() => (dirty = true)}
>
	<div class="head">
		<div>
			<h1>{title}</h1>
			{#if subtitle}<div class="muted sub">{subtitle}</div>{/if}
		</div>
	</div>

	{#if error}
		<div class="banner" role="alert">{error}</div>
	{/if}

	<div class="body">{@render children()}</div>

	<div class="actions">
		{#if remove}
			<button type="button" class="btn danger" disabled={busy} onclick={() => (confirming = true)}>Delete</button>
		{/if}
		<span class="grow"></span>
		<button type="button" class="btn" onclick={cancel}>Cancel</button>
		<button type="submit" class="btn primary" disabled={busy} title="⌘/Ctrl + Enter">{busy && !confirming ? 'Saving…' : saveLabel}</button>
	</div>
</form>

{#if remove}
	<ConfirmDialog
		open={confirming}
		title={remove.blocked ? `${remove.what.replace(/^./, (c) => c.toUpperCase())} can’t be deleted yet` : `Delete ${remove.what}?`}
		message={remove.message}
		blocked={remove.blocked}
		{busy}
		onconfirm={() => run(remove.run)}
		oncancel={() => (confirming = false)}
	/>
{/if}

<style>
	.form {
		max-width: 880px;
	}
	.head {
		margin-bottom: 18px;
	}
	.sub {
		margin-top: 2px;
	}
	.banner {
		margin-bottom: 14px;
		padding: 10px 14px;
		border-radius: var(--radius);
		border: 1px solid color-mix(in srgb, var(--down) 45%, transparent);
		background: color-mix(in srgb, var(--down) 10%, var(--surface));
		color: var(--down);
	}
	.body {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.actions {
		position: sticky;
		bottom: 0;
		z-index: 5;
		display: flex;
		gap: 8px;
		align-items: center;
		margin-top: 18px;
		padding: 12px 0;
		background: linear-gradient(to bottom, transparent, var(--bg) 30%);
	}
	.grow {
		flex: 1;
	}
	.actions .btn {
		padding: 8px 16px;
	}
</style>

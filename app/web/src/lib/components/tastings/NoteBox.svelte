<script lang="ts">
	import { saveNote } from '#lib/api/forms.ts';
	import { messageOf } from '#lib/api/http.ts';

	/** A tasting's note, written in place: saved a moment after you stop typing, and when you leave the box. */
	let { id, notes = '', label = 'Tasting note' }: { id: number; notes?: string; label?: string } = $props();

	// svelte-ignore state_referenced_locally
	let text = $state(notes);
	// svelte-ignore state_referenced_locally
	let saved = notes;
	let status = $state<'' | 'saving' | 'saved' | 'error'>('');
	let error = $state('');
	let timer: ReturnType<typeof setTimeout> | undefined;

	async function save() {
		clearTimeout(timer);
		const value = text;
		if (value.trim() === saved.trim()) return;
		status = 'saving';
		try {
			await saveNote(id, value);
			saved = value;
			// typed more while it saved: that's saved next
			status = text.trim() === value.trim() ? 'saved' : 'saving';
			if (status === 'saving') timer = setTimeout(save, 400);
		} catch (e) {
			status = 'error';
			error = messageOf(e);
		}
	}

	function typed() {
		status = '';
		clearTimeout(timer);
		timer = setTimeout(save, 900);
	}

	$effect(() => () => {
		// leaving the page with a note not yet saved: saved now
		if (text.trim() !== saved.trim()) void saveNote(id, text).catch(() => {});
		clearTimeout(timer);
	});
</script>

<div class="notebox">
	<textarea
		aria-label={label}
		placeholder="Write the note: nose, palate, how it went with the dinner…"
		bind:value={text}
		oninput={typed}
		onblur={save}
		rows="2"
	></textarea>
	<span class="status" class:err={status === 'error'} aria-live="polite">
		{#if status === 'saving'}Saving…{:else if status === 'saved'}Saved{:else if status === 'error'}Not saved: {error}{/if}
	</span>
</div>

<style>
	.notebox {
		position: relative;
	}
	textarea {
		display: block;
		width: 100%;
		box-sizing: border-box;
		min-height: 3.2em;
		field-sizing: content;
		resize: vertical;
		padding: 8px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg);
		color: var(--text);
		font: inherit;
		font-size: 15px;
		line-height: 1.5;
	}
	textarea:focus {
		outline: none;
		border-color: var(--accent);
	}
	.status {
		display: block;
		min-height: 16px;
		margin-top: 2px;
		font-size: 11px;
		color: var(--muted);
		text-align: right;
	}
	.status.err {
		color: var(--danger, #c0392b);
	}
</style>

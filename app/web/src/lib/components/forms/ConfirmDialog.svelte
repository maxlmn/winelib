<script lang="ts">
	interface Props {
		open: boolean;
		title: string;
		message: string;
		confirmLabel?: string;
		busy?: boolean;
		/** only explain why it can't be done */
		blocked?: boolean;
		onconfirm: () => void;
		oncancel: () => void;
	}

	let { open, title, message, confirmLabel = 'Delete', busy = false, blocked = false, onconfirm, oncancel }: Props = $props();

	let dialog = $state<HTMLDialogElement>();

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		else if (!open && dialog.open) dialog.close();
	});
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="confirm-title" oncancel={(e) => (e.preventDefault(), oncancel())}>
	<h2 id="confirm-title">{title}</h2>
	<p class="muted">{message}</p>
	<div class="actions">
		<button type="button" class="btn" onclick={oncancel}>{blocked ? 'OK' : 'Cancel'}</button>
		{#if !blocked}
			<button type="button" class="btn danger-fill" disabled={busy} onclick={onconfirm}>{busy ? 'Deleting…' : confirmLabel}</button>
		{/if}
	</div>
</dialog>

<style>
	dialog {
		width: min(420px, calc(100vw - 32px));
		padding: 20px 22px;
		color: var(--text);
	}
	dialog::backdrop {
		background: #0006;
	}
	h2 {
		margin: 0 0 6px;
		font-size: 17px;
	}
	p {
		margin: 0 0 18px;
	}
	.actions {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
	}
	.danger-fill {
		background: var(--down);
		border-color: var(--down);
		color: white;
	}
	.danger-fill:hover {
		color: white;
		filter: brightness(1.08);
	}
</style>

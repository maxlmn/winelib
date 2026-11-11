<script lang="ts">
	// The app's questions (lib/ask.svelte.ts), in the confirm dialog the forms use
	import ConfirmDialog from '#lib/components/forms/ConfirmDialog.svelte';
	import { answer, question } from '#lib/ask.svelte.ts';
</script>

<ConfirmDialog
	open={!!question.current}
	title={question.current?.title ?? ''}
	message={question.current?.message ?? ''}
	confirmLabel={question.current?.confirmLabel ?? 'OK'}
	plain={!question.current?.danger}
	blocked={question.current?.notice ?? false}
	onconfirm={() => answer(true)}
	oncancel={() => answer(false)}
/>

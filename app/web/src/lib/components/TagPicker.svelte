<script lang="ts">
	/** Style tags to pick: the suggested words as chips to tick, and your own word added with Enter. */
	let {
		value = $bindable([]),
		suggestions = [],
		id
	}: { value: string[]; suggestions: string[]; id?: string } = $props();

	const clean = (s: string) => s.trim().replace(/\s+/g, ' ').toLowerCase();
	// the suggestions, and any picked word that isn't one of them
	const chips = $derived([...new Set([...suggestions, ...value])]);
	let own = $state('');

	function toggle(tag: string) {
		value = value.includes(tag) ? value.filter((t) => t !== tag) : [...value, tag];
	}
	function addOwn() {
		const t = clean(own);
		if (t && !value.includes(t)) value = [...value, t];
		own = '';
	}
</script>

<div class="picker" {id}>
	{#each chips as tag (tag)}
		<button type="button" class="chip" class:on={value.includes(tag)} aria-pressed={value.includes(tag)} onclick={() => toggle(tag)}>
			{tag}
		</button>
	{/each}
	<input
		class="own"
		bind:value={own}
		placeholder="+ your own word"
		aria-label="Add your own word"
		onkeydown={(e) => {
			if (e.key === 'Enter') {
				e.preventDefault();
				addOwn();
			}
		}}
		onblur={addOwn}
	/>
</div>

<style>
	.picker {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		align-items: center;
	}
	.chip {
		padding: 3px 10px;
		border: 1px solid var(--border);
		border-radius: 12px;
		background: var(--surface);
		color: var(--muted);
		font: inherit;
		font-size: 12px;
		cursor: pointer;
	}
	.chip:hover {
		border-color: var(--accent);
	}
	.chip.on {
		border-color: var(--accent);
		background: var(--accent-soft);
		color: var(--accent);
	}
	/* beats the form fields' input rule (.form input:not(...)×3) */
	.picker input.own.own {
		width: 130px;
		padding: 3px 9px;
		border: 1px dashed var(--border);
		border-radius: 12px;
		background: transparent;
		font: inherit;
		font-size: 12px;
		color: inherit;
	}
</style>

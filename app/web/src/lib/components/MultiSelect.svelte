<script lang="ts">
	interface Props {
		label: string;
		options: { value: string; count: number }[];
		selected: string[];
		onchange: (values: string[]) => void;
		swatch?: (value: string) => string | undefined;
		/** what an option shows (its value by default) */
		format?: (value: string) => string;
	}

	let { label, options, selected, onchange, swatch, format = (v: string) => v }: Props = $props();

	let open = $state(false);
	let query = $state('');
	let root: HTMLDivElement;

	const shown = $derived(
		query ? options.filter((o) => format(o.value).toLowerCase().includes(query.toLowerCase())) : options
	);

	function toggle(value: string) {
		onchange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
	}

	function onWindowClick(e: MouseEvent) {
		if (open && !root.contains(e.target as Node)) open = false;
	}
</script>

<svelte:window onclick={onWindowClick} onkeydown={(e) => e.key === 'Escape' && (open = false)} />

<div class="ms" bind:this={root}>
	<button class="trigger" class:on={selected.length} onclick={() => (open = !open)}>
		{label}
		{#if selected.length}<span class="badge">{selected.length}</span>{/if}
		<span class="chev">▾</span>
	</button>
	{#if open}
		<div class="panel card">
			{#if options.length > 8}
				<!-- svelte-ignore a11y_autofocus -->
				<input class="search" placeholder="Filter {label.toLowerCase()}…" bind:value={query} autofocus />
			{/if}
			<div class="list">
				{#each shown as o (o.value)}
					<label>
						<input type="checkbox" checked={selected.includes(o.value)} onchange={() => toggle(o.value)} />
						{#if swatch}<span class="dot" style:background={swatch(o.value)}></span>{/if}
						<span class="val">{format(o.value)}</span>
						<span class="count muted num">{o.count}</span>
					</label>
				{:else}
					<div class="muted empty">No match</div>
				{/each}
			</div>
			{#if selected.length}
				<button class="clear" onclick={() => onchange([])}>Clear</button>
			{/if}
		</div>
	{/if}
</div>

<style>
	.ms {
		position: relative;
	}
	.trigger {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 6px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface);
		cursor: pointer;
	}
	.trigger:hover,
	.trigger.on {
		border-color: var(--accent);
	}
	.badge {
		background: var(--accent);
		color: white;
		border-radius: 10px;
		padding: 0 6px;
		font-size: 11px;
		font-weight: 600;
	}
	.chev {
		color: var(--muted);
		font-size: 10px;
	}
	.panel {
		position: absolute;
		z-index: 20;
		top: calc(100% + 4px);
		left: 0;
		width: 260px;
		padding: 6px;
	}
	.search {
		width: 100%;
		padding: 6px 8px;
		margin-bottom: 4px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface-2);
	}
	.list {
		max-height: 300px;
		overflow-y: auto;
	}
	label {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 5px 6px;
		border-radius: 6px;
		cursor: pointer;
	}
	label:hover {
		background: var(--surface-2);
	}
	.val {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.count {
		font-size: 12px;
	}
	.empty {
		padding: 8px;
	}
	.clear {
		width: 100%;
		margin-top: 4px;
		padding: 5px;
		border: none;
		background: none;
		color: var(--accent);
		cursor: pointer;
	}
</style>

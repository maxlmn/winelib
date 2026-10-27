<script lang="ts">
	import type { Choice, WineDraft } from '#lib/api/forms.ts';
	import { links } from '#lib/links.ts';

	/** Fill from a link: a shop's or Vivino's page fills the wine's fields (GET /api/lookups/from-link); a draft to
	 * check, nothing saved. */
	let { value = $bindable(), prefix }: { value: WineDraft; prefix: string } = $props();

	interface Found {
		name: string;
		url: string;
		image: string | null;
		price: number | null;
		currency: string | null;
		producer: Choice | null;
		cuvee: string;
		vintage: string;
		type: string | null;
		appellation: Choice | null;
		region: Choice | null;
		size: string | null;
		/** from the cuvée already in WineLib, as another vintage of it */
		grapes?: { id: number; name: string; share: number | null }[];
		blend?: string | null;
		lwin?: string | null;
		/** that very wine (same vintage) is already in WineLib */
		wine_id: number | null;
	}

	let url = $state('');
	let busy = $state(false);
	let error = $state('');
	let found = $state<Found | null>(null);
	const host = (u: string) => {
		try {
			return new URL(u).hostname.replace(/^www\./, '');
		} catch {
			return u;
		}
	};

	async function fill() {
		if (!url.trim() || busy) return;
		busy = true;
		error = '';
		try {
			const r = await fetch(`/api/lookups/from-link?${new URLSearchParams({ url: url.trim() })}`);
			const body = await r.json();
			if (!r.ok) throw new Error(body.detail ?? 'The page couldn’t be read');
			found = body as Found;
			// What the page says, over the form's empty or older values; nothing where it says nothing
			if (found.producer) value.producer = found.producer;
			if (found.cuvee) value.cuvee = found.cuvee;
			if (found.vintage) value.vintage = found.vintage;
			if (found.type) value.type = found.type;
			if (found.appellation) value.appellation = found.appellation;
			if (found.region) value.region = found.region;
			// the cuvée's grapes, blend and LWIN when it's one WineLib knows, where the form has none
			if (found.grapes?.length && !value.grapes.some((g) => g.varietal))
				value.grapes = found.grapes.map((g) => ({ varietal: { id: g.id, name: g.name }, share: g.share }));
			if (found.blend && !value.blend) value.blend = found.blend;
			if (found.lwin && !value.lwin) value.lwin = found.lwin;
		} catch (e) {
			found = null;
			error = e instanceof Error ? e.message : 'The page couldn’t be read';
		} finally {
			busy = false;
		}
	}
</script>

<div class="link">
	<label for="{prefix}-link">Fill from a link</label>
	<div class="row">
		<input
			id="{prefix}-link"
			type="url"
			bind:value={url}
			placeholder="A shop’s or Vivino’s page for this wine"
			onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), fill())}
		/>
		<button type="button" class="btn" onclick={fill} disabled={busy || !url.trim()}>{busy ? 'Reading…' : 'Fill'}</button>
	</div>
	{#if error}<p class="error">{error}</p>{/if}
	{#if found}
		<div class="found">
			{#if found.image}<img src={found.image} alt="" referrerpolicy="no-referrer" />{/if}
			<div>
				<div>Filled from <b>{host(found.url)}</b>: “{found.name}”. Check the fields below.</div>
				{#if found.price}<div class="muted">Its price there: {found.price.toLocaleString()} {found.currency ?? ''}{found.size ? ` (${found.size})` : ''}</div>{/if}
				{#if found.producer && found.producer.id === null}<div class="muted">{found.producer.name} isn’t in WineLib yet: it will be created.</div>{/if}
				{#if found.wine_id}<div>This wine is already in WineLib: <a href={links.wine(found.wine_id)}>open it</a>.</div>{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.link {
		grid-column: 1 / -1;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding-bottom: 14px;
		margin-bottom: 4px;
		border-bottom: 1px dashed var(--border);
	}
	label {
		font-size: 13px;
		font-weight: 600;
	}
	.row {
		display: flex;
		gap: 8px;
	}
	input {
		flex: 1;
		min-width: 0;
	}
	.error {
		margin: 0;
		color: var(--down);
		font-size: 13px;
	}
	.found {
		display: flex;
		gap: 12px;
		align-items: flex-start;
		font-size: 13px;
		padding: 10px;
		border-radius: 8px;
		background: var(--surface-2);
	}
	.found img {
		width: 48px;
		height: 64px;
		object-fit: contain;
		flex: none;
		background: #fff;
		border-radius: 4px;
	}
</style>

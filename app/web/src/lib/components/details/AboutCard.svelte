<script lang="ts">
	/** A photo and a short description of a grape, from Wikipedia (see app/api/wiki.py).
	 *  Loaded after the page so it never holds it up; hidden when there's nothing to show. */
	import { links } from '#lib/links.ts';
	interface About {
		found: boolean;
		error?: string;
		title?: string;
		description?: string | null;
		extract?: string;
		image?: string | null;
		image_full?: string | null;
		url?: string;
	}

	let { src }: { src: string } = $props();

	let about = $state<About | null>(null);
	let expanded = $state(false);
	// The thumbnail, then the full picture if it won't load, then no picture
	let photo = $state<string | null>(null);
	function photoFailed() {
		photo = photo !== about?.image_full && about?.image_full ? about.image_full : null;
	}

	$effect(() => {
		let cancelled = false;
		about = null;
		expanded = false;
		fetch(src)
			.then((r) => (r.ok ? r.json() : null))
			.then((d: About | null) => {
				if (cancelled) return;
				about = d;
				photo = d?.image ?? d?.image_full ?? null;
			})
			.catch(() => {});
		return () => (cancelled = true);
	});

	// Long extracts fold after a few sentences
	const LIMIT = 520;
	const long = $derived((about?.extract?.length ?? 0) > LIMIT);
	const text = $derived.by(() => {
		const t = about?.extract ?? '';
		if (expanded || !long) return t;
		const cut = t.slice(0, LIMIT);
		const end = cut.lastIndexOf('. ') + 1;
		// End on a full sentence when there's one; otherwise mark the cut
		return end >= 200 ? cut.slice(0, end) : `${cut.slice(0, cut.lastIndexOf(' '))}…`;
	});
</script>

{#if about?.found}
	<section class="card about" class:has-image={!!photo}>
		{#if photo}
			<a class="photo" href={about.image_full ?? photo} target="_blank" rel="noreferrer" title="Open the full picture">
				<img src={photo} alt={about.title} decoding="async" referrerpolicy="no-referrer" onerror={photoFailed} />
			</a>
		{/if}
		<div class="text">
			<h2>{about.title}</h2>
			{#if about.description}<div class="muted desc">{about.description}</div>{/if}
			<p>{text}</p>
			<div class="foot">
				{#if long}<button class="link" onclick={() => (expanded = !expanded)}>{expanded ? 'Less' : 'More'}</button>{/if}
				<a class="source" href={about.url} target="_blank" rel="noreferrer">Read more on Wikipedia ↗</a>
				<span class="muted small">Text: Wikipedia, CC BY-SA 4.0 · <a href={links.about()}>sources</a></span>
			</div>
		</div>
	</section>
{/if}

<style>
	.about {
		display: grid;
		grid-template-columns: 1fr;
		gap: 18px;
		padding: 16px 18px;
		margin-bottom: 14px;
	}
	.about.has-image {
		grid-template-columns: minmax(180px, 280px) 1fr;
	}
	.photo {
		display: block;
		border-radius: 10px;
		overflow: hidden;
		background: var(--surface-2);
		align-self: start;
	}
	img {
		display: block;
		width: 100%;
		max-height: 260px;
		object-fit: cover;
	}
	h2 {
		font-size: 15px;
		margin: 0;
	}
	.desc {
		font-size: 12px;
		margin-top: 2px;
	}
	p {
		margin: 8px 0 0;
		font-size: 13px;
		line-height: 1.55;
	}
	.foot {
		display: flex;
		gap: 14px;
		align-items: baseline;
		margin-top: 8px;
		font-size: 12px;
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		color: var(--link);
		text-decoration: var(--link-decoration, none);
		cursor: pointer;
		font-size: 12px;
	}
	.link:hover {
		color: var(--accent);
	}
	.source {
		color: var(--muted);
	}
	.source:hover {
		color: var(--accent);
	}
	@media (max-width: 640px) {
		.about.has-image {
			grid-template-columns: 1fr;
		}
	}
</style>

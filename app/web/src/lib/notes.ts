/** Notes written in the app or imported (the evening's menu, a tasting's note): Markdown, rendered safely: no raw
 * HTML (shown as text), no images, links only to web pages; a line break is a line break (as written). */
import { Marked } from 'marked';

const escape = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const notes = new Marked({
	gfm: true,
	breaks: true,
	renderer: {
		html: ({ text }) => escape(text),
		image: ({ text }) => escape(text)
	}
});

export function noteHtml(md: string): string {
	const html = notes.parse(md, { async: false }) as string;
	// links: to web pages only (a new tab), others kept as their text
	return html.replace(/<a href="([^"]*)"([^>]*)>(.*?)<\/a>/g, (_, href: string, rest: string, text: string) =>
		/^https?:/i.test(href) ? `<a href="${href}"${rest} target="_blank" rel="noreferrer">${text}</a>` : text
	);
}

/** A note as one plain run of text (a card's excerpt): no headings' #, no bullets, no emphasis. */
export function plainText(md: string): string {
	return md
		.split('\n')
		.map((l) =>
			l
				.replace(/^\s*#+\s*/, '')
				.replace(/^\s*([-*+]|\d+\.)\s+/, '')
				.replace(/^\s*>\s?/, '')
				.replace(/^\s*\|.*\|\s*$/, '')
				.replace(/(\*\*|__|\*|_|`)(.+?)\1/g, '$2')
				.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
				.trim()
		)
		.filter(Boolean)
		.join(' · ');
}

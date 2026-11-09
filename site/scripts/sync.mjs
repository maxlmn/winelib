// The site's pages that live in the app: the help guides, About the data, the MCP server's README, and the
// screenshots, copied in before each build so the site and the app say the same. The copies are git-ignored.
import { cpSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const site = join(dirname(fileURLToPath(import.meta.url)), '..');
const app = join(site, '..');
const docs = join(site, 'src', 'content', 'docs');

/** A Markdown file as a page: its first "# Title" becomes the front matter's title */
function page(src, dest, { order, title, description, intro = '' } = {}) {
	let text = readFileSync(src, 'utf8').replace(/\r\n/g, '\n');
	const h1 = text.match(/^# (.+)\n+/);
	if (h1) text = text.slice(h1[0].length);
	const fm = [`title: ${JSON.stringify(title ?? h1?.[1] ?? 'WineLib')}`];
	if (description) fm.push(`description: ${JSON.stringify(description)}`);
	if (order !== undefined) fm.push(`sidebar:\n  order: ${order}`);
	fm.push('editUrl: false');
	mkdirSync(dirname(dest), { recursive: true });
	writeFileSync(dest, `---\n${fm.join('\n')}\n---\n\n${intro}${text}`);
}

// The guides (app/api/data/docs/help/NN-name.md → /guide/name/)
const guides = join(docs, 'guide');
rmSync(guides, { recursive: true, force: true });
for (const f of readdirSync(join(app, 'app/api/data/docs/help')).filter((f) => f.endsWith('.md')).sort()) {
	const [, n, name] = f.match(/^(\d+)-(.+)\.md$/) ?? [null, '99', f.replace(/\.md$/, '')];
	page(join(app, 'app/api/data/docs/help', f), join(guides, `${name}.md`), { order: +n });
}

// About the data: its sources and how it was built, one page as in the app
const about = join(docs, 'about');
rmSync(about, { recursive: true, force: true });
mkdirSync(about, { recursive: true });
const sources = readFileSync(join(app, 'app/api/data/docs/sources.md'), 'utf8');
const built = readFileSync(join(app, 'app/api/data/docs/how-built.md'), 'utf8');
writeFileSync(join(about, 'data.md'), `---\ntitle: "About the data"\ndescription: "Where WineLib's reference data and maps come from, and their licences."\neditUrl: false\n---\n\n${sources}\n\n${built}`);

// The MCP server
page(join(app, 'app/mcp_server/README.md'), join(docs, 'mcp.md'), {
	title: 'Ask your AI assistant',
	description: 'The MCP server: Claude, or any assistant that speaks MCP, reads your cellar and journal.'
});

// The screenshots
rmSync(join(site, 'public', 'screenshots'), { recursive: true, force: true });
cpSync(join(app, 'screenshots'), join(site, 'public', 'screenshots'), { recursive: true });
console.log('sync: guides, about, mcp and screenshots copied from the app');

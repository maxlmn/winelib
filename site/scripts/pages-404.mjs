// After the build: GitHub Pages answers every missing address with the site's one 404.html, the demo's pages too
// (/winelib/demo/cellar opened directly, or reloaded). Its 404 page sends those to the demo, the route as ?route=,
// which the demo puts back (app/web/src/hooks.client.ts); any other address keeps the site's 404 page.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const file = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist', '404.html');
const demo = `${(process.env.BASE_PATH || '/winelib').replace(/\/$/, '')}/demo/`;
const script = `<script>(function(){var d=${JSON.stringify(demo)},p=location.pathname;` +
	`if(p.indexOf(d)===0&&p!==d)location.replace(d+'?route='+encodeURIComponent(p.slice(d.length-1)+location.search+location.hash));})();</script>`;
const html = readFileSync(file, 'utf8');
if (!html.includes('?route=')) writeFileSync(file, html.replace('<head>', `<head>${script}`));
console.log('404.html: sends', demo, 'pages to the demo');

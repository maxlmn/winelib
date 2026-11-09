import { base } from '#lib/base.ts';
import { DEMO, installDemoFetch } from '#lib/demo.ts';

if (DEMO) {
	// The static demo answers the API from saved files: in place before any page asks
	installDemoFetch();
	// GitHub Pages has one 404 page for the whole site: it sends a demo page opened directly (a link, a reload) to the
	// demo's own address with ?route=, put back here before the app reads the address
	const route = new URLSearchParams(location.search).get('route');
	if (route?.startsWith('/')) history.replaceState(history.state, '', base + route);
}

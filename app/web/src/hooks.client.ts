import { DEMO, installDemoFetch } from '#lib/demo.ts';

// The static demo answers the API from saved files: in place before any page asks
if (DEMO) installDemoFetch();

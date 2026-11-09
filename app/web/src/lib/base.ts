import { resolve } from '$app/paths';

/** The app's sub-path ('' at the root; '/winelib/demo' for the static demo: BASE_PATH at build) */
export const base = resolve('/').replace(/\/$/, '');

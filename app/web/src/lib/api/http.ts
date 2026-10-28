/** Requests to the API, in one place: a page's data (loadJson: the error page when it fails), and what a page sends
 * or asks for itself (request: a RequestError with the server's message, a network failure included, for the page
 * to show). */
import { error } from '@sveltejs/kit';

type Fetch = typeof fetch;

/** A request that failed: the message to show, and per field when the server named them (a form) */
export class RequestError extends Error {
	constructor(
		message: string,
		public fields: Record<string, string> = {},
		public status = 0
	) {
		super(message);
	}
}

type PydanticError = { loc: (string | number)[]; msg: string };

// loc looks like ["body", "wine", "WineIn", "producer", "NewProducer", "name"]: keep the snake_case field names
const fieldOf = (loc: (string | number)[]) =>
	loc.filter((x): x is string => typeof x === 'string' && /^[a-z][a-z_]*$/.test(x) && x !== 'body' && x !== 'int').join('.');

const pretty = (field: string) => (field.split('.').pop() ?? '').replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());

/** The server's message for a failed response (FastAPI's detail: a text, or Pydantic's errors per field, into
 * `fields`); a proxy's HTML page or an empty body says only the status */
export async function errorMessage(r: Response, fields: Record<string, string> = {}) {
	const body = await r.json().catch(() => null);
	const detail = body?.detail;
	if (typeof detail === 'string') return detail;
	if (Array.isArray(detail)) {
		// A union (id or new name) reports a failure per branch: drop the "not an integer" noise
		const errs = (detail as PydanticError[]).filter((e) => !/valid integer/.test(e.msg) || detail.length === 1);
		for (const e of errs) fields[fieldOf(e.loc)] ??= e.msg.replace(/^Value error, /, '');
		return Object.entries(fields)
			.map(([f, m]) => (f ? `${pretty(f)}: ${m}` : m))
			.join(' · ');
	}
	return `Request failed (${r.status})`;
}

/** A page's data in its load: the 404 page when it isn't there (a non-numeric id is the API's 422), the error page
 * otherwise. `what` names it in those pages ("List not found"); without, the server's message. */
export async function loadJson<T>(fetch: Fetch, url: string, what?: string): Promise<T> {
	const r = await fetch(url);
	if (r.status === 404 || r.status === 422) error(404, what ? `${what} not found` : await errorMessage(r));
	if (!r.ok) error(r.status, what ? `Couldn’t load the ${what.toLowerCase()}` : await errorMessage(r));
	return r.json();
}

/** A request from a page (GET by default; a body is sent as JSON): its JSON, or a RequestError to show (the server's
 * message, per field for a form; "couldn't reach" when the network or the app is down). Aborted (`signal`): the
 * AbortError as is, for the caller to ignore. */
export async function request<T = unknown>(
	url: string,
	{ method = 'GET', body, signal }: { method?: 'GET' | 'POST' | 'PUT' | 'DELETE'; body?: unknown; signal?: AbortSignal } = {}
): Promise<T> {
	let r: Response;
	try {
		r = await fetch(url, {
			method,
			signal,
			headers: body === undefined ? {} : { 'content-type': 'application/json' },
			body: body === undefined ? undefined : JSON.stringify(body)
		});
	} catch (e) {
		if (e instanceof DOMException && e.name === 'AbortError') throw e;
		throw new RequestError('Couldn’t reach WineLib: check your connection and try again');
	}
	if (!r.ok) {
		const fields: Record<string, string> = {};
		throw new RequestError(await errorMessage(r, fields), fields, r.status);
	}
	if (r.status === 204) return undefined as T;
	return r.json().catch(() => {
		throw new RequestError(`The answer couldn’t be read (${r.status})`, {}, r.status);
	});
}

/** A failure's message for the page (a RequestError's, else a generic one) */
export const messageOf = (e: unknown) => (e instanceof Error && e.message ? e.message : 'Something went wrong');

/** Aborted on purpose (a newer search started): not an error to show */
export const aborted = (e: unknown) => e instanceof DOMException && e.name === 'AbortError';

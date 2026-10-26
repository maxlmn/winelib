/** Occasion photos: one per place and day (see app/api/photos.py). */
import { forgetJournal } from './tastings.ts';

export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
export const MAX_PHOTO_MB = 15;

/** Photo URLs from the API are the full-size originals (versioned: cached for good). Pages show resized JPEG
 * copies instead: `thumb` (~480 px) in lists and cards, `large` (~1600 px) where a photo is shown big. */
export const photoSrc = (url: string, size: 'thumb' | 'large') => `${url}${url.includes('?') ? '&' : '?'}size=${size}`;

const query = (place: string, date: string) => `place=${encodeURIComponent(place)}&date=${encodeURIComponent(date)}`;

async function detail(res: Response) {
	const body = await res.json().catch(() => ({}));
	return typeof body.detail === 'string' ? body.detail : `Error ${res.status}`;
}

export async function photoFor(place: string, date: string): Promise<string | null> {
	const res = await fetch(`/api/photos?${query(place, date)}`);
	return res.ok ? (await res.json()).url : null;
}

export async function uploadPhoto(place: string, date: string, file: File): Promise<string> {
	const res = await fetch(`/api/photos?${query(place, date)}`, { method: 'PUT', headers: { 'content-type': file.type }, body: file });
	if (!res.ok) throw new Error(await detail(res));
	forgetJournal();
	return (await res.json()).url;
}

export async function deletePhoto(place: string, date: string) {
	const res = await fetch(`/api/photos?${query(place, date)}`, { method: 'DELETE' });
	if (!res.ok) throw new Error(await detail(res));
	forgetJournal();
}

/** Applies the form's photo choice once the note or visit is saved; never throws (the save already happened). */
export async function applyPhotoChange(place: string | null | undefined, date: string, change: { file: File | null; remove: boolean }) {
	if (!place || !date || (!change.file && !change.remove)) return;
	try {
		if (change.file) await uploadPhoto(place, date, change.file);
		else await deletePhoto(place, date);
	} catch (e) {
		alert(`Saved, but the photo couldn’t be ${change.file ? 'uploaded' : 'removed'}: ${e instanceof Error ? e.message : e}`);
	}
}

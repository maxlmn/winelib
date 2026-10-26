/** Places: a friend's home (the type Friend's Place) is shown as a house, who it is and the city; your own homes
 * (Home) as a solid house. */
export const FRIENDS = "Friend's Place";

export const isFriends = (type: string | null | undefined) => type === FRIENDS;
/** one of your own homes */
export const isHome = (type: string | null | undefined) => type === 'Home';

/** The line under a place's name: its city, and its type unless it says nothing more (a home, a friend's) */
export const placeMeta = (p: { city?: string | null; type?: string | null }) =>
	[p.city, p.type && p.type !== 'Home' && !isFriends(p.type) ? p.type : null].filter(Boolean).join(' · ');

/** The place types to suggest, Friend's Place always among them */
export const withFriends = (types: string[]) => (types.includes(FRIENDS) ? types : [...types, FRIENDS]);

import type { Driver } from "../..";
type DriverFactory<OptionsT, InstanceT> = (opts: OptionsT) => Driver<OptionsT, InstanceT>;
interface ErrorOptions {
}
export declare function defineDriver<OptionsT = any, InstanceT = never>(factory: DriverFactory<OptionsT, InstanceT>): DriverFactory<OptionsT, InstanceT>;
export declare function normalizeKey(key: string | undefined, sep?: ":" | "/"): string;
export declare function joinKeys(...keys: string[]): string;
/**
 * Percent-encode a single URL path segment.
 *
 * Throws for empty, `.` and `..` segments (that URL parsers would collapse)
 * and for malformed unicode (lone surrogates).
 */
export declare function encodeURLSegment(driver: string, segment: string, key?: string): string;
/**
 * Encode a key as a URL path (`a:b` => `a/b`) with each segment
 * percent-encoded, so that the key can never escape the base URL or inject
 * a `?query` / `#hash`.
 */
export declare function encodeURLKey(driver: string, key: string | undefined): string;
/**
 * Validate a key that a third-party SDK puts into a URL path *without*
 * encoding it, so that the key can never escape its path.
 *
 * Throws for empty keys, `?` / `#`, control characters, leading / trailing
 * spaces and `.` / `..` segments (including the `%2e` spelling).
 */
export declare function assertURLPathKey(driver: string, key: string): string;
/**
 * Escape glob special characters (`*`, `?`, `[`, `]`, `\`) so that a key
 * prefix can be used literally in a redis `SCAN MATCH` pattern.
 */
export declare function escapeRedisGlob(pattern: string): string;
export declare function createError(driver: string, message: string, opts?: ErrorOptions): Error;
export declare function createRequiredError(driver: string, name: string | string[]): Error;
export {};

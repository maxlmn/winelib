/**
 * Merges caller-provided operation overrides over the defaults. Iterating the
 * default keys (rather than the override's own keys) means nullish members
 * fall back to the default, and inherited members — e.g. from a class
 * instance — are picked up.
 *
 * @template {Record<string, any>} T
 * @param {T} defaults
 * @param {Partial<T> | undefined} overrides
 * @returns {T}
 */
export declare function merge_operations<T extends Record<string, any>>(defaults: T, overrides: Partial<T> | undefined): T;
export declare const default_stringify_operations: Readonly<import("./types.js").DefaultStringifyOperations>;
export declare const default_parse_operations: Readonly<import("./types.js").DefaultParseOperations>;
//# sourceMappingURL=operations.d.ts.map
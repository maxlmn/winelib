/** @type {Record<string, string>} */
export declare const escaped: Record<string, string>;
export declare class DevalueError extends Error {
    path: string;
    value: any;
    root: any;
    /**
     * @param {string} message
     * @param {string[]} keys
     * @param {any} [value] - The value that failed to be serialized
     * @param {any} [root] - The root value being serialized
     */
    constructor(message: string, keys: string[], value?: any, root?: any);
}
/**
 * Marks a Map key on the path being serialized. The key itself is recorded
 * right after the marker, so nothing is formatted or allocated per entry.
 */
export declare const MAP_KEY: unique symbol;
/**
 * Formats the path recorded on the way to the value being serialized — a
 * property key, an array index, or `MAP_KEY` followed by a Map key — into
 * the segments a `DevalueError` joins. Only runs when an error is raised.
 * @param {any[]} keys
 * @param {(key: any) => string} format_map_key
 * @returns {string[]}
 */
export declare function format_path(keys: any[], format_map_key: (key: any) => string): string[];
/** @param {any} thing */
export declare function is_primitive(thing: any): boolean;
/** @param {any} thing */
export declare function is_plain_object(thing: any): boolean;
/** @param {any} thing */
export declare function get_type(thing: any): string;
/** @param {any} thing */
export declare function is_buffer(thing: any): boolean;
/**
 * Emit an array whose storage is not proportional to its declared length.
 * Touching and deleting the largest valid index forces dictionary elements
 * before setting the length; assigning .length on [] can still eagerly allocate.
 * @param {number} length
 */
export declare function stringify_sparse_array(length: number): string;
/** Returns the compact JavaScript identifier at `index`. @param {number} index */
export declare function get_name(index: number): string;
/** @param {string} str */
export declare function stringify_string(str: string): string;
/** @param {string} key */
export declare function quote_key(key: string): string;
/** @param {Record<string | symbol, any>} object */
export declare function enumerable_symbols(object: Record<string | symbol, any>): symbol[];
/** @param {number} n */
export declare function is_valid_array_index(n: number): boolean;
/** @param {number} n */
export declare function is_valid_array_len(n: number): boolean;
/**
 * Finds the populated indices of an array.
 * @param {unknown[]} array
 */
export declare function valid_array_indices(array: unknown[]): string[];
/**
 * Given the own enumerable string keys of an array-like value, in property
 * order, returns the leading run of them that are valid array indices.
 *
 * This is the filtering half of the `indicesOf` stringify operation,
 * exposed so that custom operations — which typically already have the keys
 * in hand, e.g. from a foreign runtime — don't have to reimplement it.
 *
 * Does not modify `keys`.
 *
 * @param {readonly string[]} keys
 * @returns {string[]}
 */
export declare function filter_array_indices(keys: readonly string[]): string[];
//# sourceMappingURL=utils.d.ts.map
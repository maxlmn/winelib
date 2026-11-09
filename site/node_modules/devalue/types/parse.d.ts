/**
 * Revive a value serialized with `devalue.stringify`
 * @param {string} serialized
 * @param {Record<string, (value: any) => any>} [revivers]
 * @param {import('./types.js').ParseOptions} [options]
 */
export declare function parse(serialized: string, revivers?: Record<string, (value: any) => any>, options?: import('./types.js').ParseOptions): any;
/**
 * Revive a value flattened with `devalue.stringify`
 * @param {number | any[]} parsed
 * @param {Record<string, (value: any) => any>} [revivers]
 * @param {import('./types.js').ParseOptions} [options]
 */
export declare function unflatten(parsed: number | any[], revivers?: Record<string, (value: any) => any>, options?: import('./types.js').ParseOptions): any;
//# sourceMappingURL=parse.d.ts.map
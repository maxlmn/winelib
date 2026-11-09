/**
 * Turn a value into a JSON string that can be parsed with `devalue.parse`
 * @param {any} value
 * @param {Record<string, (value: any) => any>} [reducers]
 * @param {import('./types.js').StringifyOptions} [options]
 */
export declare function stringify(value: any, reducers?: Record<string, (value: any) => any>, options?: import('./types.js').StringifyOptions): string;
/**
 * Turn a value into a JSON string that can be parsed with `devalue.parse`
 * @param {any} value
 * @param {Record<string, (value: any) => any>} [reducers]
 * @param {import('./types.js').StringifyOptions} [options]
 */
export declare function stringifyAsync(value: any, reducers?: Record<string, (value: any) => any>, options?: import('./types.js').StringifyOptions): Promise<string>;
//# sourceMappingURL=stringify.d.ts.map
declare const SOURCE: unique symbol;
export declare class JavaScriptSource {
    strings: TemplateStringsArray;
    values: unknown[];
    /**
     * @param {TemplateStringsArray} strings
     * @param {unknown[]} values
     */
    constructor(strings: TemplateStringsArray, values: unknown[]);
    /**
     * @param {(value: unknown) => string} fn
     */
    render(fn: (value: unknown) => string): string;
    /**
     * @param {(value: unknown) => void} fn
     * @param {Set<string>} reserved
     * @param {Set<readonly string[]>} templates
     */
    visit(fn: (value: unknown) => void, reserved: Set<string>, templates: Set<readonly string[]>): void;
    /**
     * @param {unknown} value
     * @returns {value is JavaScriptFragment}
     */
    static is_fragment(value: unknown): value is JavaScriptFragment;
    /**
     * @param {JavaScriptFragment} fragment
     * @returns {JavaScriptSource}
     */
    static from(fragment: JavaScriptFragment): JavaScriptSource;
}
/**
 * @param {TemplateStringsArray} strings
 * @param {...unknown} values
 * @returns {JavaScriptFragment}
 */
export declare function js(strings: TemplateStringsArray, ...values: unknown[]): JavaScriptFragment;
export type JavaScriptFragment = {
    readonly [SOURCE]: JavaScriptSource;
};
export {};
/**
 * The opaque result of the `js` tag passed to an `uneval` replacer.
 * @typedef {{ readonly [SOURCE]: JavaScriptSource }} JavaScriptFragment
 */
//# sourceMappingURL=javascript-source.d.ts.map
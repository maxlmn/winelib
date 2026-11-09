/**
 * Get the plain-text value of a node.
 *
 * ###### Algorithm
 *
 * *   if `tree` is a comment, returns its `value`
 * *   if `tree` is a text, applies normal whitespace collapsing to its
 *     `value`, as defined by the CSS Text spec
 * *   if `tree` is a root or element, applies an algorithm similar to the
 *     `innerText` getter as defined by HTML
 *
 * ###### Notes
 *
 * > 👉 **Note**: the algorithm acts as if `tree` is being rendered, and as if
 * > we’re a CSS-supporting user agent, with scripting enabled.
 *
 * *   if `tree` is an element that is not displayed (such as a `head`), we’ll
 *     still use the `innerText` algorithm instead of switching to `textContent`
 * *   if descendants of `tree` are elements that are not displayed, they are
 *     ignored
 * *   CSS is not considered, except for the default user agent style sheet
 * *   a line feed is collapsed instead of ignored in cases where Fullwidth, Wide,
 *     or Halfwidth East Asian Width characters are used, the same goes for a case
 *     with Chinese, Japanese, or Yi writing systems
 * *   replaced elements (such as `audio`) are treated like non-replaced elements
 *
 * @param {Nodes} tree
 *   Tree to turn into text.
 * @param {Readonly<Options> | null | undefined} [options]
 *   Configuration (optional).
 * @returns {string}
 *   Serialized `tree`.
 */
export function toText(tree: Nodes, options?: Readonly<Options> | null | undefined): string;
/**
 * Any value for a break after.
 */
export type BreakAfter = BreakForce | BreakNumber | BreakValue | undefined;
/**
 * Any value for a break before.
 */
export type BreakBefore = BreakNumber | BreakValue | undefined;
/**
 * Forced break.
 */
export type BreakForce = "\n";
/**
 * Specific break:
 *
 * *   `0` — space
 * *   `1` — line ending
 * *   `2` — blank line
 */
export type BreakNumber = 0 | 1 | 2;
/**
 * Whether there was a break.
 */
export type BreakValue = boolean;
/**
 * Info on current collection.
 */
export type CollectionInfo = {
    /**
     *   Whether there was a break after.
     */
    breakAfter: BreakAfter;
    /**
     *   Whether there was a break before.
     */
    breakBefore: BreakBefore;
    /**
     * Whether a row comes later in the nearest table, after the current node or
     * after the row group it is in.
     */
    rowAfter?: boolean | undefined;
    /**
     *   Current whitespace setting.
     */
    whitespace: Whitespace;
};
/**
 * Configuration.
 */
export type Options = {
    /**
     * Initial CSS whitespace setting to use (default: `'normal'`).
     */
    whitespace?: Whitespace | null | undefined;
};
/**
 * Valid and useful whitespace values (from CSS).
 */
export type Whitespace = "normal" | "nowrap" | "pre" | "pre-wrap";
import type { Nodes } from 'hast';
//# sourceMappingURL=index.d.ts.map
/**
 * Create an extension for `mdast-util-from-markdown` to enable directives in
 * markdown.
 *
 * @param {Readonly<FromMarkdownOptions> | null | undefined} [options]
 *   Configuration (optional).
 * @returns {FromMarkdownExtension}
 *   Extension for `mdast-util-from-markdown` to enable directives.
 */
export function directiveFromMarkdown(options?: Readonly<FromMarkdownOptions> | null | undefined): FromMarkdownExtension;
/**
 * Create an extension for `mdast-util-to-markdown` to enable directives in
 * markdown.
 *
 * @param {Readonly<ToMarkdownOptions> | null | undefined} [options]
 *   Configuration (optional).
 * @returns {ToMarkdownExtension}
 *   Extension for `mdast-util-to-markdown` to enable directives.
 */
export function directiveToMarkdown(options?: Readonly<ToMarkdownOptions> | null | undefined): ToMarkdownExtension;
import type { FromMarkdownOptions } from 'mdast-util-directive';
import type { Extension as FromMarkdownExtension } from 'mdast-util-from-markdown';
import type { ToMarkdownOptions } from 'mdast-util-directive';
import type { Options as ToMarkdownExtension } from 'mdast-util-to-markdown';
//# sourceMappingURL=index.d.ts.map
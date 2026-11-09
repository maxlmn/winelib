/**
 * Create an automatic runtime.
 *
 * @param {ReturnType<CreateH>} f
 *   `h` function.
 * @returns
 *   Automatic JSX runtime.
 */
export function createAutomaticRuntime(f: ReturnType<typeof CreateH>): {
    Fragment: null;
    jsxDEV: {
        /**
         * Create a root or an element.
         *
         * @overload
         * @param {null} type
         *   `null` to get a root.
         * @param {{children?: Child}} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Root}
         *   Root.
         *
         * @overload
         * @param {string} type
         *   Element name.
         * @param {JSXProps} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Element}
         *   Element.
         *
         * @param {string | null} type
         *   Element name or `null` to get a root.
         * @param {Properties & {children?: Child}} properties
         *   Properties.
         * @returns {Result}
         *   Result.
         */
        (type: null, properties: {
            children?: Child;
        }, key?: string | null | undefined): Root;
        /**
         * Create a root or an element.
         *
         * @overload
         * @param {null} type
         *   `null` to get a root.
         * @param {{children?: Child}} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Root}
         *   Root.
         *
         * @overload
         * @param {string} type
         *   Element name.
         * @param {JSXProps} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Element}
         *   Element.
         *
         * @param {string | null} type
         *   Element name or `null` to get a root.
         * @param {Properties & {children?: Child}} properties
         *   Properties.
         * @returns {Result}
         *   Result.
         */
        (type: string, properties: JSXProps, key?: string | null | undefined): Element;
    };
    jsxs: {
        /**
         * Create a root or an element.
         *
         * @overload
         * @param {null} type
         *   `null` to get a root.
         * @param {{children?: Child}} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Root}
         *   Root.
         *
         * @overload
         * @param {string} type
         *   Element name.
         * @param {JSXProps} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Element}
         *   Element.
         *
         * @param {string | null} type
         *   Element name or `null` to get a root.
         * @param {Properties & {children?: Child}} properties
         *   Properties.
         * @returns {Result}
         *   Result.
         */
        (type: null, properties: {
            children?: Child;
        }, key?: string | null | undefined): Root;
        /**
         * Create a root or an element.
         *
         * @overload
         * @param {null} type
         *   `null` to get a root.
         * @param {{children?: Child}} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Root}
         *   Root.
         *
         * @overload
         * @param {string} type
         *   Element name.
         * @param {JSXProps} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Element}
         *   Element.
         *
         * @param {string | null} type
         *   Element name or `null` to get a root.
         * @param {Properties & {children?: Child}} properties
         *   Properties.
         * @returns {Result}
         *   Result.
         */
        (type: string, properties: JSXProps, key?: string | null | undefined): Element;
    };
    jsx: {
        /**
         * Create a root or an element.
         *
         * @overload
         * @param {null} type
         *   `null` to get a root.
         * @param {{children?: Child}} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Root}
         *   Root.
         *
         * @overload
         * @param {string} type
         *   Element name.
         * @param {JSXProps} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Element}
         *   Element.
         *
         * @param {string | null} type
         *   Element name or `null` to get a root.
         * @param {Properties & {children?: Child}} properties
         *   Properties.
         * @returns {Result}
         *   Result.
         */
        (type: null, properties: {
            children?: Child;
        }, key?: string | null | undefined): Root;
        /**
         * Create a root or an element.
         *
         * @overload
         * @param {null} type
         *   `null` to get a root.
         * @param {{children?: Child}} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Root}
         *   Root.
         *
         * @overload
         * @param {string} type
         *   Element name.
         * @param {JSXProps} properties
         *   Properties with children.
         * @param {string | null | undefined} [key]
         *   Key (ignored).
         * @returns {Element}
         *   Element.
         *
         * @param {string | null} type
         *   Element name or `null` to get a root.
         * @param {Properties & {children?: Child}} properties
         *   Properties.
         * @returns {Result}
         *   Result.
         */
        (type: string, properties: JSXProps, key?: string | null | undefined): Element;
    };
};
export type JSXProps = Record<string, Child | PropertyValue | Style>;
import type { createH as CreateH } from './create-h.js';
import type { Child } from './create-h.js';
import type { Root } from 'hast';
import type { Element } from 'hast';
import type { PropertyValue } from './create-h.js';
import type { Style } from './create-h.js';
//# sourceMappingURL=create-automatic-runtime.d.ts.map
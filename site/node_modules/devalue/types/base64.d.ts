/**	@type {(array_buffer: ArrayBuffer) => string} */
export declare function encode_native(array_buffer: ArrayBuffer): string;
/**	@type {(base64: string) => ArrayBuffer} */
export declare function decode_native(base64: string): ArrayBuffer;
/** @type {(array_buffer: ArrayBuffer) => string} */
export declare function encode_buffer(array_buffer: ArrayBuffer): string;
/**	@type {(base64: string) => ArrayBuffer} */
export declare function decode_buffer(base64: string): ArrayBuffer;
/** @type {(array_buffer: ArrayBuffer) => string} */
export declare function encode_legacy(array_buffer: ArrayBuffer): string;
/**	@type {(base64: string) => ArrayBuffer} */
export declare function decode_legacy(base64: string): ArrayBuffer;
export declare const encode64: typeof encode_native;
export declare const decode64: typeof decode_native;
//# sourceMappingURL=base64.d.ts.map
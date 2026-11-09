# fnv1a-64

[![npm version][npm-version-src]][npm-version-href]
[![npm downloads][npm-downloads-src]][npm-downloads-href]
[![Github Actions][github-actions-src]][github-actions-href]
[![Codecov][codecov-src]][codecov-href]

> Tiny, fast, dependency-free 64-bit [FNV-1a](http://www.isthe.com/chongo/tech/comp/fnv/) string hash for Node and the browser.

The core computes a true 64-bit hash in two 32-bit lanes with plain JS numbers. It's ~320B gzipped (minified) and hashes a short key in ~36ns.

> [!IMPORTANT]
>
> FNV-1a is a fast, **non-cryptographic** hash. It's useful for hash tables, cache keys, checksums, and bucketing, but do not use it for anything security-sensitive: it is not collision-resistant against an adversary and offers no preimage resistance.

## Why

I created this for [Nuxt](https://github.com/nuxt/nuxt) due to particular constraints (fast, small, browser-use, no collisions), but you should consider using one of these other packages if you don't have the same constraints I did:

| Package | Width | Gzip | Notes |
| --- | --- | --- | --- |
| `fnv1a`, `object-code` | 32-bit | tiny | collides at ~50k distinct keys |
| [`fnv1a52`](https://github.com/SukkaW/fnv1a52) | 52-bit | tiny | faster than this package; fits in a JS `number` |
| `@sindresorhus/fnv1a` | 64-bit | ~1KB | BigInt, ~20x slower |
| `fnv-lite` | 128-bit | ~1.4KB | byte arrays, ~40x slower |
| `fnv-plus` | multi | ~9KB | _excellent_ package, but contains lots of utilities |
| `fnv-hash` | 64-bit | native | can't run in the browser |

## Usage

```sh
npm install fnv1a-64
```

```js
import { fnv1a64, fnv1a64Base36, fnv1a64BigInt, fnv1a64Hex } from 'fnv1a-64'

fnv1a64Hex('hello world') // => '779a65e7023cd2e7'  (16-char zero-padded hex)
fnv1a64Base36('hello world') // => '1th7cxzlyc0dj'  (shortest, good for cache keys)
fnv1a64BigInt('hello world') // => 8618312879776256743n
fnv1a64('hello world') // => { high: 2006607335, low: 37540583 }  (fast core, no BigInt)
```

- **`fnv1a64Hex`** and **`fnv1a64Base36`** are what you usually want as a map or cache key.
- **`fnv1a64`** returns the raw 32-bit lanes and is the fastest path if you never need a string.
- **`fnv1a64BigInt`** composes the lanes into a `bigint` when you want a single comparable number.

All outputs are deterministic: the same input always produces the same result. Hex is always exactly 16 characters; base36 length varies with the value but is stable per value.

## Non-ASCII usage

The hash iterates `str.charCodeAt(i)`, so it hashes UTF-16 code units rather than UTF-8 bytes. For **ASCII input this is bit-for-bit identical to a canonical FNV-1a-64**. For non-ASCII (accents, CJK, emoji) the output is stable and collision-resistant but will **not** match an FNV-1a-64 computed over the UTF-8 encoding of the same string.

If you need to interoperate with a hash produced elsewhere over UTF-8 bytes, encode first:

```js
const bytes = new TextEncoder().encode(str)
// then hash the bytes with a UTF-8-aware FNV-1a-64 implementation
```

## Benchmark

Run `pnpm bench` (uses [mitata](https://github.com/evanwashere/mitata)). Indicative numbers on Node 22 (Apple silicon), lower is better:

| | width | short key | 1 KB string |
| --- | --- | --- | --- |
| `fnv1a-64` | 64 | **~25 ns** | ~2.0 µs |
| `fnv1a-64` (hex) | 64 | ~49 ns | ~1.7 µs |
| `fnv1a-64` (base 36) | 64 | ~87 ns | ~1.8 µs |
| `fnv1a52` | 52 | **~24 ns** | ~1.9 µs |
| `fnv1a52` (hex) | 52 | ~43 ns | ~2.0 µs |
| `fnv1a52` (base 36) | 52 | ~64 ns | ~1.7 µs |
| `fnv-plus` `fast1a64` | 64 | ~62 ns | ~1.7 µs |
| `murmurhash` v3 | 32 | ~332 ns | **~1.5 µs** |
| `@sindresorhus/fnv1a` | 64 | ~699 ns | ~28 µs |
| `fnv-lite` `hex` | 128 | ~5.4 µs | ~296 µs |
| `xxhashjs` `h64` | 64 | ~31 µs | ~57 µs |

The `fnv1a-64` core is the fastest 64-bit option on short keys (our main use in Nuxt), and hex formatting costs ~25 ns on top of it.
`fnv1a52` matches it on short keys and needs no `BigInt` or lane pair, at the cost of 12 bits of hash space; pick it if 52 bits is enough for you.
On 1 KB inputs the FNV implementations are all within noise of each other.
`fnv-plus` is competitive but ships ~9 KB gzipped for a whole multi-width toolkit rather than one function. This is less relevant if you're bundling or sharing the dependency.
`murmurhash` is fastest on long inputs but is 32-bit, so it collides.
`fnv-lite` and `xxhashjs` pay a large constant cost for their byte-array / `cuint` internals.

## 💻 Development

- Clone this repository
- Enable [Corepack](https://github.com/nodejs/corepack) using `corepack enable`
- Install dependencies using `pnpm install`
- Run interactive tests using `pnpm dev`

## License

Made with ❤️

Published under [MIT License](./LICENCE).

<!-- Badges -->

[npm-version-src]: https://npmx.dev/api/registry/badge/version/fnv1a-64
[npm-version-href]: https://npmx.dev/package/fnv1a-64
[npm-downloads-src]: https://npmx.dev/api/registry/badge/downloads/fnv1a-64
[npm-downloads-href]: https://npm.chart.dev/fnv1a-64
[github-actions-src]: https://img.shields.io/github/actions/workflow/status/danielroe/fnv1a-64/ci.yml?branch=main&style=flat-square
[github-actions-href]: https://github.com/danielroe/fnv1a-64/actions?query=workflow%3Aci
[codecov-src]: https://img.shields.io/codecov/c/gh/danielroe/fnv1a-64/main?style=flat-square
[codecov-href]: https://codecov.io/gh/danielroe/fnv1a-64

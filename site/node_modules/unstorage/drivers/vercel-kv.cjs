"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});

var _kv = require("@vercel/kv");
var _utils = require("./utils/index.cjs");
const DRIVER_NAME = "vercel-kv";
module.exports = (0, _utils.defineDriver)(opts => {
  const base = (0, _utils.normalizeKey)(opts?.base);
  const r = (...keys) => (0, _utils.joinKeys)(base, ...keys);
  const m = base2 => {
    const prefix = r(base2 || "");
    return prefix ? `${(0, _utils.escapeRedisGlob)(prefix)}:*` : "*";
  };
  let _client;
  const getClient = () => {
    if (!_client) {
      const envPrefix = typeof process !== "undefined" && opts.env !== false ? `${opts.env || "KV"}_` : "";
      if (!opts.url) {
        const envName = envPrefix + "REST_API_URL";
        if (envPrefix && process.env[envName]) {
          opts.url = process.env[envName];
        } else {
          throw (0, _utils.createError)("vercel-kv", `missing required \`url\` option or '${envName}' env.`);
        }
      }
      if (!opts.token) {
        const envName = envPrefix + "REST_API_TOKEN";
        if (envPrefix && process.env[envName]) {
          opts.token = process.env[envName];
        } else {
          throw (0, _utils.createError)("vercel-kv", `missing required \`token\` option or '${envName}' env.`);
        }
      }
      _client = (0, _kv.createClient)(opts);
    }
    return _client;
  };
  const scan = async pattern => {
    const client = getClient();
    const keys = [];
    let cursor = "0";
    do {
      const [nextCursor, scanKeys] = await client.scan(cursor, {
        match: pattern,
        count: opts.scanCount
      });
      cursor = nextCursor;
      keys.push(...scanKeys);
    } while (cursor !== "0");
    return keys;
  };
  return {
    name: DRIVER_NAME,
    getInstance: getClient,
    hasItem(key) {
      return getClient().exists(r(key)).then(Boolean);
    },
    getItem(key) {
      return getClient().get(r(key));
    },
    setItem(key, value, tOptions) {
      const ttl = tOptions?.ttl ?? opts.ttl;
      return getClient().set(r(key), value, ttl ? {
        ex: ttl
      } : void 0).then(() => {});
    },
    removeItem(key) {
      return getClient().unlink(r(key)).then(() => {});
    },
    getKeys(base2) {
      return scan(m(base2));
    },
    async clear(base2) {
      const keys = await scan(m(base2));
      if (keys.length === 0) {
        return;
      }
      return getClient().del(...keys).then(() => {});
    }
  };
});
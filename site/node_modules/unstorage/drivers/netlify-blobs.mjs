import {
  assertURLPathKey,
  createError,
  createRequiredError,
  defineDriver
} from "./utils/index.mjs";
import { getStore, getDeployStore } from "@netlify/blobs";
import { fetch } from "ofetch";
const DRIVER_NAME = "netlify-blobs";
export default defineDriver((options) => {
  const { deployScoped, name, ...opts } = options;
  let store;
  const getClient = () => {
    if (!store) {
      if (deployScoped) {
        if (name) {
          throw createError(
            DRIVER_NAME,
            "deploy-scoped stores cannot have a name"
          );
        }
        store = getDeployStore({ fetch, ...options });
      } else {
        if (!name) {
          throw createRequiredError(DRIVER_NAME, "name");
        }
        store = getStore({ name: encodeURIComponent(name), fetch, ...opts });
      }
    }
    return store;
  };
  const k = (key) => assertURLPathKey(DRIVER_NAME, key);
  return {
    name: DRIVER_NAME,
    options,
    getInstance: getClient,
    async hasItem(key) {
      return getClient().getMetadata(k(key)).then(Boolean);
    },
    getItem: async (key, tops) => {
      return getClient().get(k(key), tops);
    },
    async getMeta(key) {
      return getClient().getMetadata(k(key));
    },
    async getItemRaw(key, topts) {
      return getClient().get(k(key), { type: topts?.type ?? "arrayBuffer" });
    },
    async setItem(key, value, topts) {
      await getClient().set(k(key), value, topts);
    },
    async setItemRaw(key, value, topts) {
      await getClient().set(k(key), value, topts);
    },
    async removeItem(key) {
      return getClient().delete(k(key));
    },
    async getKeys(base, tops) {
      return (await getClient().list({ ...tops, prefix: base })).blobs.map(
        (item) => item.key
      );
    },
    async clear(base) {
      const client = getClient();
      return Promise.allSettled(
        (await client.list({ prefix: base })).blobs.map(
          (item) => client.delete(item.key)
        )
      ).then(() => {
      });
    }
  };
});

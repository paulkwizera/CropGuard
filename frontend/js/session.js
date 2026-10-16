import { api } from "./api.js";
import { cacheMe, cachedMe } from "./auth.js";

/** Current farmer's profile, cached for the tab's lifetime so every page doesn't refetch it. */
export async function getMe({ fresh = false } = {}) {
  if (!fresh) { const c = cachedMe(); if (c) return c; }
  const me = await api.me();
  cacheMe(me);
  return me;
}

export async function updateMe(data) {
  const me = await api.updateMe(data);
  cacheMe(me);
  return me;
}

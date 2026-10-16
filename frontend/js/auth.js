const KEY = "cropguard.tokens";
const ME_KEY = "cropguard.me";

export function getTokens() {
  try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch { return null; }
}
export function saveTokens(tokens) { localStorage.setItem(KEY, JSON.stringify(tokens)); }
export function clearTokens() { localStorage.removeItem(KEY); sessionStorage.removeItem(ME_KEY); }
export function isLoggedIn() { return Boolean(getTokens()?.access); }

export function cachedMe() { try { return JSON.parse(sessionStorage.getItem(ME_KEY)); } catch { return null; } }
export function cacheMe(me) { sessionStorage.setItem(ME_KEY, JSON.stringify(me)); }

export function logout() {
  clearTokens();
  window.location.href = "login.html";
}

/** Call at the top of every page that needs a signed-in farmer. */
export function requireAuth() {
  if (!isLoggedIn()) {
    window.location.replace("login.html");
    return false;
  }
  return true;
}

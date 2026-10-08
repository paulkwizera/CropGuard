const KEY = "cropguard.tokens";

export function getTokens() {
  try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch { return null; }
}
export function saveTokens(tokens) { localStorage.setItem(KEY, JSON.stringify(tokens)); }
export function clearTokens() { localStorage.removeItem(KEY); }
export function isLoggedIn() { return Boolean(getTokens()?.access); }

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

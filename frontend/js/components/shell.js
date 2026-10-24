import { BRAND_MARK, icon, injectSprite } from "./icons.js";
import { cachedMe, isLoggedIn, logout } from "../auth.js";
import { CONFIG } from "../config.js";
import { getMe } from "../session.js";
import { escapeHtml, initial } from "./format.js";
import { confirmDialog } from "./dialog.js";
import { initI18n } from "../i18n.js";
import { mountLangSwitch, promptForLanguage } from "./lang-ui.js";

const brand = (href) => `<a class="brand" href="${href}" aria-label="CropGuard home">${BRAND_MARK}<span>Crop<b>Guard</b></span></a>`;
const demoBadge = () => (CONFIG.USE_MOCK ? `<span class="badge badge--demo" title="Showing sample data without a backend. Add ?mock=0 to the address to use the real backend.">Demo data</span>` : "");

const NAV = [
  { id: "dashboard", href: "dashboard.html", label: "Home", icon: "home" },
  { id: "history", href: "history.html", label: "My checks", icon: "history" },
  { id: "advisory", href: "advisory.html", label: "Weather advice", icon: "cloud" },
  { id: "assistant", href: "assistant.html", label: "Ask the AI", icon: "message" },
  { id: "story", href: "story.html", label: "Our story", icon: "book" },
];

const cur = (active, id) => (active === id ? ' aria-current="page"' : "");

/* ---------- public pages (landing, login, register) ---------- */
export function mountPublicHeader(active = "") {
  injectSprite();
  initI18n();
  const host = document.getElementById("site-header");
  if (!host) return;
  const signedIn = isLoggedIn();
  host.className = "site-header";
  host.innerHTML = `<div class="container">
    ${brand("index.html")}
    <div class="header-tools">
    <span data-lang-switch></span>
    <button class="icon-btn menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Open menu">${icon("menu")}</button>
    <nav class="site-nav" id="site-nav" aria-label="Main">
      <a href="story.html" ${active === "story" ? 'aria-current="page"' : ""}>Our story</a>
      <a href="index.html#how">How it works</a>
      <a href="index.html#features">Features</a>
      ${signedIn
        ? `<a class="btn btn--sm" href="dashboard.html">Open dashboard</a>`
        : `<a href="login.html" ${active === "login" ? 'aria-current="page"' : ""}>Sign in</a><a class="btn btn--sm" href="register.html">Create account</a>`}
    </nav></div></div>`;
  mountLangSwitch(host.querySelector("[data-lang-switch]"));
  promptForLanguage();
  const toggle = host.querySelector(".menu-toggle");
  const nav = host.querySelector(".site-nav");
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    toggle.innerHTML = icon(open ? "x" : "menu");
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && nav.classList.contains("is-open")) toggle.click(); });
}

export function mountPublicFooter() {
  initI18n();
  const host = document.getElementById("site-footer");
  if (!host) return;
  host.className = "site-footer";
  host.innerHTML = `<div class="container">
    ${brand("index.html")}
    <p style="margin:0">Maize and cassava disease detection for Rwandan farmers.</p>
    <nav aria-label="Footer"><a href="login.html">Sign in</a><a href="register.html">Create account</a></nav></div>`;
}

/* ---------- signed-in app shell ---------- */
export function mountShell(active) {
  injectSprite();
  initI18n();
  const me = cachedMe();
  const name = me?.username || "Account";

  const sidebar = `<aside class="sidebar on-dark" aria-label="Sidebar">
    ${brand("dashboard.html")}
    <a class="btn btn--kernel btn--block side-cta" href="detect.html">${icon("camera")}Check a plant</a>
    <nav class="side-nav" aria-label="Main">
      ${NAV.map((n) => `<a href="${n.href}"${cur(active, n.id)}>${icon(n.icon)}${n.label}</a>`).join("")}
    </nav>
    <div class="side-foot">
      <span data-lang-switch></span>
      ${demoBadge()}
      <a class="side-user" href="account.html"${cur(active, "account")}>
        <span class="avatar" data-avatar>${escapeHtml(initial(name))}</span>
        <span><span data-username>${escapeHtml(name)}</span><small>Account &amp; settings</small></span>
      </a>
      <button type="button" class="btn btn--ghost-light btn--sm" data-logout>${icon("logout", "icon--sm")}Sign out</button>
    </div></aside>`;

  const topbar = `<header class="topbar on-dark">${brand("dashboard.html")}<div class="topbar-tools">${demoBadge()}<span data-lang-switch></span><a class="avatar avatar--link" href="account.html" aria-label="Account"${cur(active, "account")} data-avatar>${escapeHtml(initial(name))}</a></div></header>`;

  const tab = (href, id, label, ic) => `<a href="${href}"${cur(active, id)}>${icon(ic)}<span class="tab-label">${label}</span></a>`;
  const tabbar = `<nav class="tabbar" aria-label="Main">
    ${tab("dashboard.html", "dashboard", "Home", "home")}
    ${tab("history.html", "history", "History", "history")}
    <a class="tab-primary" href="detect.html"${cur(active, "detect")}><span class="tab-disc">${icon("camera")}</span><span class="tab-label">Check</span></a>
    ${tab("assistant.html", "assistant", "Ask AI", "message")}
    ${tab("advisory.html", "advisory", "Weather", "cloud")}
  </nav>`;

  const main = document.getElementById("main");
  main.insertAdjacentHTML("beforebegin", sidebar + topbar);
  document.documentElement.setAttribute("data-shell", "1");
  document.body.insertAdjacentHTML("beforeend", tabbar);

  document.querySelectorAll("[data-lang-switch]").forEach(mountLangSwitch);
  promptForLanguage();

  document.querySelector("[data-logout]").addEventListener("click", async () => {
    const ok = await confirmDialog({ title: "Sign out?", message: "You will need to sign in again to see your checks.", confirmLabel: "Sign out" });
    if (ok) logout();
  });

  // fill in the real username once the profile is available
  getMe().then((m) => {
    document.querySelector("[data-username]").textContent = m.username;
    document.querySelectorAll("[data-avatar]").forEach((el) => { el.textContent = initial(m.username); });
  }).catch(() => {});
}

/* ---------- login / register brand block ---------- */
export function mountAuthAside() {
  injectSprite();
  initI18n();
  document.querySelectorAll("[data-lang-switch]").forEach(mountLangSwitch);
  promptForLanguage();
  document.querySelectorAll("[data-brand]").forEach((el) => { el.outerHTML = `${BRAND_MARK}<span>Crop<b>Guard</b></span>`; });
}

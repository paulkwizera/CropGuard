/* CropGuard i18n: English text in the HTML/JS is the source; Kinyarwanda and French are looked up by that text.
   - Static pages: every text node and a few attributes are translated when the page loads.
   - Text added later (rendered by page scripts) is translated by a MutationObserver.
   - Sentences with changing values use t("Showing {a} of {b}", { a, b }).
   To add a language: create js/i18n/<code>.js and register it in DICT and LANGS below. */
import { RW } from "./i18n/rw.js";
import { FR } from "./i18n/fr.js";

export const LANGS = [
  { code: "rw", label: "Kinyarwanda", locale: "rw" },
  { code: "en", label: "English", locale: "en" },
  { code: "fr", label: "Français", locale: "fr" },
];
const DICT = { rw: RW, fr: FR };
const KEY = "cropguard.lang";
const ATTRS = ["placeholder", "aria-label", "title", "alt"];
const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE", "NOSCRIPT"]);
export const missing = new Set(); // English strings with no translation (handy while developing)

export const hasChosenLang = () => LANGS.some((l) => l.code === localStorage.getItem(KEY));
export const currentLang = () => (hasChosenLang() ? localStorage.getItem(KEY) : "en");
export const currentLocale = () => LANGS.find((l) => l.code === currentLang())?.locale || "en";
/** Language to preselect for AI advice: the visitor's choice, or Kinyarwanda before they have chosen. */
export const adviceLang = () => (hasChosenLang() ? currentLang() : "rw");
export function setLang(code) { if (LANGS.some((l) => l.code === code)) localStorage.setItem(KEY, code); }

const norm = (s) => s.replace(/\s+/g, " ").trim();

const known = {}; // translated strings per language, so we never report our own output as "missing"
function lookup(text) {
  const lang = currentLang();
  if (lang === "en") return null;
  const hit = DICT[lang]?.[text];
  if (hit === undefined) {
    known[lang] ??= new Set(Object.values(DICT[lang] || {}));
    if (/[A-Za-z]{3}/.test(text) && !known[lang].has(text)) missing.add(text);
  }
  return hit ?? null;
}

/** Translate one string (for text built in JavaScript). */
export function t(text, vars) {
  let out = lookup(text) ?? text;
  if (vars) out = out.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? ""));
  return out;
}

// ---- DOM translation ---------------------------------------------------
const done = new WeakMap(); // text node -> the translated string we wrote

function translateTextNode(node) {
  const raw = node.data;
  if (done.get(node) === raw) return;
  const key = norm(raw);
  if (!key) return;
  const hit = lookup(key);
  if (hit == null) return;
  const lead = raw.match(/^\s*/)[0], trail = raw.match(/\s*$/)[0];
  const out = lead + hit + trail;
  done.set(node, out);
  node.data = out;
}

function translateAttrs(el) {
  for (const a of ATTRS) {
    const v = el.getAttribute?.(a);
    if (!v) continue;
    const hit = lookup(norm(v));
    if (hit != null) el.setAttribute(a, hit);
  }
}

function translateTree(root) {
  if (root.nodeType === Node.TEXT_NODE) { if (!SKIP.has(root.parentNode?.nodeName)) translateTextNode(root); return; }
  if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
  if (SKIP.has(root.nodeName)) return;
  if (root.nodeType === Node.ELEMENT_NODE) translateAttrs(root);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (SKIP.has(n.nodeName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
  });
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (n.nodeType === Node.TEXT_NODE) translateTextNode(n); else translateAttrs(n);
  }
}

function translateHead() {
  const whole = lookup(norm(document.title));
  if (whole != null) document.title = whole;
  else {
    const [first, ...rest] = document.title.split(" · ");
    const hit = lookup(first);
    if (hit != null) document.title = [hit, ...rest].join(" · ");
  }
  const meta = document.querySelector('meta[name="description"]');
  if (meta) { const m = lookup(norm(meta.content)); if (m != null) meta.content = m; }
}

let started = false;
export function initI18n() {
  const lang = currentLang();
  document.documentElement.lang = lang;
  document.documentElement.setAttribute("data-ready", "1"); // tells the page-level watchdog that scripts started
  if (started) return;
  started = true;
  if (lang !== "en") {
    translateHead();
    translateTree(document.body);
    new MutationObserver((records) => {
      for (const r of records) {
        if (r.type === "characterData") { if (!SKIP.has(r.target.parentNode?.nodeName)) translateTextNode(r.target); }
        else if (r.type === "attributes") translateAttrs(r.target);
        else r.addedNodes.forEach(translateTree);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }
  document.documentElement.classList.remove("i18n-pending");
}

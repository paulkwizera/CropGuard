export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
import { currentLang, currentLocale, t } from "../i18n.js";

export const percent = (x) => `${Math.round(x * 100)}%`;
export const initial = (name) => (name || "?").trim().charAt(0).toUpperCase();

export function formatDate(iso, { withTime = true } = {}) {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = (a, b) => a.toDateString() === b.toDateString();
  const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1);
  const loc = [currentLocale(), "en"];
  const time = d.toLocaleTimeString(loc, { hour: "2-digit", minute: "2-digit" });
  if (sameDay(d, now)) return withTime ? t("Today, {time}", { time }) : t("Today");
  if (sameDay(d, yesterday)) return withTime ? t("Yesterday, {time}", { time }) : t("Yesterday");
  const date = d.toLocaleDateString(loc, { day: "numeric", month: "short", year: d.getFullYear() === now.getFullYear() ? undefined : "numeric" });
  return withTime ? `${date}, ${time}` : date;
}

export function greeting(language = currentLang()) {
  return { rw: "Muraho", en: "Welcome back", fr: "Bonjour" }[language] || "Welcome back";
}

export const LANGUAGES = [
  { code: "rw", label: "Kinyarwanda" },
  { code: "en", label: "English" },
  { code: "fr", label: "Français" },
];

export const DISTRICTS = ["Bugesera","Burera","Gakenke","Gasabo","Gatsibo","Gicumbi","Gisagara","Huye","Kamonyi","Karongi","Kayonza","Kicukiro","Kirehe","Muhanga","Musanze","Ngoma","Ngororero","Nyabihu","Nyagatare","Nyamagabe","Nyamasheke","Nyanza","Nyarugenge","Nyaruguru","Rubavu","Ruhango","Rulindo","Rusizi","Rutsiro","Rwamagana"];

/** Tiny, safe renderer for the plain/markdown-ish text the AI returns. Escapes everything first. */
export function renderAdvice(text) {
  const inline = (s) => escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/(^|[\s(])\*(?!\s)(.+?)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
  const out = [];
  let list = null; // "ul" | "ol"
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const raw of String(text || "").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) { closeList(); continue; }
    let m;
    if ((m = line.match(/^#{1,4}\s+(.*)$/))) { closeList(); out.push(`<h4>${inline(m[1])}</h4>`); }
    else if ((m = line.match(/^[-*•]\s+(.*)$/))) { if (list !== "ul") { closeList(); out.push("<ul>"); list = "ul"; } out.push(`<li>${inline(m[1])}</li>`); }
    else if ((m = line.match(/^\d+[.)]\s+(.*)$/))) { if (list !== "ol") { closeList(); out.push("<ol>"); list = "ol"; } out.push(`<li>${inline(m[1])}</li>`); }
    else { closeList(); out.push(`<p>${inline(line)}</p>`); }
  }
  closeList();
  return out.join("");
}

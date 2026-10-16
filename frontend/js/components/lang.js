import { DISTRICTS, LANGUAGES, escapeHtml } from "./format.js";

/** Build a 3-option segmented radio control (Kinyarwanda / English / Français). */
export function mountLanguage(container, value = "rw", name = "language") {
  container.innerHTML = LANGUAGES.map((l, i) => `
    <label><input type="radio" name="${name}" value="${l.code}" ${l.code === value ? "checked" : ""} ${i === 0 ? "" : ""}><span>${escapeHtml(l.label)}</span></label>`).join("");
}
export const getLanguage = (container) => container.querySelector("input:checked")?.value || "rw";
export const setLanguage = (container, value) => { const r = container.querySelector(`input[value="${value}"]`); if (r) r.checked = true; };

export function fillDistricts(datalist) {
  if (datalist) datalist.innerHTML = DISTRICTS.map((d) => `<option value="${d}"></option>`).join("");
}

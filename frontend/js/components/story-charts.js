// Small, dependency-free chart builders for the story page. Every value is printed as text as well,
// so nothing depends on colour alone. Bars grow when their section scrolls into view (CSS handles the motion).
import { escapeHtml } from "./format.js";
import { t } from "../i18n.js";

const num = (v) => (Number.isInteger(v) ? String(v) : String(Math.round(v * 10) / 10));
export const pctText = (v) => `${num(v)}%`;

/** Horizontal bars: items = [{ label, value (0-100), text?, color? }] */
export function bars(items) {
  return items.map((i) => `<li class="bar-row" style="--v:${i.value};--c:${i.color || "var(--leaf-600)"}">
      <span class="bar-label">${escapeHtml(i.label)}</span>
      <span class="bar-track"><span class="bar-fill"></span></span>
      <span class="bar-val">${escapeHtml(i.text ?? pctText(i.value))}</span></li>`).join("");
}

/** Two bars per row (for example maize and cassava per province). */
export function pairBars(rows, aColor, bColor) {
  return rows.map((r) => `<li class="pair-row">
      <span class="bar-label">${escapeHtml(r.label)}</span>
      <span class="pair-bars">
        <span class="bar-row bar-row--thin" style="--v:${r.a};--c:${aColor}"><span class="bar-track"><span class="bar-fill"></span></span><span class="bar-val">${pctText(r.a)}</span></span>
        <span class="bar-row bar-row--thin" style="--v:${r.b};--c:${bColor}"><span class="bar-track"><span class="bar-fill"></span></span><span class="bar-val">${pctText(r.b)}</span></span>
      </span></li>`).join("");
}

/** A row of stacked bars. rows = [{ label, parts: [{ value, color, name }] }] */
export function stacks(rows) {
  return rows.map((r) => {
    const summary = r.parts.map((p) => `${t(p.name)} ${pctText(p.value)}`).join(", ");
    return `<div class="stack-row">
      <p class="stack-label">${escapeHtml(r.label)}</p>
      <div class="stackbar" role="img" aria-label="${escapeHtml(summary)}">${r.parts.map((p) =>
        `<span class="seg" style="--v:${p.value};--c:${p.color}"${p.value < 6 ? ' data-small="true"' : ""}><b>${p.value >= 6 ? pctText(p.value) : ""}</b></span>`).join("")}</div>
      <p class="stack-values">${r.parts.filter((p) => p.value >= 0.5).map((p) => `<span><i style="--c:${p.color}"></i><span>${escapeHtml(p.name)}</span> <b>${pctText(p.value)}</b></span>`).join("")}</p>
    </div>`;
  }).join("");
}

/** 10 x 10 grid of squares. parts = [{ value (percent), color }] */
export function waffle(parts) {
  // largest-remainder rounding so the squares always add up to exactly 100
  const raw = parts.map((p) => p.value);
  const floors = raw.map(Math.floor);
  let left = 100 - floors.reduce((a, b) => a + b, 0);
  raw.map((v, i) => [v - floors[i], i]).sort((a, b) => b[0] - a[0]).forEach(([, i]) => { if (left-- > 0) floors[i]++; });
  return parts.map((p, i) => Array.from({ length: floors[i] }, () => `<i style="--c:${p.color}"></i>`).join("")).join("");
}

/** Two tall columns for a head-to-head number. items = [{ label, value, text, color }] */
export function compare(items) {
  const max = Math.max(...items.map((i) => i.value));
  return items.map((i) => `<div class="col" style="--v:${(i.value / max) * 100};--c:${i.color}">
      <span class="col-val">${escapeHtml(i.text)}</span><span class="col-bar"><span class="col-fill"></span></span><span class="col-label">${escapeHtml(i.label)}</span></div>`).join("");
}

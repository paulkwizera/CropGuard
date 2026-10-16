import { escapeHtml, formatDate, percent } from "./format.js";
import { t } from "../i18n.js";
import { icon } from "./icons.js";

export const hasIssue = (d) => Boolean(d.top_label);

export function thumb(d, cls = "") {
  return `<div class="thumb ${cls}">${d.image
    ? `<img src="${escapeHtml(d.image)}" alt="" loading="lazy" decoding="async">`
    : icon("leaf", "icon--lg")}</div>`;
}

export function issueBadge(d) {
  return hasIssue(d)
    ? `<span class="badge badge--issue">${icon("alert", "icon--sm")}${escapeHtml(d.top_label)}</span>`
    : `<span class="badge badge--warn">${icon("info", "icon--sm")}No disease found</span>`;
}

export const confidenceText = (d) => (hasIssue(d) ? t("{pct} confidence", { pct: percent(d.top_confidence) }) : t("Try a clearer photo if unsure"));
export const dateText = (d) => formatDate(d.created_at);

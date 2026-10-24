import { escapeHtml, formatDate, percent } from "./format.js";
import { t } from "../i18n.js";
import { icon } from "./icons.js";

export const cropName = (d) => ({ maize: "Maize", cassava: "Cassava" }[d.crop] || "Maize");
/** "disease" | "healthy" | "none". Older records have no status: a label means a disease was found. */
export const statusOf = (d) => (d.status === "disease" || d.status === "healthy" ? d.status : d.top_label ? "disease" : "none");
export const hasIssue = (d) => statusOf(d) === "disease";
export const isHealthy = (d) => statusOf(d) === "healthy";

export function thumb(d, cls = "") {
  return `<div class="thumb ${cls}">${d.image
    ? `<img src="${escapeHtml(d.image)}" alt="" loading="lazy" decoding="async">`
    : icon("leaf", "icon--lg")}</div>`;
}

export function issueBadge(d) {
  if (hasIssue(d)) return `<span class="badge badge--issue">${icon("alert", "icon--sm")}${escapeHtml(d.top_label)}</span>`;
  if (isHealthy(d)) return `<span class="badge badge--ok">${icon("check-circle", "icon--sm")}Healthy leaf</span>`;
  return `<span class="badge badge--warn">${icon("info", "icon--sm")}No disease found</span>`;
}

export const confidenceText = (d) => (hasIssue(d) || isHealthy(d) ? t("{pct} confidence", { pct: percent(d.top_confidence) }) : t("Try a clearer photo if unsure"));
export const dateText = (d) => formatDate(d.created_at);

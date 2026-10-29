import { escapeHtml, formatDate, percent } from "./format.js";
import { t } from "../i18n.js";
import { icon } from "./icons.js";

export const cropName = (d) => ({ maize: "Maize", cassava: "Cassava", other: "Other plant" }[d.crop] || "Maize");
/** "disease" | "healthy" | "none" | "other" (Gemini says it is not a maize/cassava leaf). Older records have no status: a label means a disease was found. */
export const statusOf = (d) => (["disease", "healthy", "other"].includes(d.status) ? d.status : d.status === "none" ? "none" : d.top_label ? "disease" : "none");
export const hasIssue = (d) => statusOf(d) === "disease";
export const isHealthy = (d) => statusOf(d) === "healthy";
export const isOther = (d) => statusOf(d) === "other";

export function thumb(d, cls = "") {
  return `<div class="thumb ${cls}">${d.image
    ? `<img src="${escapeHtml(d.image)}" alt="" loading="lazy" decoding="async" onerror="this.remove()">`
    : icon("leaf", "icon--lg")}</div>`;
}

export function issueBadge(d) {
  if (hasIssue(d)) return `<span class="badge badge--issue">${icon("alert", "icon--sm")}${escapeHtml(d.top_label)}</span>`;
  if (isHealthy(d)) return `<span class="badge badge--ok">${icon("check-circle", "icon--sm")}Healthy leaf</span>`;
  if (isOther(d)) return `<span class="badge badge--warn">${icon("info", "icon--sm")}${escapeHtml(d.top_label || "Not a maize or cassava leaf")}</span>`;
  return `<span class="badge badge--warn">${icon("info", "icon--sm")}No disease found</span>`;
}

export const confidenceText = (d) => (hasIssue(d) || isHealthy(d)
  ? (d.top_confidence == null ? t("Gemini is highly certain") : t("{pct} confidence", { pct: percent(d.top_confidence) }))
  : isOther(d) ? t("Only maize and cassava are checked") : t("Try a clearer photo if unsure"));
/** The confidence number and bar shown under a result's title (both result pages use this). */
export const confidenceBlock = (d) => d.top_confidence == null
  ? `<p class="conf-line"><strong>Gemini is highly certain</strong></p>`
  : `<p class="conf-line"><strong>${percent(d.top_confidence)}</strong> <span class="muted">confidence</span></p>
        <div class="meter" role="img" aria-label="${escapeHtml(t("Confidence {pct}", { pct: percent(d.top_confidence) }))}"><span style="width:${percent(d.top_confidence)}"></span></div>`;
export const dateText = (d) => formatDate(d.created_at);

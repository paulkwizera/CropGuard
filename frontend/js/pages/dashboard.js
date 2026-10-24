import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { mountShell } from "../components/shell.js";
import { confidenceText, dateText, hasIssue, issueBadge, thumb } from "../components/checks.js";
import { escapeHtml, formatDate, greeting } from "../components/format.js";
import { icon } from "../components/icons.js";
import { getMe } from "../session.js";
import { t } from "../i18n.js";

if (requireAuth()) init();

async function init() {
  mountShell("dashboard");
  const $ = (id) => document.getElementById(id);
  const me = await getMe().catch(() => ({ username: "", preferred_language: "en" }));
  $("greeting").textContent = me.username ? `${greeting()}, ${me.username}` : t("Welcome back");

  let data;
  try {
    data = await api.listDetections(1);
  } catch (err) {
    $("stats").innerHTML = "";
    $("recent").innerHTML = `<div class="alert alert--error" role="alert">${icon("alert")}<p>${escapeHtml(err.message)} <button class="btn btn--sm btn--secondary" type="button" onclick="location.reload()">Try again</button></p></div>`;
    loadWeather(me);
    return;
  }
  const { count, results } = data;
  const issues = results.filter(hasIssue);
  const partial = count > results.length;

  // --- summary strip (all numbers come from real saved checks)
  const tally = {};
  for (const d of issues) tally[d.top_label] = (tally[d.top_label] || 0) + 1;
  const ranked = Object.entries(tally).sort((a, b) => b[1] - a[1]);
  const stat = (label, value, note = "") => `<div class="stat"><dt>${label}</dt><dd>${value}${note ? `<small>${note}</small>` : ""}</dd></div>`;
  $("stats").innerHTML =
    stat("Total checks", count) +
    stat("Problems found", issues.length, partial ? t("in your latest {n}", { n: results.length }) : count ? t("of {n} checks", { n: count }) : "") +
    stat("Most common", ranked[0] ? escapeHtml(ranked[0][0]) : "None yet", ranked[0] ? t(ranked[0][1] === 1 ? "{n} time" : "{n} times", { n: ranked[0][1] }) : "") +
    stat("Last check", results[0] ? formatDate(results[0].created_at, { withTime: false }) : "None yet");
  $("greeting-sub").textContent = count ? "Here is how your checks are going." : "Start with a photo of one leaf.";

  // --- recent checks
  if (!count) {
    $("recent").innerHTML = `<div class="empty"><img class="empty-art" src="assets/images/seedling.svg" alt="" width="200" height="150"><h2>No checks yet</h2><p>Photograph a leaf and your first result will appear here.</p><a class="btn" href="detect.html">${icon("camera")}Check your first plant</a></div>`;
  } else {
    $("recent").innerHTML = `<ul class="check-list">${results.slice(0, 5).map((d) => `
      <li><a class="check-row" href="history.html?open=${encodeURIComponent(d.id)}">
        ${thumb(d, "thumb--row")}
        <span class="check-row-main">${issueBadge(d)}<span class="faint">${escapeHtml(confidenceText(d))}</span></span>
        <span class="check-row-date">${escapeHtml(dateText(d))}</span>
        ${icon("chevron", "icon--sm")}
      </a></li>`).join("")}</ul>`;
    $("all-link").hidden = count <= 5;
  }

  // --- what you found
  if (ranked.length) {
    const max = ranked[0][1];
    $("mix-section").hidden = false;
    $("mix").innerHTML = `<ul class="mix">${ranked.slice(0, 5).map(([label, n]) => `
      <li><span class="mix-label">${escapeHtml(label)}</span><span class="mix-n">${n}</span>
      <span class="meter meter--thin meter--issue" aria-hidden="true"><span style="width:${(n / max) * 100}%"></span></span></li>`).join("")}</ul>
      ${partial ? `<p class="faint" style="margin:.75rem 0 0;font-size:var(--fs-xs)">${t("Based on your latest {n} checks.", { n: results.length })}</p>` : ""}`;
  }

  // --- getting started (only while something is still to do)
  const steps = [
    { done: true, text: "Create your account" },
    { done: Boolean(me.district), text: "Add your district for weather advice", href: "account.html" },
    { done: count > 0, text: "Check your first plant", href: "detect.html" },
  ];
  if (steps.some((s) => !s.done)) {
    $("start-section").hidden = false;
    $("start").innerHTML = steps.map((s) => `<li class="${s.done ? "is-done" : ""}">
      <span class="check-dot" aria-hidden="true">${s.done ? icon("check", "icon--sm") : ""}</span>
      ${s.done || !s.href ? `<span>${s.text}</span><span class="visually-hidden">(done)</span>` : `<a href="${s.href}">${s.text}</a>`}</li>`).join("");
  }

  loadWeather(me);
}

async function loadWeather(me) {
  const box = document.getElementById("wx");
  if (!me.district) {
    box.innerHTML = `<p class="muted" style="margin:0 0 .75rem">Add your district to see today's weather.</p><a class="btn btn--sm btn--secondary" href="account.html">Add district</a>`;
    return;
  }
  const key = `cropguard.wx.${me.district}`;
  try {
    let cached = null;
    try { cached = JSON.parse(sessionStorage.getItem(key)); } catch { /* ignore */ }
    let wx = cached && Date.now() - cached.at < 30 * 60 * 1000 ? cached.data : null;
    if (!wx) { wx = await api.weather(me.district); sessionStorage.setItem(key, JSON.stringify({ at: Date.now(), data: wx })); }
    box.innerHTML = `<p class="faint" style="margin:0 0 .5rem;font-size:var(--fs-xs)">${escapeHtml(t("Next 24 hours in {city}", { city: wx.city }))}</p>
      <div class="wx-figures">
        <div>${icon("thermo")}<strong>${wx.avg_temp_c}°C</strong><span class="faint">average</span></div>
        <div>${icon("droplet")}<strong>${wx.total_rain_mm} mm</strong><span class="faint">rain expected</span></div>
      </div>`;
  } catch {
    box.innerHTML = `<p class="muted" style="margin:0">Weather is not available right now.</p>`;
  }
}

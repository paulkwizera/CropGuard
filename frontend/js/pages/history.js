import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { mountShell } from "../components/shell.js";
import { confidenceText, dateText, hasIssue, issueBadge, thumb } from "../components/checks.js";
import { confirmDialog, enableBackdropClose } from "../components/dialog.js";
import { escapeHtml, formatDate, LANGUAGES, percent, renderAdvice } from "../components/format.js";
import { drawDetection } from "../components/image.js";
import { icon } from "../components/icons.js";
import { setBusy } from "../components/forms.js";
import { toast } from "../components/toast.js";
import { getMe } from "../session.js";
import { adviceLang, t } from "../i18n.js";

if (requireAuth()) init();

async function init() {
  mountShell("history");
  const $ = (id) => document.getElementById(id);
  const state = { items: [], total: 0, page: 1, next: null, filter: "", sort: "new", lang: adviceLang(), opener: null };


  // ---------- list ----------
  function skeletons() {
    $("grid").innerHTML = Array.from({ length: 6 }, () => `<div class="check-card check-card--skeleton"><div class="skeleton" style="aspect-ratio:4/3"></div><div class="skeleton" style="height:1.2rem;margin-top:.75rem;width:70%"></div></div>`).join("");
  }

  async function load(page = 1) {
    if (page === 1) skeletons();
    $("grid").setAttribute("aria-busy", "true");
    try {
      const data = await api.listDetections(page);
      state.total = data.count;
      state.next = data.next;
      state.page = page;
      state.items = page === 1 ? data.results : [...state.items, ...data.results];
      buildFilter();
      render();
    } catch (err) {
      $("grid").innerHTML = `<div class="alert alert--error" role="alert" style="grid-column:1/-1">${icon("alert")}<p>${escapeHtml(err.message)} <button class="btn btn--sm btn--secondary" id="retry" type="button">Try again</button></p></div>`;
      $("retry")?.addEventListener("click", () => load(page));
    } finally {
      $("grid").setAttribute("aria-busy", "false");
    }
  }

  function buildFilter() {
    const labels = [...new Set(state.items.filter(hasIssue).map((d) => d.top_label))].sort();
    const hasNone = state.items.some((d) => !hasIssue(d));
    $("filter").innerHTML = `<option value="">All results</option>` +
      labels.map((l) => `<option value="${escapeHtml(l)}">${escapeHtml(l)}</option>`).join("") +
      (hasNone ? `<option value="__none__">No disease found</option>` : "");
    $("filter").value = [...$("filter").options].some((o) => o.value === state.filter) ? state.filter : "";
    state.filter = $("filter").value;
  }

  function visible() {
    let list = state.items.filter((d) => !state.filter || (state.filter === "__none__" ? !hasIssue(d) : d.top_label === state.filter));
    const by = {
      new: (a, b) => new Date(b.created_at) - new Date(a.created_at),
      old: (a, b) => new Date(a.created_at) - new Date(b.created_at),
      conf: (a, b) => (b.top_confidence ?? -1) - (a.top_confidence ?? -1),
    }[state.sort];
    return list.sort(by);
  }

  function render() {
    const list = visible();
    const none = state.total === 0;
    $("empty").hidden = !none;
    $("toolbar").hidden = none;
    $("no-match").hidden = none || list.length > 0;
    $("history-sub").textContent = none ? t("Your saved results will appear here.") : t(state.total === 1 ? "{n} check saved, newest first." : "{n} checks saved, newest first.", { n: state.total });
    $("count").textContent = none ? "" : t(state.next ? "Showing {shown} of {total}+" : "Showing {shown} of {total}", { shown: list.length, total: state.items.length });
    $("load-more").hidden = !state.next;
    $("grid").innerHTML = list.map((d) => `
      <button class="check-card" type="button" data-id="${escapeHtml(d.id)}">
        ${thumb(d)}
        <span class="check-card-body">${issueBadge(d)}<span class="check-card-conf">${escapeHtml(confidenceText(d))}</span><span class="faint check-card-date">${escapeHtml(dateText(d))}</span></span>
      </button>`).join("");
  }

  $("filter").addEventListener("change", (e) => { state.filter = e.target.value; render(); });
  $("sort").addEventListener("change", (e) => { state.sort = e.target.value; render(); });
  $("clear-filter").addEventListener("click", () => { state.filter = ""; $("filter").value = ""; render(); });
  $("load-more").addEventListener("click", async (e) => { setBusy(e.currentTarget, true); await load(state.page + 1); setBusy(e.currentTarget, false); });

  // ---------- detail dialog ----------
  const dialog = $("detail");
  enableBackdropClose(dialog);
  dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => { state.opener?.focus?.(); state.opener = null; history.replaceState(null, "", "history.html"); });

  $("grid").addEventListener("click", (e) => {
    const card = e.target.closest(".check-card[data-id]");
    if (!card) return;
    state.opener = card;
    openDetail(state.items.find((d) => d.id === card.dataset.id));
  });

  function openDetail(d) {
    if (!d) return;
    const body = $("detail-body");
    body.innerHTML = `
      <div class="detail">
        <figure class="result-media frame"><canvas id="detail-canvas" role="img" aria-label="Photo with detected area framed"></canvas></figure>
        <div class="detail-info stack">
          <div>${issueBadge(d)}<h3 class="result-title" style="margin-top:.5rem">${escapeHtml(d.top_label || "No disease found")}</h3>
            <p class="faint" style="margin:0">${escapeHtml(formatDate(d.created_at))}</p></div>
          ${hasIssue(d) ? `<div><p class="conf-line"><strong>${percent(d.top_confidence)}</strong> <span class="muted">confidence</span></p>
            <div class="meter" role="img" aria-label="${escapeHtml(t("Confidence {pct}", { pct: percent(d.top_confidence) }))}"><span style="width:${percent(d.top_confidence)}"></span></div></div>` : `<p class="muted">The model did not find a problem it was confident about.</p>`}
          ${hasIssue(d) ? `<div class="advice">
            <h3>Treatment advice</h3>
            <div id="d-advice" class="prose-ai advice-out" ${d.advice ? "" : "hidden"}>${d.advice ? renderAdvice(d.advice) : ""}</div>
            <div class="advice-controls">
              <div class="field"><label for="d-lang">Language</label><select class="select" id="d-lang">${LANGUAGES.map((l) => `<option value="${l.code}" ${l.code === state.lang ? "selected" : ""}>${l.label}</option>`).join("")}</select></div>
              <button class="btn" id="d-advice-btn" type="button">${icon("sparkle")}<span>${d.advice ? "Get advice again" : "Get advice"}</span></button>
            </div></div>` : ""}
        </div>
      </div>
      <div class="modal-foot detail-foot"><button class="btn btn--danger-ghost" id="d-delete" type="button">${icon("trash")}Delete this check</button><button class="btn btn--secondary" type="button" data-close-btn>Close</button></div>`;
    body.querySelector("[data-close-btn]").addEventListener("click", () => dialog.close());
    if (!dialog.open) dialog.showModal();
    drawDetection($("detail-canvas"), d.image, d);

    $("d-advice-btn")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      setBusy(btn, true);
      try {
        const updated = await api.detectionAdvice(d.id, $("d-lang").value);
        Object.assign(d, updated);
        $("d-advice").innerHTML = renderAdvice(updated.advice);
        $("d-advice").hidden = false;
        btn.querySelector("span").textContent = "Get advice again";
      } catch (err) { toast(err.message, "error"); }
      finally { setBusy(btn, false); }
    });

    $("d-delete").addEventListener("click", async () => {
      const ok = await confirmDialog({ title: "Delete this check?", message: "The photo and its result will be removed from your history. This cannot be undone.", confirmLabel: "Delete", danger: true });
      if (!ok) return;
      try {
        await api.deleteDetection(d.id);
        state.items = state.items.filter((x) => x.id !== d.id);
        state.total = Math.max(0, state.total - 1);
        state.opener = null;
        dialog.close();
        buildFilter(); render();
        toast("Check deleted.");
      } catch (err) { toast(err.message, "error"); }
    });
  }

  await load(1);

  // deep link from the dashboard: history.html?open=<id>
  const openId = new URLSearchParams(location.search).get("open");
  if (openId) {
    let d = state.items.find((x) => x.id === openId);
    if (!d) { try { d = await api.getDetection(openId); } catch { /* not found */ } }
    if (d) openDetail(d);
  }
}

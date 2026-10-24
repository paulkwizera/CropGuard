import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { mountShell } from "../components/shell.js";
import { drawDetection, prepareImage } from "../components/image.js";
import { escapeHtml, percent, renderAdvice, LANGUAGES } from "../components/format.js";
import { icon } from "../components/icons.js";
import { toast } from "../components/toast.js";
import { setBusy } from "../components/forms.js";
import { cropName, isHealthy } from "../components/checks.js";
import { adviceLang, t } from "../i18n.js";

if (requireAuth()) init();

function init() {
  mountShell("detect");
  const $ = (id) => document.getElementById(id);
  const MAX_MB = 8;
  const stages = ["photo", "ready", "busy", "error", "result"];
  const order = ["photo", "diagnosis", "advice"];
  let file = null;      // the (possibly shrunk) image we will upload
  let preview = null;   // object URL for the preview
  let current = null;   // detection returned by the API
  let adviceText = "";
  let crop = "maize";   // which detector to use

  $("advice-lang").innerHTML = LANGUAGES.map((l) => `<option value="${l.code}">${l.label}</option>`).join("");
  $("advice-lang").value = adviceLang();

  // ---- which crop? (cassava stays "coming soon" until its model file exists on the server)
  const FALLBACK_CROPS = [{ id: "maize", name: "Maize", available: true }];
  api.crops().catch(() => FALLBACK_CROPS).then((list) => {
    $("crop-seg").innerHTML = list.map((c) => `<label><input type="radio" name="crop" value="${c.id}" ${c.available ? "" : "disabled"} ${c.id === crop ? "checked" : ""}><span>${escapeHtml(c.name)}${c.available ? "" : ` <em class="soon">Coming soon</em>`}</span></label>`).join("");
    $("crop-note").hidden = list.every((c) => c.available);
  });
  $("crop-seg").addEventListener("change", (e) => { crop = e.target.value; });

  function show(stage, step = "photo") {
    stages.forEach((s) => ($(`stage-${s}`).hidden = s !== stage));
    document.querySelectorAll("#stepper li").forEach((li) => {
      li.classList.toggle("is-done", order.indexOf(li.dataset.step) < order.indexOf(step));
      if (li.dataset.step === step) li.setAttribute("aria-current", "step");
      else li.removeAttribute("aria-current");
    });
  }
  const photoError = (msg) => { const el = $("photo-error"); el.hidden = !msg; el.querySelector("[data-text]").textContent = msg || ""; };

  async function choose(f) {
    photoError("");
    if (!f) return;
    if (!f.type.startsWith("image/")) return photoError("That file is not an image. Choose a JPG or PNG photo.");
    if (f.size > 40 * 1024 * 1024) return photoError("That photo is very large. Choose one under 40 MB.");
    try {
      file = await prepareImage(f);
    } catch (err) { return photoError(err.message); }
    if (file.size > MAX_MB * 1024 * 1024) return photoError(t("That photo is still larger than {n} MB after shrinking. Try a smaller one.", { n: MAX_MB }));
    if (preview) URL.revokeObjectURL(preview);
    preview = URL.createObjectURL(file);
    $("preview-img").src = preview;
    $("file-meta").textContent = t(file.size < f.size ? "{name} ({size} MB, shrunk to save data)" : "{name} ({size} MB)", { name: f.name, size: (file.size / 1024 / 1024).toFixed(1) });
    show("ready");
    $("analyze-btn").focus();
  }

  // --- choosing a photo
  $("camera-btn").addEventListener("click", () => $("camera-input").click());
  $("gallery-btn").addEventListener("click", () => $("file-input").click());
  for (const id of ["camera-input", "file-input"]) $(id).addEventListener("change", (e) => { choose(e.target.files[0]); e.target.value = ""; });
  const zone = $("dropzone");
  ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("is-over"); }));
  ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("is-over"); }));
  zone.addEventListener("drop", (e) => choose(e.dataTransfer.files[0]));

  const reset = () => { file = null; current = null; adviceText = ""; photoError(""); show("photo"); $("camera-btn").focus(); };
  ["reset-btn", "error-reset", "again-btn"].forEach((id) => $(id).addEventListener("click", reset));

  // --- analysing
  async function analyze() {
    $("busy-img").src = preview;
    const bar = $("progress");
    bar.classList.remove("is-indeterminate");
    bar.firstElementChild.style.width = "0%";
    $("busy-title").textContent = "Uploading photo…";
    show("busy");
    try {
      current = await api.createDetection(file, (p) => {
        bar.firstElementChild.style.width = `${Math.round(p * 100)}%`;
        if (p >= 1) { $("busy-title").textContent = "Checking the leaf…"; bar.classList.add("is-indeterminate"); }
      }, crop);
      await renderResult(current);
    } catch (err) {
      $("error-text").textContent = err.message;
      show("error");
      $("retry-btn").focus();
    }
  }
  $("analyze-btn").addEventListener("click", analyze);
  $("retry-btn").addEventListener("click", analyze);

  // --- result
  async function renderResult(d) {
    show("result", "diagnosis");
    const drawn = await drawDetection($("result-canvas"), d.image, d);
    if (!drawn) $("result-canvas").replaceWith(Object.assign(document.createElement("img"), { src: preview, alt: "Your photo" }));
    const summary = $("result-summary");
    $("advice-out").hidden = true; $("copy-advice").hidden = true; adviceText = "";

    if (isHealthy(d)) {
      summary.innerHTML = `<span class="badge badge--ok">${icon("check-circle", "icon--sm")}Looks healthy</span> <span class="badge">${escapeHtml(cropName(d))}</span>
        <h2 class="result-title">${escapeHtml(d.top_label)}</h2>
        <p class="conf-line"><strong>${percent(d.top_confidence)}</strong> <span class="muted">confidence</span></p>
        <div class="meter" role="img" aria-label="${escapeHtml(t("Confidence {pct}", { pct: percent(d.top_confidence) }))}"><span style="width:${percent(d.top_confidence)}"></span></div>
        <p class="muted" style="margin-top:1rem">No disease was detected on this leaf. Check a few more leaves from different parts of the field to be sure.</p>`;
      $("advice-section").hidden = true;
      return;
    }
    if (!d.top_label) {
      summary.innerHTML = `<span class="badge badge--warn">${icon("info", "icon--sm")}Nothing detected</span>
        <h2 class="result-title">No disease found</h2>
        <p class="muted">The model did not find a problem it was confident about. That does not guarantee the plant is healthy. Try a closer, sharper photo of one leaf in daylight, or check a different leaf.</p>`;
      $("advice-section").hidden = true;
      return;
    }
    const others = (d.results || []).slice(1, 4);
    summary.innerHTML = `<span class="badge badge--issue">${icon("alert", "icon--sm")}Problem detected</span> <span class="badge">${escapeHtml(cropName(d))}</span>
      <h2 class="result-title">${escapeHtml(d.top_label)}</h2>
      <p class="conf-line"><strong>${percent(d.top_confidence)}</strong> <span class="muted">confidence</span></p>
      <div class="meter" role="img" aria-label="${escapeHtml(t("Confidence {pct}", { pct: percent(d.top_confidence) }))}"><span style="width:${percent(d.top_confidence)}"></span></div>
      ${others.length ? `<p class="muted" style="margin:1rem 0 .25rem;font-size:var(--fs-sm)">Also considered</p><ul class="also">${others.map((r) => `<li><span>${escapeHtml(r.label)}</span><span class="faint">${percent(r.confidence)}</span></li>`).join("")}</ul>` : ""}
      <p class="disclaimer">${icon("info", "icon--sm")}<span>This is a computer estimate from one photo. For a severe outbreak, confirm with your local agronomist.</span></p>`;
    $("advice-section").hidden = false;
    if (d.advice) showAdvice(d.advice);
  }

  function showAdvice(text) {
    adviceText = text;
    $("advice-out").innerHTML = renderAdvice(text);
    $("advice-out").hidden = false;
    $("copy-advice").hidden = false;
    $("advice-btn").querySelector("span").textContent = "Get advice again";
    show("result", "advice");
  }

  $("advice-btn").addEventListener("click", async () => {
    const btn = $("advice-btn");
    setBusy(btn, true);
    try {
      const updated = await api.detectionAdvice(current.id, $("advice-lang").value);
      current = updated;
      showAdvice(updated.advice);
      $("advice-out").scrollIntoView({ block: "nearest", behavior: "smooth" });
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(btn, false);
    }
  });

  $("copy-advice").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(adviceText); toast("Advice copied."); }
    catch { toast("Could not copy. Select the text and copy it instead.", "error"); }
  });
}

import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { mountShell } from "../components/shell.js";
import { drawDetection, prepareImage } from "../components/image.js";
import { escapeHtml, percent, renderAdvice, LANGUAGES } from "../components/format.js";
import { icon } from "../components/icons.js";
import { toast } from "../components/toast.js";
import { setBusy } from "../components/forms.js";
import { confidenceBlock, cropName, isHealthy, isOther } from "../components/checks.js";
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
  let crop = "auto";    // which detector to use: "auto" (the server tells maize from cassava) or a crop id
  let requested = crop; // what was asked for on the last check (so the result can say "recognised as ...")

  $("advice-lang").innerHTML = LANGUAGES.map((l) => `<option value="${l.code}">${l.label}</option>`).join("");
  $("advice-lang").value = adviceLang();

  // ---- which crop? Each detector only knows its own crop, so a leaf sent to the wrong one still gets
  // an (wrong) answer. "Auto-detect" is therefore the default whenever two or more detectors are ready:
  // the server asks all of them and trusts the one that is most sure. A crop whose model file is missing
  // on the server stays "coming soon".
  const AUTO = { id: "auto", name: "Auto-detect", available: true };
  // If the crop list cannot be loaded, still offer every crop (the server explains if one is not ready).
  const FALLBACK_CROPS = [{ id: "maize", name: "Maize", available: true }, { id: "cassava", name: "Cassava", available: true }];
  const syncCropHint = () => { $("crop-auto-hint").hidden = crop !== "auto"; };
  api.crops().catch(() => FALLBACK_CROPS).then((list) => {
    const ready = list.filter((c) => c.available);
    crop = ready.length > 1 ? "auto" : (ready[0]?.id ?? "maize");
    const options = ready.length > 1 ? [AUTO, ...list] : list;
    $("crop-seg").innerHTML = options.map((c) => `<label><input type="radio" name="crop" value="${c.id}" ${c.available ? "" : "disabled"} ${c.id === crop ? "checked" : ""}><span>${escapeHtml(c.name)}${c.available ? "" : ` <em class="soon">Coming soon</em>`}</span></label>`).join("");
    $("crop-note").hidden = list.every((c) => c.available);
    syncCropHint();
  });
  $("crop-seg").addEventListener("change", (e) => { crop = e.target.value; syncCropHint(); });

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

  const reset = () => { file = null; current = null; adviceText = ""; $("verify-box").hidden = true; photoError(""); show("photo"); $("camera-btn").focus(); };
  ["reset-btn", "error-reset", "again-btn"].forEach((id) => $(id).addEventListener("click", reset));

  // --- analysing
  async function analyze() {
    $("busy-img").src = preview;
    const bar = $("progress");
    bar.classList.remove("is-indeterminate");
    bar.firstElementChild.style.width = "0%";
    $("busy-title").textContent = "Uploading photo…";
    show("busy");
    requested = crop;
    try {
      current = await api.createDetection(file, (p) => {
        bar.firstElementChild.style.width = `${Math.round(p * 100)}%`;
        if (p >= 1) { $("busy-title").textContent = "Checking the leaf…"; bar.classList.add("is-indeterminate"); }
      }, crop);
      // Gemini double-checks the photo and the server picks ONE final answer (see services/decision.py). We wait for it
      // so the result never flips from one answer to another on screen. If Gemini is unavailable, the detector's own
      // answer is shown on its own.
      $("busy-title").textContent = "Double-checking with Gemini…";
      try { current = await api.verifyDetection(current.id, $("advice-lang").value); } catch { /* keep the detector's answer */ }
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
    renderVerification(d);
    const drawn = await drawDetection($("result-canvas"), d.image, d);
    if (!drawn) $("result-canvas").replaceWith(Object.assign(document.createElement("img"), { src: preview, alt: "Your photo" }));
    const summary = $("result-summary");
    $("advice-out").hidden = true; $("copy-advice").hidden = true; adviceText = "";

    if (isOther(d)) {   // Gemini says this is not a maize or cassava leaf: no disease verdict is given at all
      const v = d.verification || {};
      const first = d.verification?.resolution?.basis === "not_a_leaf"
        ? "Gemini cannot see a plant leaf in this photo."
        : v.plant_name ? t("Gemini thinks this is a {plant} leaf.", { plant: escapeHtml(v.plant_name) }) : "Gemini does not think this is a maize or cassava leaf.";
      summary.innerHTML = `<span class="badge badge--warn">${icon("info", "icon--sm")}Not checked</span>
        <h2 class="result-title">${escapeHtml(d.top_label)}</h2>
        <p class="muted">${first} CropGuard only checks maize and cassava, so it gives no disease result for this photo.</p>
        ${v.explanation ? `<p class="muted" style="font-size:var(--fs-sm)">${escapeHtml(v.explanation)}</p>` : ""}
        <p class="disclaimer">${icon("info", "icon--sm")}<span>Take a clear, close photo of one maize or cassava leaf in daylight and check again.</span></p>`;
      $("advice-section").hidden = true;
      return;
    }
    if (isHealthy(d)) {
      summary.innerHTML = `<span class="badge badge--ok">${icon("check-circle", "icon--sm")}Looks healthy</span> <span class="badge">${escapeHtml(cropName(d))}</span>
        <h2 class="result-title">${escapeHtml(d.top_label)}</h2>
        ${confidenceBlock(d)}
        <p class="muted" style="margin-top:1rem">No disease was detected on this leaf. Check a few more leaves from different parts of the field to be sure.</p>${recognisedLine(d)}`;
      $("advice-section").hidden = true;
      return;
    }
    if (!d.top_label) {
      summary.innerHTML = `<span class="badge badge--warn">${icon("info", "icon--sm")}Nothing detected</span>
        <h2 class="result-title">No disease found</h2>
        <p class="muted">${requested === "auto"
          ? "CropGuard could not recognise a maize or cassava leaf with confidence in this photo. Try a closer, sharper photo of one leaf in daylight, or choose the crop yourself and check again."
          : "The model did not find a problem it was confident about. That does not guarantee the plant is healthy. Try a closer, sharper photo of one leaf in daylight, or check a different leaf."}</p>`;
      $("advice-section").hidden = true;
      return;
    }
    const others = (d.results || []).slice(1, 4);
    summary.innerHTML = `<span class="badge badge--issue">${icon("alert", "icon--sm")}Problem detected</span> <span class="badge">${escapeHtml(cropName(d))}</span>
      <h2 class="result-title">${escapeHtml(d.top_label)}</h2>
      ${confidenceBlock(d)}
      ${others.length ? `<p class="muted" style="margin:1rem 0 .25rem;font-size:var(--fs-sm)">Also considered</p><ul class="also">${others.map((r) => `<li><span>${escapeHtml(r.label)}</span><span class="faint">${percent(r.confidence)}</span></li>`).join("")}</ul>` : ""}
      ${recognisedLine(d)}
      <p class="disclaimer">${icon("info", "icon--sm")}<span>This is a computer estimate from one photo. For a severe outbreak, confirm with your local agronomist.</span></p>`;
    $("advice-section").hidden = false;
    if (d.advice) showAdvice(d.advice);
  }

  // ---- how the final answer was chosen. The detector and Gemini each looked at the photo; the server picked one
  // (resolution.winner) and already stored it as the result above. This card says who decided, and why.
  const BASIS = {
    confirmed:             { badge: "badge--ok",   icon: "check-circle", title: "Confirmed by Gemini" },
    unconfirmed:           { badge: "badge--warn", icon: "info",         title: "Gemini could not confirm this", detail: "Treat this result with care and check a few more leaves." },
    gemini_more_certain:   { badge: "badge--ok",   icon: "sparkle",      title: "Gemini and the detector disagreed", detail: "Gemini was highly certain and the detector was not, so Gemini's answer is shown." },
    detector_more_certain: { badge: "badge--ok",   icon: "check-circle", title: "Gemini and the detector disagreed", detail: "The detector was more sure, so its answer is shown." },
  };

  function renderVerification(d) {
    const box = $("verify-box");
    const v = d.verification || {};
    const r = v.resolution;
    box.hidden = isOther(d);
    if (isOther(d)) return;
    if (!r) {   // Gemini did not answer (no key, slow, offline)
      box.innerHTML = `<h3>Second opinion</h3><p class="muted">Gemini could not double-check this photo, so this is the detector's answer on its own.</p>`;
      return;
    }
    const meta = BASIS[r.basis] || BASIS.unconfirmed;
    const was = r.detector || {};
    const cropLine = r.crop_changed
      ? (d.crop === "cassava"
        ? "Gemini recognised a cassava leaf, so the photo was checked again with the cassava detector."
        : "Gemini recognised a maize leaf, so the photo was checked again with the maize detector.")
      : "";
    // the answer that did NOT win, so the farmer can see what was set aside
    const other = r.basis === "gemini_more_certain" && was.top_label
        ? `<p class="verify-sees"><strong>The detector said:</strong> <span>${escapeHtml(was.top_label)}</span> <span class="faint">${percent(was.top_confidence)}</span></p>`
      : r.basis === "detector_more_certain" && v.condition && v.condition !== "Cannot tell"
        ? `<p class="verify-sees"><strong>Gemini suggested:</strong> <span>${escapeHtml(v.condition)}</span></p>`
      : "";
    box.innerHTML = `<h3>Second opinion</h3>
      <span class="badge ${meta.badge}">${icon(meta.icon, "icon--sm")}${meta.title}</span>
      ${cropLine ? `<p class="verify-why">${cropLine}</p>` : ""}
      ${meta.detail ? `<p class="verify-why">${meta.detail}</p>` : ""}
      ${other}
      ${v.explanation ? `<p class="verify-why">${escapeHtml(v.explanation)}</p>` : ""}`;
  }

  // After an Auto-detect check, say which crop was recognised and how to correct it if that is wrong.
  function recognisedLine(d) {
    if (requested !== "auto" || d.verification?.resolution?.crop_changed) return "";
    const text = d.crop === "cassava"
      ? "CropGuard recognised this as a cassava leaf. Not right? Choose the crop yourself and check again."
      : "CropGuard recognised this as a maize leaf. Not right? Choose the crop yourself and check again.";
    return `<p class="muted" style="margin-top:1rem;font-size:var(--fs-sm)">${text}</p>`;
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

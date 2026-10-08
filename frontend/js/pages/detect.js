import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { drawDetection, percent, renderHeader, setBusy, toast, escapeHtml } from "../ui.js";

if (requireAuth()) init();

function init() {
  renderHeader("detect.html");
  const $ = (id) => document.getElementById(id);
  const MAX_MB = 8;
  let file = null;
  let current = null; // the detection returned by the API

  const show = (...ids) => ["upload-panel", "preview-panel", "result-panel"].forEach((id) => $(id).classList.toggle("hidden", !ids.includes(id)));

  function choose(f) {
    if (!f) return;
    if (!f.type.startsWith("image/")) return toast("Please choose an image file.", "error");
    if (f.size > MAX_MB * 1024 * 1024) return toast(`That photo is larger than ${MAX_MB} MB.`, "error");
    file = f;
    $("preview-img").src = URL.createObjectURL(f);
    show("preview-panel");
  }

  $("file-input").addEventListener("change", (e) => choose(e.target.files[0]));
  const zone = $("dropzone");
  ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("is-over"); }));
  ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("is-over"); }));
  zone.addEventListener("drop", (e) => choose(e.dataTransfer.files[0]));

  const reset = () => { file = null; current = null; $("file-input").value = ""; show("upload-panel"); };
  $("reset-btn").addEventListener("click", reset);
  $("again-btn").addEventListener("click", reset);

  $("analyze-btn").addEventListener("click", async () => {
    const btn = $("analyze-btn");
    setBusy(btn, true, "Checking…");
    try {
      current = await api.createDetection(file);
      await renderResult(current);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(btn, false);
    }
  });

  async function renderResult(d) {
    show("result-panel");
    await drawDetection($("result-canvas"), d.image, d);
    const summary = $("result-summary");
    $("advice-box").classList.add("hidden");
    if (!d.top_label) {
      summary.innerHTML = `<span class="badge badge--ok">No disease found</span>
        <p>Nothing was detected with enough confidence. Try a closer photo of one leaf in daylight.</p>`;
      $("advice-controls").classList.add("hidden");
      return;
    }
    summary.innerHTML = `<span class="badge">Disease detected</span>
      <h2>${escapeHtml(d.top_label)}</h2>
      <p class="muted">Confidence ${percent(d.top_confidence)}</p>
      <div class="meter" role="img" aria-label="Confidence ${percent(d.top_confidence)}"><span style="width:${percent(d.top_confidence)}"></span></div>`;
    $("advice-controls").classList.remove("hidden");
    if (d.advice) showAdvice(d.advice);
  }

  function showAdvice(text) {
    $("advice-text").textContent = text;
    $("advice-box").classList.remove("hidden");
  }

  $("advice-btn").addEventListener("click", async () => {
    const btn = $("advice-btn");
    setBusy(btn, true, "Asking the advisor…");
    try {
      const updated = await api.detectionAdvice(current.id, $("advice-lang").value);
      showAdvice(updated.advice);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(btn, false);
    }
  });
}

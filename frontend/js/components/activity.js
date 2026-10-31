// A short live list of what the AI is doing right now, in the style of a terminal / agent log:
//
//   ✓ Uploading photo…            2s
//   ✓ Checking the leaf…          4s
//   ◌ Double-checking with Gemini…  Comparing with the detector's answer   7s
//
// Every line is a REAL stage of the work (the page only moves to the next line when the server has finished the
// previous stage). The grey hint beside the running line rotates through what that stage involves, so the farmer can
// see that something is happening while a slow free server works. The text is translated like the rest of the page.
export function createActivity(root) {
  let line = null, hintTimer = 0, tickTimer = 0;
  root.classList.add("activity");
  root.hidden = true;

  const stopTimers = () => { clearInterval(hintTimer); clearInterval(tickTimer); hintTimer = tickTimer = 0; };

  function finish() {
    if (!line) return;
    stopTimers();
    const secs = Math.round((Date.now() - line.started) / 1000);
    line.el.classList.remove("is-running");
    line.el.classList.add("is-done");
    line.hintEl.textContent = "";
    line.timeEl.textContent = secs >= 1 ? `${secs}s` : "";
    line = null;
  }

  return {
    /** Mark the previous line done and start a new running one. Repeating the same title does nothing. */
    step(title, hints = []) {
      if (line && line.title === title) return;
      finish();
      root.hidden = false;
      const el = document.createElement("li");
      el.className = "activity__line is-running";
      el.innerHTML = '<span class="activity__mark" aria-hidden="true"><i></i><i></i><i></i></span><span class="activity__title"></span><span class="activity__hint"></span><span class="activity__time"></span>';
      const titleEl = el.querySelector(".activity__title"), hintEl = el.querySelector(".activity__hint"), timeEl = el.querySelector(".activity__time");
      titleEl.textContent = title;
      root.append(el);
      const me = { el, title, hintEl, timeEl, started: Date.now() };
      line = me;
      if (hints.length) {
        let i = 0;
        hintEl.textContent = hints[0];
        if (hints.length > 1) hintTimer = setInterval(() => { i = (i + 1) % hints.length; hintEl.textContent = hints[i]; }, 2400);
      }
      tickTimer = setInterval(() => { const s = Math.floor((Date.now() - me.started) / 1000); if (s >= 3) timeEl.textContent = `${s}s`; }, 1000);
    },
    /** Finish the running line and keep the whole log on screen. */
    stop: finish,
    /** Remove everything (used when the real answer starts to appear, or before a new run). */
    clear() { stopTimers(); line = null; root.innerHTML = ""; root.hidden = true; },
  };
}

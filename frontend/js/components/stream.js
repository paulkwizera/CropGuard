// Show an AI answer growing on screen while it is still being written.
import { renderAdvice } from "./format.js";

/** Markdown that is cut off half-way ("**bol") would flash stray asterisks, so close it for display only. */
export function partialHtml(text) {
  const openBold = (String(text).match(/\*\*/g) || []).length % 2 === 1;
  return renderAdvice(openBold ? `${text}**` : text);
}

/**
 * Pieces arrive from the server in bursts (a sentence at a time). The writer reveals them at an even pace, a few
 * letters per frame, speeding up when it falls behind so it never lags far behind the real answer.
 *   const w = smoothWriter((shown) => { box.innerHTML = partialHtml(shown); });
 *   w.push("Hello ");  w.push("farmer");
 *   await w.finish(fullText);   // shows the rest, then resolves
 */
export function smoothWriter(render) {
  let target = "", shown = 0, timer = 0, waiting = null;
  const tick = () => {
    timer = 0;
    const backlog = target.length - shown;
    if (backlog > 0) {
      shown = Math.min(target.length, shown + Math.max(1, Math.ceil(backlog / 40)));
      render(target.slice(0, shown));
    }
    if (shown < target.length) timer = setTimeout(tick, 16);
    else if (waiting) { const done = waiting; waiting = null; done(); }
  };
  const kick = () => { if (!timer) timer = setTimeout(tick, 16); };
  return {
    push(text) { target += text; kick(); },
    /** `full` (optional) replaces what was pushed: used when streaming was unavailable and the whole answer arrives at once. */
    finish(full) {
      if (typeof full === "string") target = full;
      return new Promise((resolve) => { waiting = resolve; kick(); });
    },
    text: () => target,
  };
}

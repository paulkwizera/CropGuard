import { icon } from "./icons.js";
import { escapeHtml } from "./format.js";

/** Close a native <dialog> when the dark backdrop is clicked. */
export function enableBackdropClose(dialog) {
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
}

/** Accessible confirmation: resolves true if confirmed. Native <dialog> traps focus and handles Esc. */
export function confirmDialog({ title, message, confirmLabel = "Confirm", cancelLabel = "Cancel", danger = false }) {
  return new Promise((resolve) => {
    const dialog = document.createElement("dialog");
    dialog.className = "modal modal--sm";
    dialog.setAttribute("aria-labelledby", "confirm-title");
    dialog.setAttribute("aria-describedby", "confirm-message");
    dialog.innerHTML = `
      <div class="modal-body stack">
        <h2 id="confirm-title">${escapeHtml(title)}</h2>
        <p id="confirm-message" class="muted" style="margin:0">${escapeHtml(message)}</p>
      </div>
      <div class="modal-foot">
        <button type="button" class="btn btn--secondary" data-act="cancel">${escapeHtml(cancelLabel)}</button>
        <button type="button" class="btn ${danger ? "btn--danger" : ""}" data-act="ok">${danger ? icon("trash", "icon--sm") : ""}${escapeHtml(confirmLabel)}</button>
      </div>`;
    document.body.append(dialog);
    let result = false;
    dialog.addEventListener("click", (e) => {
      const act = e.target.closest("[data-act]")?.dataset.act;
      if (act === "ok") { result = true; dialog.close(); }
      else if (act === "cancel" || e.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => { dialog.remove(); resolve(result); });
    dialog.showModal();
    dialog.querySelector('[data-act="cancel"]').focus();
  });
}

export const closeButton = (label = "Close") => `<button type="button" class="icon-btn" data-close aria-label="${label}">${icon("x")}</button>`;

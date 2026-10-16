import { icon } from "./icons.js";
import { escapeHtml } from "./format.js";

export function toast(message, type = "success") {
  let box = document.getElementById("toasts");
  if (!box) {
    box = document.createElement("div");
    box.id = "toasts";
    box.setAttribute("role", "region");
    box.setAttribute("aria-label", "Notifications");
    document.body.append(box);
  }
  const el = document.createElement("div");
  const isError = type === "error";
  el.className = `toast ${isError ? "toast--error" : ""}`;
  el.setAttribute("role", isError ? "alert" : "status");
  el.innerHTML = `${icon(isError ? "alert" : "check-circle")}<p>${escapeHtml(message)}</p><button type="button" aria-label="Dismiss">${icon("x", "icon--sm")}</button>`;
  box.append(el);
  const close = () => { el.classList.add("is-leaving"); setTimeout(() => el.remove(), 220); };
  el.querySelector("button").addEventListener("click", close);
  setTimeout(close, isError ? 8000 : 4500);
}

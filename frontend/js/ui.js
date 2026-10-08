import { isLoggedIn, logout } from "./auth.js";
import { CONFIG } from "./config.js";

const NAV = [
  { href: "detect.html", label: "Check a plant", auth: true },
  { href: "history.html", label: "My checks", auth: true },
  { href: "advisory.html", label: "Weather advice", auth: true },
];

/** Renders the shared header into <header id="site-header">. `active` = current file name. */
export function renderHeader(active) {
  const host = document.getElementById("site-header");
  if (!host) return;
  const links = isLoggedIn()
    ? NAV.map((n) => `<a href="${n.href}" ${n.href === active ? 'aria-current="page"' : ""}>${n.label}</a>`).join("") +
      `<button type="button" id="logout-btn">Sign out</button>`
    : `<a href="login.html" ${active === "login.html" ? 'aria-current="page"' : ""}>Sign in</a><a href="register.html">Create account</a>`;
  host.className = "site-header";
  host.innerHTML = `<div class="container">
    <a class="brand" href="index.html">Crop<span>Guard</span></a>
    <nav class="nav" aria-label="Main">${links}</nav></div>`;
  document.getElementById("logout-btn")?.addEventListener("click", logout);

  if (CONFIG.USE_MOCK) {
    const note = document.createElement("div");
    note.style.cssText = "background:#e8b931;color:#2b2118;text-align:center;font-size:.8rem;padding:.2rem";
    note.textContent = "Demo mode: showing sample data (set USE_MOCK to false in js/config.js to use the real API)";
    host.after(note);
  }
}

export function toast(message, type = "info") {
  let box = document.getElementById("toasts");
  if (!box) { box = document.createElement("div"); box.id = "toasts"; box.setAttribute("aria-live", "polite"); document.body.append(box); }
  const t = document.createElement("div");
  t.className = `toast ${type === "error" ? "toast--error" : ""}`;
  t.textContent = message;
  box.append(t);
  setTimeout(() => t.remove(), 5000);
}

export function setBusy(button, busy, busyText = "Please wait…") {
  if (busy) { button.dataset.label = button.textContent; button.textContent = busyText; }
  else if (button.dataset.label) button.textContent = button.dataset.label;
  button.disabled = busy;
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function percent(x) { return `${Math.round(x * 100)}%`; }

/** Draw detection boxes on a canvas that already holds `img`'s natural size. */
export function drawDetection(canvas, imageUrl, detection) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      const unit = Math.max(2, img.naturalWidth / 200);
      ctx.lineWidth = unit;
      ctx.font = `600 ${unit * 6}px sans-serif`;
      for (const r of detection.results) {
        const [x1, y1, x2, y2] = r.bbox;
        ctx.strokeStyle = "#e8b931";
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        const text = `${r.label} ${percent(r.confidence)}`;
        const w = ctx.measureText(text).width + unit * 3;
        ctx.fillStyle = "#e8b931";
        ctx.fillRect(x1, Math.max(0, y1 - unit * 8), w, unit * 8);
        ctx.fillStyle = "#2b2118";
        ctx.fillText(text, x1 + unit * 1.5, Math.max(unit * 6, y1 - unit * 2));
      }
      resolve();
    };
    img.onerror = () => resolve();
    img.src = imageUrl;
  });
}

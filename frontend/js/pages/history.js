import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { escapeHtml, formatDate, percent, renderHeader, toast } from "../ui.js";

if (requireAuth()) init();

async function init() {
  renderHeader("history.html");
  const list = document.getElementById("history-list");
  const empty = document.getElementById("history-empty");

  async function load() {
    try {
      const { results } = await api.listDetections();
      empty.classList.toggle("hidden", results.length > 0);
      list.innerHTML = results.map((d) => `
        <article class="card stack" data-id="${d.id}">
          <div class="thumb" ${d.image ? `style="background-image:url('${encodeURI(d.image)}')"` : ""}>${d.image ? "" : "No photo"}</div>
          <div>
            <strong>${escapeHtml(d.top_label || "No disease found")}</strong>
            ${d.top_confidence ? `<span class="muted"> · ${percent(d.top_confidence)}</span>` : ""}
            <div class="muted">${formatDate(d.created_at)}</div>
          </div>
          <button class="btn btn--danger" data-delete="${d.id}" type="button">Delete</button>
        </article>`).join("");
    } catch (err) {
      toast(err.message, "error");
    }
  }

  list.addEventListener("click", async (e) => {
    const id = e.target.dataset?.delete;
    if (!id || !confirm("Delete this check?")) return;
    try { await api.deleteDetection(id); await load(); } catch (err) { toast(err.message, "error"); }
  });

  load();
}

import { isLoggedIn } from "../auth.js";
import { mountPublicFooter, mountPublicHeader } from "../components/shell.js";

mountPublicHeader();
mountPublicFooter();

if (isLoggedIn()) {
  for (const id of ["cta-primary", "cta-band"]) {
    const el = document.getElementById(id);
    el.textContent = "Open your dashboard";
    el.href = "dashboard.html";
  }
  document.getElementById("cta-secondary").hidden = true;
  const title = document.getElementById("cta-title");
  if (title) title.textContent = "Ready for your next check?";
}

// the three headline numbers come from the survey summary used on the story page
fetch("assets/data/story.json").then((r) => (r.ok ? r.json() : Promise.reject())).then((d) => {
  document.querySelectorAll("[data-bind]").forEach((el) => {
    const v = el.dataset.bind.split(".").reduce((o, k) => o?.[k], d);
    el.textContent = v == null ? "–" : `${Math.round(v)}%`;
  });
}).catch(() => { document.querySelector(".story-teaser dl")?.remove(); });

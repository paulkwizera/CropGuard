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

import { isLoggedIn } from "../auth.js";
import { renderHeader } from "../ui.js";

renderHeader("index.html");
if (isLoggedIn()) {
  const primary = document.getElementById("cta-primary");
  primary.textContent = "Check a plant";
  primary.href = "detect.html";
  document.getElementById("cta-secondary").classList.add("hidden");
}

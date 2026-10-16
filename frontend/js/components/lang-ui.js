import { LANGS, currentLang, hasChosenLang, setLang } from "../i18n.js";
import { icon } from "./icons.js";
import { isLoggedIn } from "../auth.js";
import { updateMe } from "../session.js";

/** Store the choice, tell the server (if signed in) and reload so every string is rebuilt in the new language. */
export async function changeLanguage(code) {
  setLang(code);
  if (isLoggedIn()) {
    try { await Promise.race([updateMe({ preferred_language: code }), new Promise((r) => setTimeout(r, 1500))]); } catch { /* the device choice still applies */ }
  }
  window.location.reload();
}

/** Compact language picker (globe + select). `host` is any empty element. */
export function mountLangSwitch(host) {
  if (!host) return;
  host.innerHTML = `<label class="lang-switch">${icon("globe", "icon--sm")}<span class="visually-hidden">Language</span>
    <select>${LANGS.map((l) => `<option value="${l.code}" lang="${l.code}" ${l.code === currentLang() ? "selected" : ""}>${l.label}</option>`).join("")}</select></label>`;
  host.querySelector("select").addEventListener("change", (e) => changeLanguage(e.target.value));
}

const PROMPT = {
  rw: { hint: "Gukomeza mu Kinyarwanda", label: "Kinyarwanda" },
  en: { hint: "Continue in English", label: "English" },
  fr: { hint: "Continuer en français", label: "Français" },
};

/** First visit: ask which language to use. Shown in all three languages, cannot be dismissed without choosing. */
export function promptForLanguage() {
  if (hasChosenLang() || document.getElementById("lang-prompt")) return;
  const dialog = document.createElement("dialog");
  dialog.id = "lang-prompt";
  dialog.className = "modal modal--sm lang-prompt";
  dialog.setAttribute("aria-labelledby", "lp-title");
  dialog.innerHTML = `<div class="modal-body">
      <span class="lp-icon">${icon("globe", "icon--lg")}</span>
      <h2 id="lp-title"><span lang="rw">Hitamo ururimi</span><span lang="en">Choose your language</span><span lang="fr">Choisissez votre langue</span></h2>
      <div class="lang-options">${LANGS.map((l) => `<button type="button" class="lang-option" data-code="${l.code}" lang="${l.code}"><strong>${PROMPT[l.code].label}</strong><span>${PROMPT[l.code].hint}</span>${icon("arrow", "icon--sm")}</button>`).join("")}</div>
    </div>`;
  dialog.addEventListener("cancel", (e) => e.preventDefault());
  dialog.addEventListener("click", (e) => { const b = e.target.closest("[data-code]"); if (b) changeLanguage(b.dataset.code); });
  document.body.append(dialog);
  dialog.showModal();
  dialog.querySelector("button").focus();
}

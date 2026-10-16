import { api } from "../api.js";
import { isLoggedIn, saveTokens } from "../auth.js";
import { mountAuthAside } from "../components/shell.js";
import { bindPasswordToggle, bindValidation, clearAll, setBusy, showFormError } from "../components/forms.js";
import { getMe } from "../session.js";
import { hasChosenLang, setLang } from "../i18n.js";

if (isLoggedIn()) window.location.replace("dashboard.html");
mountAuthAside();

const form = document.getElementById("login-form");
if (new URLSearchParams(location.search).has("expired")) document.getElementById("expired-note").hidden = false;
bindPasswordToggle(document.getElementById("toggle-pw"), form.password);

const validate = bindValidation(form, {
  username: (v) => (v ? "" : "Enter your username."),
  password: (v) => (v ? "" : "Enter your password."),
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAll(form);
  if (!validate()) return;
  const button = form.querySelector("button[type=submit]");
  setBusy(button, true);
  try {
    saveTokens(await api.login(form.username.value.trim(), form.password.value));
    const me = await getMe({ fresh: true }).catch(() => null);
    if (me?.preferred_language && !hasChosenLang()) setLang(me.preferred_language);
    window.location.href = "dashboard.html";
  } catch (err) {
    showFormError(form, err.status === 401 || err.status === 400 ? "That username and password do not match. Check them and try again." : err.message);
    setBusy(button, false);
  }
});

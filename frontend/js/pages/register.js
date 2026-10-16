import { api } from "../api.js";
import { isLoggedIn, saveTokens } from "../auth.js";
import { mountAuthAside } from "../components/shell.js";
import { applyApiErrors, bindPasswordToggle, bindValidation, clearAll, setBusy, showFormError } from "../components/forms.js";
import { fillDistricts, getLanguage, mountLanguage } from "../components/lang.js";
import { getMe } from "../session.js";
import { adviceLang, setLang } from "../i18n.js";

if (isLoggedIn()) window.location.replace("dashboard.html");
mountAuthAside();

const form = document.getElementById("register-form");
const seg = document.getElementById("lang-seg");
mountLanguage(seg, adviceLang(), "preferred_language");
fillDistricts(document.getElementById("districts"));
bindPasswordToggle(document.getElementById("toggle-pw"), form.password);

const validate = bindValidation(form, {
  username: (v) => (v.length < 3 ? "Use at least 3 characters." : /^[\w.@+-]+$/.test(v) ? "" : "Use only letters, numbers and . @ + - _"),
  password: (v) => (v.length < 8 ? "Use at least 8 characters." : /^\d+$/.test(v) ? "A password cannot be only numbers." : ""),
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAll(form);
  if (!validate()) return;
  const button = form.querySelector("button[type=submit]");
  setBusy(button, true);
  const data = {
    username: form.username.value.trim(),
    password: form.password.value,
    district: form.district.value.trim(),
    preferred_language: getLanguage(seg),
  };
  try {
    await api.register(data);
    saveTokens(await api.login(data.username, data.password)); // sign in straight away
    setLang(data.preferred_language); // the interface follows the language they picked
    await getMe({ fresh: true }).catch(() => {});
    window.location.href = "dashboard.html";
  } catch (err) {
    if (!applyApiErrors(form, err)) showFormError(form, err.message);
    setBusy(button, false);
  }
});

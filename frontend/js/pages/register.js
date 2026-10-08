import { api } from "../api.js";
import { saveTokens } from "../auth.js";
import { renderHeader, setBusy } from "../ui.js";

renderHeader("register.html");
const form = document.getElementById("register-form");
const errorBox = document.getElementById("form-error");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.classList.add("hidden");
  const button = form.querySelector("button[type=submit]");
  setBusy(button, true, "Creating account…");
  try {
    const data = {
      username: form.username.value.trim(),
      password: form.password.value,
      district: form.district.value.trim(),
      preferred_language: form.preferred_language.value,
    };
    await api.register(data);
    saveTokens(await api.login(data.username, data.password)); // sign in straight away
    window.location.href = "detect.html";
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.classList.remove("hidden");
  } finally {
    setBusy(button, false);
  }
});

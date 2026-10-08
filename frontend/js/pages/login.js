import { api } from "../api.js";
import { saveTokens } from "../auth.js";
import { renderHeader, setBusy } from "../ui.js";

renderHeader("login.html");
const form = document.getElementById("login-form");
const errorBox = document.getElementById("form-error");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.classList.add("hidden");
  const button = form.querySelector("button[type=submit]");
  setBusy(button, true, "Signing in…");
  try {
    saveTokens(await api.login(form.username.value.trim(), form.password.value));
    window.location.href = "detect.html";
  } catch (err) {
    errorBox.textContent = err.status === 401 ? "Wrong username or password." : err.message;
    errorBox.classList.remove("hidden");
  } finally {
    setBusy(button, false);
  }
});

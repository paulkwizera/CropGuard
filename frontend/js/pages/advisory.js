import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { escapeHtml, renderHeader, setBusy } from "../ui.js";

if (requireAuth()) init();

async function init() {
  renderHeader("advisory.html");
  const form = document.getElementById("advisory-form");
  const errorBox = document.getElementById("form-error");
  const result = document.getElementById("advisory-result");

  // Pre-fill from the farmer's profile
  try {
    const me = await api.me();
    if (me.district) form.city.value = me.district;
    if (me.preferred_language) form.language.value = me.preferred_language;
  } catch { /* the form still works without it */ }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.classList.add("hidden");
    const button = form.querySelector("button[type=submit]");
    setBusy(button, true, "Getting advice…");
    try {
      const data = await api.advisory(form.city.value.trim(), form.language.value);
      document.getElementById("out-city").textContent = data.city;
      document.getElementById("out-advice").textContent = data.advisory;
      document.getElementById("out-totals").textContent =
        `Rain expected: ${data.weather.total_rain_mm} mm · Average temperature: ${data.weather.avg_temp_c} °C`;
      document.getElementById("out-rows").innerHTML = data.weather.readings.map((r) => `
        <tr><td>${escapeHtml(r.datetime.slice(11, 16))}</td><td>${r.temp_c} °C</td><td>${r.humidity}%</td>
        <td>${escapeHtml(r.description)}</td><td>${r.rain_mm} mm</td></tr>`).join("");
      result.classList.remove("hidden");
    } catch (err) {
      errorBox.textContent = err.message;
      errorBox.classList.remove("hidden");
      result.classList.add("hidden");
    } finally {
      setBusy(button, false);
    }
  });
}

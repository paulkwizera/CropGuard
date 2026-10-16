import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { mountShell } from "../components/shell.js";
import { weatherChart } from "../components/chart.js";
import { clearAll, setBusy, setError, showFormError } from "../components/forms.js";
import { escapeHtml, renderAdvice } from "../components/format.js";
import { fillDistricts, getLanguage, mountLanguage } from "../components/lang.js";
import { getMe } from "../session.js";
import { adviceLang, t } from "../i18n.js";

if (requireAuth()) init();

async function init() {
  mountShell("advisory");
  const $ = (id) => document.getElementById(id);
  const form = $("adv-form");
  const seg = $("lang-seg");
  mountLanguage(seg, adviceLang(), "language");
  fillDistricts($("districts"));

  try {
    const me = await getMe();
    if (me.district) form.city.value = me.district;
  } catch { /* the form still works without a profile */ }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAll(form);
    const city = form.city.value.trim();
    if (!city) { setError(form.city, "Enter your district or nearest town."); form.city.focus(); return; }
    const button = form.querySelector("button[type=submit]");
    setBusy(button, true);
    $("adv-result").hidden = true;
    $("adv-loading").hidden = false;
    try {
      render(await api.advisory(city, getLanguage(seg)));
      $("adv-result").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      showFormError(form, err.message.includes("not found") ? t("We could not find that place. Try a nearby town.") : err.message);
    } finally {
      setBusy(button, false);
      $("adv-loading").hidden = true;
    }
  });

  function render(data) {
    const r = data.weather.readings;
    $("out-city").textContent = data.city;
    $("out-advice").innerHTML = renderAdvice(data.advisory);
    $("out-rain").textContent = `${data.weather.total_rain_mm} mm`;
    $("out-temp").textContent = `${data.weather.avg_temp_c}°C`;
    $("out-hum").textContent = `${Math.max(...r.map((x) => x.humidity))}%`;
    $("chart").innerHTML = weatherChart(r);
    $("out-rows").innerHTML = r.map((x) => `<tr><th scope="row">${escapeHtml(x.datetime.slice(11, 16))}</th><td>${x.temp_c}°C</td><td>${x.humidity}%</td><td>${escapeHtml(x.description)}</td><td>${x.wind_m_s} m/s</td><td>${x.rain_mm} mm</td></tr>`).join("");
    $("adv-result").hidden = false;
  }
}

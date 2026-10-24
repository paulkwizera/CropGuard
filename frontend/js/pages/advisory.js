import { api } from "../api.js";
import { requireAuth } from "../auth.js";
import { mountShell } from "../components/shell.js";
import { weatherChart } from "../components/chart.js";
import { clearAll, setBusy, setError, showFormError } from "../components/forms.js";
import { escapeHtml, renderAdvice } from "../components/format.js";
import { fillDistricts, getLanguage, mountLanguage, setLanguage } from "../components/lang.js";
import { toast } from "../components/toast.js";
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

  // Language tabs on the advice itself: switch Kinyarwanda / English / Français without filling the form again.
  const tabs = $("adv-tabs");
  const cache = new Map();   // "city|language" -> advice text
  let current = { city: "", language: adviceLang() };
  mountLanguage(tabs, current.language, "adv_lang");
  tabs.addEventListener("change", async (e) => {
    const language = e.target.value;
    setLanguage(seg, language); // keep the form in step
    const key = `${current.city}|${language}`;
    if (cache.has(key)) { current.language = language; $("out-advice").innerHTML = renderAdvice(cache.get(key)); return; }
    $("out-advice").setAttribute("aria-busy", "true");
    $("out-advice").innerHTML = `<div class="skeleton" style="height:1rem;width:90%;margin-bottom:.6rem"></div><div class="skeleton" style="height:1rem;width:75%;margin-bottom:.6rem"></div><div class="skeleton" style="height:1rem;width:60%"></div>`;
    try {
      const data = await api.advisory(current.city, language);
      cache.set(key, data.advisory);
      current.language = language;
      $("out-advice").innerHTML = renderAdvice(data.advisory);
    } catch (err) {
      toast(err.message, "error");
      setLanguage(tabs, current.language); setLanguage(seg, current.language);
      $("out-advice").innerHTML = renderAdvice(cache.get(`${current.city}|${current.language}`) || "");
    } finally {
      $("out-advice").removeAttribute("aria-busy");
    }
  });

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
    current = { city: data.city, language: data.language };
    cache.clear(); cache.set(`${data.city}|${data.language}`, data.advisory);
    setLanguage(tabs, data.language);
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

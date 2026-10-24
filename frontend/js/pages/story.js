import { isLoggedIn } from "../auth.js";
import { mountPublicFooter, mountPublicHeader } from "../components/shell.js";
import { bars, compare, pairBars, pctText, stacks, waffle } from "../components/story-charts.js";
import { currentLocale, t } from "../i18n.js";

mountPublicHeader("story");
mountPublicFooter();
if (isLoggedIn()) {
  const cta = document.getElementById("cta-band");
  cta.textContent = "Open your dashboard";
  cta.href = "dashboard.html";
}

const $ = (id) => document.getElementById(id);
const get = (obj, path) => path.split(".").reduce((o, k) => o?.[k], obj);
const numberFmt = new Intl.NumberFormat([currentLocale(), "en"]);

const COLORS = {
  leaf: "var(--leaf-600)", cassava: "var(--cassava)", sand: "#cfc9b6", sandDark: "#b9b29b",
  down2: "#7a1d16", down1: "#b3382c", up1: "#2b7d3b", up2: "#17502a", rain: "#2b7a8c", kernel: "#f0b823", danger: "#a8281f",
};
const PROVINCES = { Kigali: "Kigali", North: "North", South: "South", East: "East", West: "West" };

async function load() {
  let data;
  try {
    const res = await fetch("assets/data/story.json");
    if (!res.ok) throw new Error(res.status);
    data = await res.json();
  } catch {
    document.querySelectorAll(".chapter-viz").forEach((box) => { box.innerHTML = `<p class="alert alert--error" role="alert">The survey numbers could not be loaded. Open this page through the local server (run-frontend.bat) and reload.</p>`; });
    return;
  }
  draw(data);
}

function draw(d) {
  // ---- numbers inside sentences and headline stats
  document.querySelectorAll("[data-bind]").forEach((el) => {
    const v = get(d, el.dataset.bind);
    el.textContent = v == null ? "–" : el.dataset.fmt === "int" ? numberFmt.format(v) : pctText(v);
  });

  // 1. what is grown
  const highlight = new Set(["Maize", "Cassava"]);
  $("chart-crops").innerHTML = bars(d.top_crops.map((c) => ({ label: c.crop, value: c.share, color: highlight.has(c.crop) ? COLORS.leaf : COLORS.sandDark })));
  $("chart-province").innerHTML = pairBars(d.by_province.map((p) => ({ label: PROVINCES[p.province] || p.province, a: p.maize, b: p.cassava })), COLORS.leaf, COLORS.cassava);
  const kigali = d.by_province.find((p) => p.province === "Kigali");
  $("province-note").textContent = kigali ? t("Kigali: only {n} farming households were surveyed, so read it with care.", { n: kigali.farming_households }) : "";

  // 2. production compared with the previous season
  const change = (c, label) => ({ label, parts: [
    { value: c.highly_decreased, color: COLORS.down2, name: "Much smaller" }, { value: c.decreased, color: COLORS.down1, name: "Smaller" },
    { value: c.no_change, color: COLORS.sand, name: "No change" },
    { value: c.increased, color: COLORS.up1, name: "Bigger" }, { value: c.highly_increased, color: COLORS.up2, name: "Much bigger" }] });
  $("chart-change").innerHTML = stacks([change(d.production_change.all, "All crops"), change(d.production_change.maize, "Maize"), change(d.production_change.cassava, "Cassava")]);

  // 3. water
  const w = d.water;
  const water = [
    { value: w.irrigated, color: COLORS.rain, name: "Irrigated" },
    { value: w.no_water, color: COLORS.danger, name: "No water available" },
    { value: w.cannot_afford, color: COLORS.kernel, name: "Cannot afford irrigation" },
    { value: w.not_needed, color: COLORS.sand, name: "Farmer says irrigation is not needed" },
  ];
  $("chart-water").innerHTML = waffle(water);
  $("chart-water").setAttribute("aria-label", water.map((p) => `${t(p.name)} ${pctText(p.value)}`).join(", "));
  $("legend-water").innerHTML = water.map((p) => `<li style="--c:${p.color}"><span>${p.name}</span><b>${pctText(p.value)}</b></li>`).join("");

  // 4. seeds and yield
  const seed = (s, label) => ({ label, parts: [{ value: s.improved + s.both, color: COLORS.leaf, name: "Improved" }, { value: s.traditional, color: COLORS.sandDark, name: "Traditional" }] });
  $("chart-seeds").innerHTML = stacks([seed(d.seeds.maize, "Maize"), seed(d.seeds.cassava, "Cassava"), seed(d.seeds.all, "All crops")]);
  const y = d.maize_yield;
  if (y.traditional.median_kg_ha && y.improved.median_kg_ha) {
    const gain = Math.round((y.improved.median_kg_ha / y.traditional.median_kg_ha - 1) * 100);
    $("chart-yield").innerHTML = compare([
      { label: "Traditional seed", value: y.traditional.median_kg_ha, text: `${numberFmt.format(y.traditional.median_kg_ha)} kg`, color: COLORS.sandDark },
      { label: "Improved seed", value: y.improved.median_kg_ha, text: `${numberFmt.format(y.improved.median_kg_ha)} kg`, color: COLORS.leaf },
    ]) + `<p class="big big--good compare-gain"><strong>+${gain}%</strong><span>higher with improved seed</span></p>`;
  } else {
    $("chart-yield").closest("figure").hidden = true;
  }

  // 5. advice
  const a = d.advice;
  $("chart-advice").innerHTML = bars([
    { label: "Received no advisory service", value: a.no_service, color: COLORS.danger },
    { label: "Trained in pest management", value: a.pest_management },
    { label: "Given weather and climate information", value: a.weather_info },
    { label: "Have crop insurance", value: a.crop_insurance },
  ]);

  // 6. phones
  const p = d.phones;
  $("chart-phones").innerHTML = bars([
    { label: "Households with at least one phone owner", value: p.household_has_phone },
    { label: "People who own a phone", value: p.people_with_phone },
    { label: "Phone owners with a smartphone", value: p.owners_with_smartphone },
    { label: "People who used the internet recently", value: p.used_internet },
  ]);
}

// bars grow when their chapter scrolls into view (everything is visible straight away without IntersectionObserver or with reduced motion)
function reveal() {
  const items = document.querySelectorAll(".reveal");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!("IntersectionObserver" in window) || reduce) { items.forEach((el) => el.classList.add("in-view")); return; }
  const io = new IntersectionObserver((entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in-view"); io.unobserve(e.target); } }), { threshold: 0.15 });
  items.forEach((el) => io.observe(el));
}

load().then(reveal);

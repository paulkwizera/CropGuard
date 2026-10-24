// Fake backend so the frontend can be built before the Django API is ready.
// It mirrors the contract in docs/API.md. Data lives in memory (resets on reload).
// the two classes of the real maize model (ml/labels.json)
const LABELS = {
  maize: [["MLB", "Maize Leaf Blight", false], ["MSV", "Maize Streak Virus", false]],
  cassava: [["Cassava_Mosaic Disease", "Cassava Mosaic Disease", false], ["Cassava_Green Mottle", "Cassava Green Mottle", false], ["Cassava_Bacterial Blight", "Cassava Bacterial Blight", false], ["Healthy", "Healthy cassava leaf", true]],
};
const wait = (ms = 500) => new Promise((r) => setTimeout(r, ms));
const uid = () => Math.random().toString(16).slice(2).padEnd(24, "0").slice(0, 24);

// Add ?seed=1 to any URL (once per tab) to preload sample checks so history and dashboard look populated.
const SEEDED = new URLSearchParams(location.search).has("seed") ? (sessionStorage.setItem("cropguard.seed", "1"), true) : sessionStorage.getItem("cropguard.seed") === "1";

function sampleLeaf(spot) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480"><rect width="640" height="480" fill="#5b4a34"/><path d="M60 440C140 260 330 130 590 70C500 290 320 410 60 440Z" fill="#3a7d44"/><path d="M60 440L590 70" stroke="#a3d19a" stroke-width="6"/><ellipse cx="${spot[0]}" cy="${spot[1]}" rx="44" ry="13" fill="#e2cf6a" opacity=".6" transform="rotate(-37 ${spot[0]} ${spot[1]})"/><ellipse cx="${spot[0]}" cy="${spot[1]}" rx="30" ry="7" fill="#6e5230" transform="rotate(-37 ${spot[0]} ${spot[1]})"/></svg>`;
  return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
}

let me = { id: uid(), username: "demo", email: "", phone: "", district: "Musanze", preferred_language: "rw" };
const store = [];
if (SEEDED) {
  const H = 3600e3;
  [["Maize Leaf Blight", 0.93, 1, [330, 250]], ["Maize Streak Virus", 0.88, 26, [260, 300]], ["Maize Leaf Blight", 0.81, 74, [400, 190]], ["Maize Streak Virus", 0.86, 200, [300, 260]], [null, null, 500, [300, 260]]].forEach(([label, conf, hoursAgo, spot]) => {
    const [x, y] = spot;
    store.push({
      id: uid(), crop: "maize", status: label ? "disease" : "none", image: sampleLeaf(spot), image_width: 640, image_height: 480,
      top_label: label || "", top_confidence: conf,
      results: label ? [{ code: label === "Maize Leaf Blight" ? "MLB" : "MSV", label, confidence: conf, bbox: [x - 55, y - 48, x + 55, y + 48] }] : [],
      advice: "", created_at: new Date(Date.now() - hoursAgo * H).toISOString(),
    });
  });
}

function fakeResult(imageUrl, w, h, crop = "maize") {
  const pool = LABELS[crop] || LABELS.maize;
  const [code, label, healthy] = pool[Math.floor(Math.random() * pool.length)];
  const confidence = +(0.8 + Math.random() * 0.19).toFixed(2);
  return {
    id: uid(), crop, status: healthy ? "healthy" : "disease", image: imageUrl, image_width: w, image_height: h,
    top_label: label, top_confidence: confidence,
    results: [{ code, label, healthy, confidence, bbox: [w * 0.2, h * 0.25, w * 0.7, h * 0.75] }],
    advice: "", created_at: new Date().toISOString(),
  };
}

function imageSize(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve([img.naturalWidth, img.naturalHeight]);
    img.onerror = () => resolve([640, 480]);
    img.src = url;
  });
}

export const mock = {
  async register(data) { await wait(); me = { ...me, ...data, id: uid() }; delete me.password; return me; },
  async login() { await wait(); return { access: "mock-access", refresh: "mock-refresh" }; },
  async me() { await wait(150); return me; },
  async updateMe(data) { await wait(400); me = { ...me, ...data }; return me; },

  async crops() { await wait(150); return [{ id: "maize", name: "Maize", available: true }, { id: "cassava", name: "Cassava", available: true }]; },
  async createDetection(file, onProgress, crop = "maize") {
    for (const p of [0.2, 0.5, 0.8, 1]) { await wait(180); onProgress?.(p); }
    await wait(900);
    const url = URL.createObjectURL(file);
    const [w, h] = await imageSize(url);
    const d = fakeResult(url, w, h, crop);
    store.unshift(d);
    return d;
  },
  async listDetections() { await wait(); return { count: store.length, next: null, previous: null, results: store }; },
  async getDetection(id) { await wait(200); return store.find((d) => d.id === id); },
  async deleteDetection(id) { await wait(200); const i = store.findIndex((d) => d.id === id); if (i >= 0) store.splice(i, 1); },
  async detectionAdvice(id, language) {
    await wait(1000);
    const d = store.find((x) => x.id === id);
    d.advice = `(mock, ${language}) ${d.top_label}: remove badly infected leaves, avoid overhead watering, and rotate crops next season.`;
    return d;
  },

  async weather(city) {
    await wait();
    const readings = Array.from({ length: 8 }, (_, i) => ({
      datetime: `2026-10-08 ${String(i * 3).padStart(2, "0")}:00:00`,
      temp_c: 17 + i, humidity: 70 + i, description: i % 3 === 0 ? "light rain" : "scattered clouds",
      wind_m_s: 2.1, rain_mm: i % 3 === 0 ? 1.2 : 0,
    }));
    return { city, readings, total_rain_mm: 3.6, avg_temp_c: 20.5 };
  },
  async advisory(city, language) {
    const weather = await this.weather(city);
    await wait(900);
    return { city, language, weather, advisory: `(mock, ${language}) Some rain is expected today, so you can skip irrigation. Do not spray pesticides before the rain.` };
  },
  async assistantChat(messages, language) {
    await wait(1100);
    const q = (messages.at(-1)?.content || "").toLowerCase();
    const tip = /seed|plant/.test(q) ? "Choose certified seed from a trusted agro-dealer and plant at the start of the rains."
      : /pest|worm|disease|streak|blight/.test(q) ? "Walk the field weekly, remove badly infected plants, and ask your local agronomist about the right product."
      : "Plant early with certified seed, space plants well, weed on time, and add manure or the recommended fertilizer.";
    return { reply: `(demo answer, ${language}) ${tip}\n\n- Start with one small change this season.\n- Keep notes so you can compare harvests.`, language };
  },
  async health() { return { status: "ok", mongodb: "mock" }; },
};

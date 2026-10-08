// All HTTP calls live here. Pages never call fetch() directly.
// Keep function names and response shapes in sync with docs/API.md.
import { CONFIG } from "./config.js";
import { clearTokens, getTokens, saveTokens } from "./auth.js";
import { mock } from "./mock.js";

export class ApiError extends Error {
  constructor(message, status, details) { super(message); this.status = status; this.details = details; }
}

/** Turn DRF error bodies ({field: ["msg"]} or {detail: "msg"}) into one readable string. */
function readableError(body) {
  if (!body) return "Something went wrong. Please try again.";
  if (typeof body === "string") return body;
  if (body.detail) return body.detail;
  return Object.entries(body).map(([k, v]) => `${k}: ${[].concat(v).join(" ")}`).join("\n");
}

async function refreshAccess() {
  const tokens = getTokens();
  if (!tokens?.refresh) return false;
  const res = await fetch(`${CONFIG.API_BASE}/auth/refresh/`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: tokens.refresh }),
  });
  if (!res.ok) return false;
  saveTokens({ ...tokens, ...(await res.json()) });
  return true;
}

async function request(path, { method = "GET", json, form, auth = true, retry = true } = {}) {
  const headers = {};
  if (json) headers["Content-Type"] = "application/json";
  if (auth && getTokens()?.access) headers.Authorization = `Bearer ${getTokens().access}`;

  let res;
  try {
    res = await fetch(`${CONFIG.API_BASE}${path}`, { method, headers, body: form ?? (json ? JSON.stringify(json) : undefined) });
  } catch {
    throw new ApiError("Cannot reach the server. Check your connection.", 0);
  }

  if (res.status === 401 && auth && retry && (await refreshAccess())) {
    return request(path, { method, json, form, auth, retry: false });
  }
  if (res.status === 401 && auth) { clearTokens(); window.location.href = "login.html"; }
  if (res.status === 204) return null;

  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(readableError(body), res.status, body);
  return body;
}

const real = {
  register: (data) => request("/auth/register/", { method: "POST", json: data, auth: false }),
  login: (username, password) => request("/auth/login/", { method: "POST", json: { username, password }, auth: false }),
  me: () => request("/auth/me/"),

  createDetection: (file) => { const f = new FormData(); f.append("image", file); return request("/detections/", { method: "POST", form: f }); },
  listDetections: (page = 1) => request(`/detections/?page=${page}`),
  getDetection: (id) => request(`/detections/${id}/`),
  deleteDetection: (id) => request(`/detections/${id}/`, { method: "DELETE" }),
  detectionAdvice: (id, language) => request(`/detections/${id}/advice/`, { method: "POST", json: { language } }),

  weather: (city) => request(`/advisory/weather/?city=${encodeURIComponent(city)}`),
  advisory: (city, language) => request("/advisory/", { method: "POST", json: { city, language } }),
  health: () => request("/health/", { auth: false }),
};

export const api = CONFIG.USE_MOCK ? mock : real;

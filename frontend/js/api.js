// All HTTP calls live here. Pages never call fetch() directly.
// Keep function names and response shapes in sync with docs/API.md.
import { CONFIG, IS_LOCAL } from "./config.js";
import { clearTokens, getTokens, saveTokens } from "./auth.js";
import { mock } from "./mock.js";

// Render puts an idle backend to sleep and it takes up to a minute to wake. Knocking on its door as soon as any page
// opens means it is usually awake by the time the farmer logs in or picks a photo.
if (!IS_LOCAL && !CONFIG.USE_MOCK) fetch(`${CONFIG.API_BASE}/health/`).catch(() => {});

export class ApiError extends Error {
  constructor(message, status, details) { super(message); this.status = status; this.details = details; }
}

const FRIENDLY = {
  0: "Cannot reach the server. Check your internet connection and try again.",
  502: "An outside service did not answer. Please try again in a moment.",
  503: "This feature is temporarily unavailable. Please try again later.",
};

/** Turn DRF error bodies ({field: ["msg"]} or {detail: "msg"}) into one readable string. */
function readableError(body, status) {
  if (body?.detail) return body.detail;
  if (body && typeof body === "object") {
    const text = Object.entries(body).map(([k, v]) => `${k}: ${[].concat(v).join(" ")}`).join(" ");
    if (text) return text;
  }
  return FRIENDLY[status] || "Something went wrong. Please try again.";
}

async function refreshAccess() {
  const tokens = getTokens();
  if (!tokens?.refresh) return false;
  try {
    const res = await fetch(`${CONFIG.API_BASE}/auth/refresh/`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: tokens.refresh }),
    });
    if (!res.ok) return false;
    saveTokens({ ...tokens, ...(await res.json()) });
    return true;
  } catch { return false; }
}

function expireSession() {
  clearTokens();
  window.location.href = "login.html?expired=1";
}

async function request(path, { method = "GET", json, form, auth = true, retry = true } = {}) {
  const headers = {};
  if (json) headers["Content-Type"] = "application/json";
  if (auth && getTokens()?.access) headers.Authorization = `Bearer ${getTokens().access}`;

  let res;
  try {
    res = await fetch(`${CONFIG.API_BASE}${path}`, { method, headers, body: form ?? (json ? JSON.stringify(json) : undefined) });
  } catch {
    throw new ApiError(FRIENDLY[0], 0);
  }

  if (res.status === 401 && auth) {
    if (retry && (await refreshAccess())) return request(path, { method, json, form, auth, retry: false });
    expireSession();
    throw new ApiError("Your session has ended. Please sign in again.", 401);
  }
  if (res.status === 204) return null;

  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(readableError(body, res.status), res.status, body);
  return body;
}

/** Multipart upload with real progress events (fetch cannot report upload progress). */
function upload(path, form, onProgress, retry = true) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${CONFIG.API_BASE}${path}`);
    const token = getTokens()?.access;
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress?.(e.loaded / e.total); };
    xhr.onerror = xhr.ontimeout = () => reject(new ApiError(FRIENDLY[0], 0));
    xhr.onload = async () => {
      if (xhr.status === 401) {
        if (retry && (await refreshAccess())) return resolve(upload(path, form, onProgress, false));
        expireSession();
        return reject(new ApiError("Your session has ended. Please sign in again.", 401));
      }
      let body = null;
      try { body = JSON.parse(xhr.responseText); } catch { /* non-JSON error page */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body);
      else reject(new ApiError(readableError(body, xhr.status), xhr.status, body));
    };
    xhr.timeout = 120000;
    xhr.send(form);
  });
}

const real = {
  register: (data) => request("/auth/register/", { method: "POST", json: data, auth: false }),
  login: (username, password) => request("/auth/login/", { method: "POST", json: { username, password }, auth: false }),
  me: () => request("/auth/me/"),
  updateMe: (data) => request("/auth/me/", { method: "PATCH", json: data }),

  crops: () => request("/detections/crops/"),
  createDetection: (file, onProgress, crop = "auto") => { const f = new FormData(); f.append("image", file); f.append("crop", crop); return upload("/detections/", f, onProgress); },
  listDetections: (page = 1) => request(`/detections/?page=${page}`),
  getDetection: (id) => request(`/detections/${id}/`),
  deleteDetection: (id) => request(`/detections/${id}/`, { method: "DELETE" }),
  detectionAdvice: (id, language) => request(`/detections/${id}/advice/`, { method: "POST", json: { language } }),
  verifyDetection: (id, language) => request(`/detections/${id}/verify/`, { method: "POST", json: { language } }),

  weather: (city) => request(`/advisory/weather/?city=${encodeURIComponent(city)}`),
  advisory: (city, language) => request("/advisory/", { method: "POST", json: { city, language } }),
  assistantChat: (messages, language, context) => request("/assistant/chat/", { method: "POST", json: { messages, language, context } }),
  health: () => request("/health/", { auth: false }),
};

export const api = CONFIG.USE_MOCK ? mock : real;

// The ONLY place that knows where the backend lives.
export const CONFIG = {
  API_BASE: "http://127.0.0.1:8000/api",
  // true  = pages run on fake data from mock.js (no backend needed)
  // false = pages call the real Django API
  USE_MOCK: true,
};

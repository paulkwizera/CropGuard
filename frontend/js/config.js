// The ONLY place that knows where the backend lives.
const params = new URLSearchParams(location.search);
if (params.has("mock")) localStorage.setItem("cropguard.mock", params.get("mock") === "1" ? "1" : "0");

export const CONFIG = {
  API_BASE: "https://cropguarv1.onrender.com/api",
  // false (default) = pages talk to the real Django backend (run-backend.bat / run-backend.sh).
  // true  = demo mode with sample data and no backend: open any page with ?mock=1 (and ?mock=0 to leave it).
  USE_MOCK: localStorage.getItem("cropguard.mock") === "1",
};

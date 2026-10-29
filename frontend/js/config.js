// The ONLY place that knows where the backend lives.
const params = new URLSearchParams(location.search);
if (params.has("mock")) localStorage.setItem("cropguard.mock", params.get("mock") === "1" ? "1" : "0");

// Opened from your own computer (run-frontend.bat) -> talk to the backend on your computer.
// Opened from the internet (the Render website) -> talk to the Render backend.
export const IS_LOCAL = ["localhost", "127.0.0.1", ""].includes(location.hostname);
const LOCAL_API = "http://127.0.0.1:8000/api";
const LIVE_API = "https://cropguarv1.onrender.com/api";   // <- change this if the backend's Render address ever changes

export const CONFIG = {
  API_BASE: IS_LOCAL ? LOCAL_API : LIVE_API,
  // false (default) = pages talk to the real Django backend (run-backend.bat / run-backend.sh).
  // true  = demo mode with sample data and no backend: open any page with ?mock=1 (and ?mock=0 to leave it).
  USE_MOCK: localStorage.getItem("cropguard.mock") === "1",
};

// Inline SVG icon set (24x24, 1.75 stroke). One sprite is injected per page; use icon("name").
const PATHS = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1.5 1.5 0 0 1-1.5 1.5H15v-6.5H9v6.5H4.5A1.5 1.5 0 0 1 3 20z"/>',
  camera: '<path d="M3 8.5A1.5 1.5 0 0 1 4.5 7H8l1.6-2.5h4.8L16 7h3.5A1.5 1.5 0 0 1 21 8.5v10a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z"/><circle cx="12" cy="13" r="3.7"/>',
  history: '<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1L3.5 8.5"/><path d="M3.5 3.5v5h5"/><path d="M12 7.5V12l3 1.8"/>',
  cloud: '<path d="M17.5 18a4.5 4.5 0 0 0 .6-8.96A6 6 0 0 0 6.4 10.2 4 4 0 0 0 7 18z"/><path d="M8 21l1-2M12 21l1-2M16 21l1-2"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 20.5a8 8 0 0 1 16 0"/>',
  logout: '<path d="M9 20.5H5.5A1.5 1.5 0 0 1 4 19V5a1.5 1.5 0 0 1 1.5-1.5H9"/><path d="m16 16.5 4.5-4.5L16 7.5M20.5 12H9"/>',
  upload: '<path d="M4 15.5V19a1.5 1.5 0 0 0 1.5 1.5h13A1.5 1.5 0 0 0 20 19v-3.5"/><path d="m7.5 8.5 4.5-4.5 4.5 4.5M12 4v11.5"/>',
  image: '<rect x="3.5" y="3.5" width="17" height="17" rx="2"/><circle cx="9" cy="9" r="1.7"/><path d="m20.5 15.5-4.8-4.8L6 20.5"/>',
  trash: '<path d="M4 7h16M9.5 7V4.5h5V7M6.5 7l.8 12a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4l.8-12M10 11v5.5M14 11v5.5"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8 12.3 2.8 2.8L16 9.5"/>',
  alert: '<path d="M10.3 4.2 2.9 17.5A2 2 0 0 0 4.6 20.5h14.8a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/><path d="M12 9.5v4M12 17h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.8h.01"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  copy: '<rect x="8.5" y="8.5" width="12" height="12" rx="2"/><path d="M15.5 8.5V5.5a2 2 0 0 0-2-2h-8a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h3"/>',
  droplet: '<path d="M12 3.2s6.5 6.3 6.5 11a6.5 6.5 0 0 1-13 0c0-4.7 6.5-11 6.5-11z"/>',
  thermo: '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/>',
  wind: '<path d="M3 9h10.5a2.5 2.5 0 1 0-2.4-3.2M3 15h14a2.5 2.5 0 1 1-2.4 3.2M3 12h17a2.5 2.5 0 1 0-2.4-3.2"/>',
  leaf: '<path d="M5 19.5C4 12 8 5.5 20 4c.5 11-4.5 16-12.5 14.5"/><path d="M5 19.5C8 14.5 11.5 11.5 15 9.5"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-14.3-4.6L4 8.5"/><path d="M4 4v4.5h4.5M4 13a8 8 0 0 0 14.3 4.6L20 15.5"/><path d="M20 20v-4.5h-4.5"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.6 3.8 5.6 3.8 9s-1.2 6.4-3.8 9c-2.6-2.6-3.8-5.6-3.8-9S9.4 5.6 12 3z"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  arrow: '<path d="M4 12h16M14 6l6 6-6 6"/>',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
  "eye-off": '<path d="M3 3l18 18M10.6 5.7A9.6 9.6 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a16 16 0 0 1-3 3.8M6.5 7.2A15.6 15.6 0 0 0 2.5 12S6 18.5 12 18.5c1.5 0 2.9-.4 4.1-1M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
  sparkle: '<path d="M12 3.5 13.9 9l5.6 1.9-5.6 1.9L12 18.5l-1.9-5.7L4.5 11 10.1 9z"/>',
  chart: '<path d="M4 20V4M4 20h16"/><path d="M8.5 16v-4M13 16V8M17.5 16v-6"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
  phone: '<rect x="6.5" y="2.5" width="11" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
  message: '<path d="M20.5 15a2 2 0 0 1-2 2H8l-4.5 3.5V6a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z"/><path d="M8 9.5h8M8 12.5h5"/>',
  book: '<path d="M12 6.5C10.5 5 8 4.5 4 4.5v13c4 0 6.5.5 8 2 1.5-1.5 4-2 8-2v-13c-4 0-6.5.5-8 2zM12 6.5v13"/>',
  send: '<path d="M21 3 3 10.5l7 3 3 7z"/><path d="M21 3 10 13.5"/>',
  language: '<path d="M4 6h9M8.5 4v2M6 6c.4 3 2.5 5.6 5 7M12 6c-.6 3-3 6-7 8"/><path d="m13.5 20 3.6-9 3.6 9M14.7 17.2h4.8"/>',
};

export function icon(name, cls = "") {
  return `<svg class="icon ${cls}" aria-hidden="true" focusable="false"><use href="#i-${name}"/></svg>`;
}

export function injectSprite() {
  if (document.getElementById("icon-sprite")) return;
  const symbols = Object.entries(PATHS).map(([n, d]) => `<symbol id="i-${n}" viewBox="0 0 24 24">${d}</symbol>`).join("");
  document.body.insertAdjacentHTML("afterbegin", `<svg id="icon-sprite" width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">${symbols}</svg>`);
}

/** Brand mark: a leaf inside yellow viewfinder corners. */
export const BRAND_MARK = `<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">
  <path d="M5 11V6.5A1.5 1.5 0 0 1 6.5 5H11M21 5h4.5A1.5 1.5 0 0 1 27 6.5V11M27 21v4.5a1.5 1.5 0 0 1-1.5 1.5H21M11 27H6.5A1.5 1.5 0 0 1 5 25.5V21" fill="none" stroke="#f0b823" stroke-width="2.4" stroke-linecap="round"/>
  <path d="M10.5 21.5c-.8-5.7 2.6-10 11-11 .8 7.8-3.3 11.6-9 11.4-.7 0-1.4-.1-2-.4z" fill="#46a258"/>
  <path d="M10.8 21.2c2.4-3.3 5-5.6 8.2-7.2" fill="none" stroke="#14372a" stroke-opacity=".55" stroke-width="1.3" stroke-linecap="round"/>
</svg>`;

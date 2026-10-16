# CropGuard frontend

Plain HTML, CSS and JavaScript (ES modules). No build step, no npm, no framework.

## Run
**Do not open the .html files by double-clicking them.** Browsers block the page scripts on `file://` addresses, so the menu and sidebar never appear and the layout looks broken. Start the small local server instead:

- **Windows:** double-click `run-frontend.bat` in the project folder (needs Python installed).
- **Mac/Linux:** run `./run-frontend.sh` in the project folder.
- **Any system:** `cd frontend` then `python -m http.server 5500`, and open http://127.0.0.1:5500
- **VS Code:** the *Live Server* extension (right-click `index.html` → *Open with Live Server*) also works.

If a page ever shows a yellow "This page did not start" banner, it is this problem (or a missing file).

`js/config.js` starts with `USE_MOCK: true`, so every page works on sample data. Set it to `false` to use the Django API at `API_BASE`.
Add `?seed=1` to any URL in mock mode (for example `dashboard.html?seed=1`) to preload five sample checks.

## Pages
| File | Who sees it | What it does |
|------|-------------|--------------|
| `index.html` | everyone | Landing page |
| `login.html`, `register.html` | signed out | Accounts, inline validation, server errors shown on the right field |
| `dashboard.html` | signed in | Totals, recent checks, what was found, today's weather, getting-started list |
| `detect.html` | signed in | Take/choose photo, upload with progress, annotated result, AI treatment advice |
| `history.html` | signed in | Saved checks, filter and sort, details dialog, delete with confirmation |
| `advisory.html` | signed in | 24-hour forecast chart + AI weather advice |
| `account.html` | signed in | Edit district, language, email, phone; sign out |

## Folders
```
css/   tokens.css (colours, type, spacing)  base.css  layout.css (header, sidebar, tab bar)  components.css  pages.css
js/
  config.js  api.js  auth.js  session.js  mock.js
  components/  shell, icons, forms, dialog, toast, image, chart, format, lang, checks
  pages/       one script per page
assets/        fonts (self-hosted), favicon
```

## Languages (Kinyarwanda, English, Français)
- First visit: a prompt asks which language to use. Everyone can change it later with the globe switcher in the header, or on the Account page.
- The choice is stored on the device (`cropguard.lang`) and, when signed in, saved to the profile (`preferred_language`). It also sets the language of AI advice.
- **English text in the HTML and JavaScript is the source.** `js/i18n.js` looks each text up in `js/i18n/rw.js` and `js/i18n/fr.js` and swaps it. Text that JavaScript adds later is translated automatically.
- Sentences with changing values use `t("Showing {shown} of {total}", { shown, total })` and a matching dictionary key.
- **Adding or changing text:** write it in English where it is used, then add the same English string as a key to both dictionary files. In development, open the browser console and run `(await import("/js/i18n.js")).missing` to list text that still has no translation.
- The Kinyarwanda was written as a first draft: **have a native speaker review `js/i18n/rw.js` before launch.**
- Disease names come from the model, so they stay as the model names them. Add them to the dictionaries once the final class names are known.

## Pictures
Original illustrations in `assets/images/` (no stock photos): `step-*.svg` (landing steps), `seedling.svg` (empty states), `field-rows.svg` (sign-in panel and call-to-action band). The landing-page hero is an inline SVG in `index.html`. To use a real photograph instead, put it in `assets/images/` and point the matching `<img>` or CSS `url()` at it.

## Rules that keep it tidy
- **Only `api.js` calls the backend.** Names and response shapes follow `docs/API.md`. If an endpoint changes, change `api.js` and `mock.js` together.
- **Colours, fonts and spacing live in `css/tokens.css`.** Do not hard-code them in other files.
- **Every page** loads one script from `js/pages/`, which calls `mountShell("<page>")` (signed in) or `mountPublicHeader()` (public).
- **Never insert API text with `innerHTML` unescaped.** Use `escapeHtml()` or `renderAdvice()` from `components/format.js`.
- **Icons:** add a path to `components/icons.js`, use `icon("name")`.

## Design notes
- Palette: forest green `#14372a`, leaf green `#2b7d3b`, warm off-white `#f7f5ee`, charcoal `#1f2421`. The yellow `#f0b823` is reserved for the "detection frame" motif.
- Fonts: Bricolage Grotesque (headings) and Public Sans (text), both self-hosted from `assets/fonts` (SIL Open Font License; licences included).
- Layout: sidebar on screens 992px and wider, top bar + bottom tab bar below that.
- Photos are shrunk to at most 1600px on the phone before upload to save mobile data.
- Motion is limited to short transitions and respects `prefers-reduced-motion`.

## Needs from the backend
- `GET/PATCH /auth/me/` must accept `email`, `phone`, `district`, `preferred_language` (already in `docs/API.md`).
- Weather and AI advice need `OPENWEATHER_API_KEY` and `GOOGLE_API_KEY` in `.env`; the UI shows a clear message when they fail.

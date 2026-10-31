# CropGuard API contract

This file is the agreement between frontend and backend. **Change it in the same pull request as the code, and tell the other developer.**

- Base URL (development): `http://127.0.0.1:8000/api`
- Format: JSON, except image upload (`multipart/form-data`)
- Auth: `Authorization: Bearer <access token>` on every endpoint except register, login, refresh and health
- IDs are 24-character MongoDB ObjectId strings, e.g. `"6702f1c2a3b4c5d6e7f80912"`
- Dates are ISO 8601 (`2026-10-08T10:15:30+02:00`)
- Lists are paginated: `{ "count": 3, "next": null, "previous": null, "results": [...] }`
- Errors: `{ "detail": "message" }` or field errors `{ "username": ["A user with that username already exists."] }`

| Status | Meaning |
|--------|---------|
| 400 | Invalid input (see field errors) |
| 401 | Missing or expired token |
| 404 | Not found (or belongs to another user) |
| 502 | Weather or AI service failed |
| 503 | Model file missing on the server |

---

## Auth

### `POST /auth/register/`
```json
{ "username": "kwizera", "password": "min 8 chars", "district": "Musanze", "preferred_language": "rw" }
```
`email`, `phone`, `district`, `preferred_language` (`rw` | `en` | `fr`, default `rw`) are optional.
**201** → `{ "id", "username", "email", "phone", "district", "preferred_language" }`

### `POST /auth/login/`
`{ "username", "password" }` → **200** `{ "access": "...", "refresh": "..." }` (access lasts 60 min, refresh 7 days)

### `POST /auth/refresh/`
`{ "refresh": "..." }` → **200** `{ "access": "..." }`

### `GET /auth/me/` · `PATCH /auth/me/`
Returns / updates the current user: `{ "id", "username", "email", "phone", "district", "preferred_language", "date_joined" }`

---

## Detections

The detection object:
```json
{
  "id": "6702f1c2a3b4c5d6e7f80912",
  "crop": "maize",
  "status": "disease",
  "image": "http://127.0.0.1:8000/media/detections/2026/10/leaf.jpg",
  "image_width": 1280,
  "image_height": 960,
  "top_label": "Maize Leaf Blight",
  "top_confidence": 0.91,
  "results": [
    { "code": "MLB", "label": "Maize Leaf Blight", "confidence": 0.91, "bbox": [120.5, 80.0, 640.2, 500.9] }
  ],
  "advice": "",
  "created_at": "2026-10-08T10:15:30+02:00"
}
```
- `bbox` = `[x1, y1, x2, y2]` in **pixels of the original image** (`image_width` x `image_height`)
- `code` is the class stored in the model file (`MLB`, `MSV`); `label` is the readable name from `ml/labels.json` (what the farmer sees)
- `crop` is `maize` or `cassava` (see *crops* below)
- `status` is `disease` (a disease was found), `healthy` (the cassava model recognised a healthy leaf) or `none` (nothing detected). A disease always wins over a healthy region of the same photo. `top_label` is the headline result.
- Each result also has `healthy` (true for the healthy class)
- Nothing found above the confidence threshold → `status: "none"`, `results: []`, `top_label: ""`, `top_confidence: null`

### `GET /detections/crops/`
Which crops can be checked right now. A crop becomes `available` automatically when its weights file exists (`ml/weights/<crop>.pt`).
```json
[ { "id": "maize", "name": "Maize", "available": true }, { "id": "cassava", "name": "Cassava", "available": false } ]
```

### `POST /detections/` (multipart)
Field `image` (JPG/PNG, max 8 MB) and optional `crop` (`maize` default, or `cassava`). **201** → detection object. The model runs inside this request.
**503** `{ "detail": "The cassava detector is not available yet." }` when that crop's model file is missing.

### `GET /detections/?page=1`
Current user's detections, newest first.

### `GET /detections/{id}/` · `DELETE /detections/{id}/`
**200** detection object · **204** no body.

### `POST /detections/{id}/advice/`
`{ "language": "rw" }` (`rw` | `en` | `fr`) → **200** detection object with `advice` filled in.

### `POST /detections/{id}/advice/stream/`
Same body as `advice/`. Streams the advice (see below); the full text is saved on the detection when it ends.

**Streamed variant** (the page uses this so the answer appears while it is being written): same request body, answered as
Server-Sent Events (`text/event-stream`) instead of one JSON body:

```
event: chunk   data: {"t": "some new words"}                      (many times)
event: done    data: {"text": "the whole answer"}                 (once, at the end)
event: error   data: {"detail": "...", "code": "gemini_busy"}     (instead of done, if the AI failed)
```
Problems with the request itself (400 bad input, 401 not signed in, 429 too many requests) are normal JSON errors sent
before the stream starts. If streaming is unavailable, the page falls back to the non-streamed endpoint.
**400** unless `status` is `disease`.

---

## Advisory (weather + AI)

### `GET /advisory/weather/?city=Musanze`
```json
{
  "city": "Musanze",
  "total_rain_mm": 3.6,
  "avg_temp_c": 20.5,
  "readings": [
    { "datetime": "2026-10-08 00:00:00", "temp_c": 17.2, "humidity": 80, "description": "light rain", "wind_m_s": 2.1, "rain_mm": 1.2 }
  ]
}
```
`readings` = next 24 h in 3-hour steps (8 items).
`city` can be any of the 30 Rwandan districts (looked up by coordinates) or a nearby town name. An unknown place returns **404** `{ "detail": "..." }`.

### `POST /advisory/`
`{ "city": "Musanze", "language": "rw" }` → **200**
`{ "city", "language", "weather": { ...same as above without city... }, "advisory": "text written by the AI" }`

---

## Assistant (farming questions, Gemini)

### `POST /assistant/chat/`
The browser keeps the conversation and sends it each time; the server stores nothing.
```json
{
  "messages": [ { "role": "user", "content": "How can I get more maize from my field?" } ],
  "language": "rw",
  "context": { "district": "Musanze", "crop": "maize", "last_check": "Maize Streak Virus" }
}
```
- `messages`: 1–40 items, `role` is `user` or `assistant`, `content` max 2000 characters; the **last** message must be from the user (only the latest 12 are sent to the model)
- `language`: `rw` | `en` | `fr` (default `rw`); `context` is optional
- **200** → `{ "reply": "text written by the AI", "language": "rw" }`
- **400** invalid input · **429** too many questions (default 30 per minute per user, `ASSISTANT_RATE`) · **502** the AI service failed

---

## Health


### `POST /assistant/chat/stream/`
Same body as `chat/`; streamed as events (same format as `advice/stream/`).

### `GET /health/` (no auth)
`{ "status": "ok", "mongodb": "ok" }`

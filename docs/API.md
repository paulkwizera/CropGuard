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
  "image": "http://127.0.0.1:8000/media/detections/2026/10/leaf.jpg",
  "image_width": 1280,
  "image_height": 960,
  "top_label": "Northern Leaf Blight",
  "top_confidence": 0.91,
  "results": [
    { "label": "Northern Leaf Blight", "confidence": 0.91, "bbox": [120.5, 80.0, 640.2, 500.9] }
  ],
  "advice": "",
  "created_at": "2026-10-08T10:15:30+02:00"
}
```
- `bbox` = `[x1, y1, x2, y2]` in **pixels of the original image** (`image_width` x `image_height`)
- Nothing found above the confidence threshold → `results: []`, `top_label: ""`, `top_confidence: null`

### `POST /detections/` (multipart)
Field `image` (JPG/PNG, max 8 MB). **201** → detection object. The model runs inside this request.

### `GET /detections/?page=1`
Current user's detections, newest first.

### `GET /detections/{id}/` · `DELETE /detections/{id}/`
**200** detection object · **204** no body.

### `POST /detections/{id}/advice/`
`{ "language": "rw" }` (`rw` | `en` | `fr`) → **200** detection object with `advice` filled in.
**400** if nothing was detected.

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

### `POST /advisory/`
`{ "city": "Musanze", "language": "rw" }` → **200**
`{ "city", "language", "weather": { ...same as above without city... }, "advisory": "text written by the AI" }`

---

## Health

### `GET /health/` (no auth)
`{ "status": "ok", "mongodb": "ok" }`

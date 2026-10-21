"""Approximate coordinates (latitude, longitude) of Rwanda's 30 districts.

OpenWeatherMap's city search does not know most district names (Gasabo, Kicukiro,
Nyarugenge, ...), so the forecast is requested by coordinates instead. Each point is
the district's main town or centre, which is accurate enough for a 3-hour forecast.
The list matches DISTRICTS in frontend/js/components/format.js.
"""

DISTRICT_COORDS: dict[str, tuple[float, float]] = {
    "Bugesera": (-2.1500, 30.0833),
    "Burera": (-1.4500, 29.8500),
    "Gakenke": (-1.6833, 29.7833),
    "Gasabo": (-1.9000, 30.1000),
    "Gatsibo": (-1.6000, 30.4333),
    "Gicumbi": (-1.5767, 30.0678),
    "Gisagara": (-2.6000, 29.8333),
    "Huye": (-2.6000, 29.7390),
    "Kamonyi": (-1.9833, 29.9000),
    "Karongi": (-2.0600, 29.3500),
    "Kayonza": (-1.8833, 30.6333),
    "Kicukiro": (-1.9800, 30.1000),
    "Kirehe": (-2.2700, 30.7000),
    "Muhanga": (-2.0833, 29.7500),
    "Musanze": (-1.4994, 29.6347),
    "Ngoma": (-2.1500, 30.5333),
    "Ngororero": (-1.8667, 29.6333),
    "Nyabihu": (-1.6500, 29.5000),
    "Nyagatare": (-1.2975, 30.3275),
    "Nyamagabe": (-2.4667, 29.5667),
    "Nyamasheke": (-2.3333, 29.1333),
    "Nyanza": (-2.3500, 29.7500),
    "Nyarugenge": (-1.9500, 30.0600),
    "Nyaruguru": (-2.6000, 29.5500),
    "Rubavu": (-1.7000, 29.2600),
    "Ruhango": (-2.2333, 29.7833),
    "Rulindo": (-1.7667, 30.0000),
    "Rusizi": (-2.4833, 28.9000),
    "Rutsiro": (-1.9500, 29.3500),
    "Rwamagana": (-1.9500, 30.4333),
}

_BY_LOWER = {name.lower(): coords for name, coords in DISTRICT_COORDS.items()}


def coords_for(place: str) -> tuple[float, float] | None:
    """Coordinates for a district name (case-insensitive, optional ' District'), else None."""
    key = place.strip().lower()
    if key.endswith(" district"):
        key = key[: -len(" district")].strip()
    return _BY_LOWER.get(key)

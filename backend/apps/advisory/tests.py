from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.core.exceptions import PlaceNotFound

from .services.districts import DISTRICT_COORDS, coords_for
from .services.weather import fetch_forecast, summarize_forecast

RAW = {
    "list": [
        {
            "dt_txt": f"2026-10-08 {h:02d}:00:00",
            "main": {"temp": 20 + i, "humidity": 70},
            "weather": [{"description": "light rain"}],
            "wind": {"speed": 2.0},
            **({"rain": {"3h": 1.5}} if i % 2 == 0 else {}),
        }
        for i, h in enumerate(range(0, 24, 3))
    ]
}


class SummarizeForecastTests(SimpleTestCase):
    def test_summary(self):
        s = summarize_forecast(RAW)
        self.assertEqual(len(s["readings"]), 8)
        self.assertEqual(s["total_rain_mm"], 6.0)
        self.assertEqual(s["avg_temp_c"], 23.5)


class DistrictLookupTests(SimpleTestCase):
    def test_all_30_districts_have_coordinates_inside_rwanda(self):
        self.assertEqual(len(DISTRICT_COORDS), 30)
        for name, (lat, lon) in DISTRICT_COORDS.items():
            self.assertTrue(-3.0 < lat < -1.0 and 28.8 < lon < 31.0, name)

    def test_lookup_is_forgiving(self):
        self.assertEqual(coords_for("gasabo"), DISTRICT_COORDS["Gasabo"])
        self.assertEqual(coords_for("  Musanze District "), DISTRICT_COORDS["Musanze"])
        self.assertIsNone(coords_for("Paris"))


@override_settings(OPENWEATHER_API_KEY="test-key")
class FetchForecastTests(SimpleTestCase):
    @patch("apps.advisory.services.weather.requests.get")
    def test_district_uses_coordinates(self, get):
        get.return_value = MagicMock(status_code=200, json=lambda: {"list": []})
        fetch_forecast("Gasabo")
        params = get.call_args.kwargs["params"]
        self.assertEqual((params["lat"], params["lon"]), DISTRICT_COORDS["Gasabo"])
        self.assertNotIn("q", params)

    @patch("apps.advisory.services.weather.requests.get")
    def test_other_place_uses_name_search(self, get):
        get.return_value = MagicMock(status_code=200, json=lambda: {"list": []})
        fetch_forecast("Gisenyi")
        self.assertEqual(get.call_args.kwargs["params"]["q"], "Gisenyi,RW")

    @patch("apps.advisory.services.weather.requests.get")
    def test_unknown_place_is_404_not_502(self, get):
        get.return_value = MagicMock(status_code=404)
        with self.assertRaises(PlaceNotFound) as ctx:
            fetch_forecast("Nowhereville")
        self.assertEqual(ctx.exception.status_code, 404)

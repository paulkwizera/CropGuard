from django.test import SimpleTestCase

from .services.weather import summarize_forecast

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

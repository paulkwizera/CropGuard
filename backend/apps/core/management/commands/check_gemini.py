"""
python manage.py check_gemini            quick test of the first model that works
python manage.py check_gemini --all      test every configured model (GEMINI_MODEL + GEMINI_FALLBACK_MODELS)
python manage.py check_gemini --image    also test sending a photo (what the second opinion does)

Run it after changing GOOGLE_API_KEY or GEMINI_MODEL. It prints exactly what is wrong, in plain words.
"""
from django.core.management.base import BaseCommand

from apps.core import gemini


class Command(BaseCommand):
    help = "Test the Gemini connection (key, model, speed) and explain any problem."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="test every configured model")
        parser.add_argument("--image", action="store_true", help="also test a photo request")

    def handle(self, *args, **opts):
        report = gemini.diagnose(all_models=opts["all"], with_image=opts["image"])
        out = self.stdout.write
        out(f"API key     : {report['key_format']}, {report['key_length']} characters")
        out(f"SDK         : google-genai {report['sdk_version']}")
        out(f"Model       : {report['model']}   (fallbacks: {', '.join(report['fallbacks']) or 'none'})")
        out(f"Thinking    : {report['thinking'] or 'model default'}")
        for row in report["checks"]:
            if row["ok"]:
                out(self.style.SUCCESS(f"  OK    {row['model']:<24} {row['ms']} ms  -> {row.get('answer', '')}"))
            else:
                out(self.style.ERROR(f"  FAIL  {row['model']:<24} {row['ms']} ms  [{row['kind']}] {row.get('error', '')}"))
        out("")
        out((self.style.SUCCESS if report["ok"] else self.style.ERROR)(report["hint"]))

import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from . import crops

from apps.accounts.models import User


def fake_image():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "green").save(buf, "JPEG")
    return SimpleUploadedFile("leaf.jpg", buf.getvalue(), content_type="image/jpeg")


FAKE_OUTCOME = {
    "width": 64,
    "height": 64,
    "results": [{"code": "MLB", "label": "Maize Leaf Blight", "healthy": False, "confidence": 0.91, "bbox": [1, 2, 30, 40]}],
}


class DetectionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("farmer", password="Str0ng-pass!")
        self.client.force_authenticate(self.user)

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/detections/").status_code, 401)

    @patch("apps.detection.views.yolo.predict", return_value=FAKE_OUTCOME)
    def test_upload_and_list(self, _predict):
        r = self.client.post("/api/detections/", {"image": fake_image()}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["top_label"], "Maize Leaf Blight")
        self.assertEqual(r.data["crop"], "maize")
        self.assertEqual(r.data["status"], "disease")

        r = self.client.get("/api/detections/")
        self.assertEqual(r.data["count"], 1)


class CropRegistryTests(SimpleTestCase):
    def test_labels_are_readable_and_unknown_codes_pass_through(self):
        crops._labels.cache_clear()
        self.assertEqual(crops.display_label("maize", "MLB"), "Maize Leaf Blight")
        self.assertEqual(crops.display_label("maize", "MSV"), "Maize Streak Virus")
        self.assertEqual(crops.display_label("maize", "XYZ"), "XYZ")

    def test_maize_model_file_is_in_the_repo(self):
        self.assertTrue(crops.is_available("maize"), crops.model_path("maize"))

    def test_both_crops_are_listed(self):
        listing = {c["id"]: c for c in crops.list_crops()}
        self.assertEqual(set(listing), {"maize", "cassava"})
        self.assertTrue(listing["cassava"]["available"], crops.model_path("cassava"))

    def test_cassava_labels_and_the_healthy_class(self):
        self.assertEqual(crops.display_label("cassava", "Cassava_Mosaic Disease"), "Cassava Mosaic Disease")
        self.assertEqual(crops.display_label("cassava", "Healthy"), "Healthy cassava leaf")
        self.assertTrue(crops.is_healthy("cassava", "Healthy"))
        self.assertFalse(crops.is_healthy("cassava", "Cassava_Green Mottle"))
        self.assertFalse(crops.is_healthy("maize", "MLB"))

    def test_a_crop_without_a_weights_file_is_coming_soon(self):
        models = {"maize": {"name": "Maize", "path": crops.model_path("maize")}, "cassava": {"name": "Cassava", "path": crops.model_path("cassava").with_name("not-trained-yet.pt")}}
        with override_settings(CROP_MODELS=models):
            listing = {c["id"]: c for c in crops.list_crops()}
            self.assertFalse(listing["cassava"]["available"])
            self.assertTrue(listing["maize"]["available"])

    def test_cassava_switches_on_when_the_weights_appear(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            weights = Path(d) / "cassava.pt"
            weights.write_bytes(b"x")
            models = {"maize": {"name": "Maize", "path": Path(d) / "nope.pt"}, "cassava": {"name": "Cassava", "path": weights}}
            with override_settings(CROP_MODELS=models):
                self.assertTrue(crops.is_available("cassava"))
                self.assertFalse(crops.is_available("maize"))


class SummarizeTests(SimpleTestCase):
    def test_disease_beats_healthy_even_with_lower_confidence(self):
        from .views import summarize

        results = [{"label": "Healthy cassava leaf", "healthy": True, "confidence": 0.9}, {"label": "Cassava Mosaic Disease", "healthy": False, "confidence": 0.6}]
        status, top = summarize(results)
        self.assertEqual((status, top["label"]), ("disease", "Cassava Mosaic Disease"))

    def test_healthy_only_and_nothing(self):
        from .views import summarize

        self.assertEqual(summarize([{"label": "Healthy cassava leaf", "healthy": True, "confidence": 0.8}])[0], "healthy")
        self.assertEqual(summarize([]), ("none", None))

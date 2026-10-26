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


CASSAVA_OUTCOME = {
    "crop": "cassava",
    "width": 64,
    "height": 64,
    "results": [{"code": "Cassava_Mosaic Disease", "label": "Cassava Mosaic Disease", "healthy": False, "confidence": 0.88, "bbox": [0, 0, 64, 64]}],
}


class DetectionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("farmer", password="Str0ng-pass!")
        self.client.force_authenticate(self.user)

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/detections/").status_code, 401)

    @patch("apps.detection.views.yolo.predict_auto", return_value={**FAKE_OUTCOME, "crop": "maize"})
    def test_upload_and_list(self, _predict):
        # No crop sent -> "auto": the server works the crop out from the photo.
        r = self.client.post("/api/detections/", {"image": fake_image()}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["top_label"], "Maize Leaf Blight")
        self.assertEqual(r.data["crop"], "maize")
        self.assertEqual(r.data["status"], "disease")

        r = self.client.get("/api/detections/")
        self.assertEqual(r.data["count"], 1)

    @patch("apps.detection.views.yolo.predict_auto", return_value=CASSAVA_OUTCOME)
    def test_auto_saves_the_crop_the_photo_turned_out_to_be(self, _predict):
        r = self.client.post("/api/detections/", {"image": fake_image(), "crop": "auto"}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["crop"], "cassava")
        self.assertEqual(r.data["top_label"], "Cassava Mosaic Disease")

    @patch("apps.detection.views.yolo.predict_auto")
    @patch("apps.detection.views.yolo.predict", return_value=CASSAVA_OUTCOME)
    def test_a_chosen_crop_is_respected_and_skips_auto(self, predict, predict_auto):
        r = self.client.post("/api/detections/", {"image": fake_image(), "crop": "cassava"}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["crop"], "cassava")
        self.assertEqual(predict.call_args.args[1], "cassava")
        predict_auto.assert_not_called()

    def test_unknown_crop_is_rejected(self):
        r = self.client.post("/api/detections/", {"image": fake_image(), "crop": "banana"}, format="multipart")
        self.assertEqual(r.status_code, 400)


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


def _found(code, label, confidence, healthy=False):
    return {"code": code, "label": label, "healthy": healthy, "confidence": confidence, "bbox": [0, 0, 10, 10]}


class AutoCropTests(SimpleTestCase):
    """predict_auto asks every available model and trusts the one that is most sure."""

    def run_auto(self, per_crop, conf=0.5, available=("maize", "cassava")):
        from .services import yolo

        def fake_predict(path, crop, conf=None):
            found = [r for r in per_crop.get(crop, []) if r["confidence"] >= (conf or 0)]
            return {"width": 100, "height": 80, "results": sorted(found, key=lambda r: -r["confidence"])}

        with patch.object(yolo, "predict", side_effect=fake_predict), \
                patch.object(crops, "is_available", side_effect=lambda c: c in available), \
                override_settings(YOLO_CONF=conf):
            return yolo.predict_auto("leaf.jpg")

    def test_a_cassava_leaf_is_not_read_as_maize(self):
        # The maize model has to answer with one of its two diseases, but only weakly; cassava is sure.
        out = self.run_auto({
            "maize": [_found("MSV", "Maize Streak Virus", 0.31)],
            "cassava": [_found("Cassava_Mosaic Disease", "Cassava Mosaic Disease", 0.93)],
        })
        self.assertEqual(out["crop"], "cassava")
        self.assertEqual(out["results"][0]["label"], "Cassava Mosaic Disease")

    def test_a_maize_leaf_is_not_read_as_cassava(self):
        out = self.run_auto({
            "maize": [_found("MLB", "Maize Leaf Blight", 0.95)],
            "cassava": [_found("Healthy", "Healthy cassava leaf", 0.40, healthy=True)],
        })
        self.assertEqual(out["crop"], "maize")
        self.assertEqual([r["label"] for r in out["results"]], ["Maize Leaf Blight"])

    def test_only_the_winning_crops_detections_above_the_threshold_are_reported(self):
        out = self.run_auto({
            "maize": [_found("MLB", "Maize Leaf Blight", 0.9), _found("MSV", "Maize Streak Virus", 0.2)],
            "cassava": [_found("Healthy", "Healthy cassava leaf", 0.3, healthy=True)],
        })
        self.assertEqual([r["label"] for r in out["results"]], ["Maize Leaf Blight"])
        self.assertEqual(out["scores"], {"maize": 0.9, "cassava": 0.3})

    def test_nothing_confident_gives_no_results_but_still_names_the_likelier_crop(self):
        out = self.run_auto({
            "maize": [_found("MSV", "Maize Streak Virus", 0.12)],
            "cassava": [_found("Cassava_Green Mottle", "Cassava Green Mottle", 0.25)],
        })
        self.assertEqual(out["crop"], "cassava")
        self.assertEqual(out["results"], [])

    def test_with_one_model_available_only_that_one_runs(self):
        out = self.run_auto({"maize": [_found("MLB", "Maize Leaf Blight", 0.8)]}, available=("maize",))
        self.assertEqual((out["crop"], list(out["scores"])), ("maize", ["maize"]))

    def test_no_models_at_all_is_a_clear_error(self):
        from apps.core.exceptions import ServiceUnavailable

        with self.assertRaises(ServiceUnavailable):
            self.run_auto({}, available=())

import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from . import crops

from apps.accounts.models import User
from apps.core.exceptions import ExternalServiceError


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


GEMINI_SEES_CASSAVA = {
    "verdict": "disagree", "crop": "cassava", "condition": "Cassava Mosaic Disease", "certainty": "high",
    "explanation": "Yellow and green patches distort the leaf.", "language": "en", "model": "test",
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

    @patch("apps.detection.views.yolo.predict", return_value=CASSAVA_OUTCOME)
    @patch("apps.detection.views.advisor.verify_detection", return_value=GEMINI_SEES_CASSAVA)
    @patch("apps.detection.views.yolo.predict_auto", return_value={**FAKE_OUTCOME, "crop": "maize"})
    def test_verify_picks_one_final_answer_and_saves_it(self, _auto, verify, rerun):
        # The detector called a cassava leaf "Maize Leaf Blight"; Gemini sees cassava -> the cassava detector re-checks.
        created = self.client.post("/api/detections/", {"image": fake_image()}, format="multipart").data
        self.assertEqual((created["crop"], created["top_label"], created["verification"]), ("maize", "Maize Leaf Blight", {}))
        url = f"/api/detections/{created['id']}/verify/"

        r = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.data["crop"], r.data["top_label"]), ("cassava", "Cassava Mosaic Disease"))
        self.assertEqual(r.data["top_confidence"], 0.88)
        res = r.data["verification"]["resolution"]
        self.assertEqual((res["winner"], res["basis"], res["crop_changed"]), ("detector", "confirmed", True))
        self.assertEqual(res["detector"]["top_label"], "Maize Leaf Blight")   # what the detector first said is kept
        self.assertEqual(verify.call_args.args[1]["crop"], "maize")           # Gemini was told the detector's answer
        self.assertEqual(rerun.call_args.args[1], "cassava")

        # the decision is made once: asking again (even in another language) gives the same answer, no new Gemini call
        again = self.client.post(url, {"language": "fr"}, format="json").data
        self.assertEqual(again["top_label"], "Cassava Mosaic Disease")
        self.assertEqual(verify.call_count, 1)
        saved = self.client.get(f"/api/detections/{created['id']}/").data
        self.assertEqual((saved["crop"], saved["top_label"]), ("cassava", "Cassava Mosaic Disease"))

    @patch("apps.detection.views.advisor.verify_detection", side_effect=ExternalServiceError("down"))
    @patch("apps.detection.views.yolo.predict_auto", return_value=CASSAVA_OUTCOME)
    def test_verify_failure_is_a_clean_error_and_the_check_itself_is_untouched(self, _predict, _verify):
        created = self.client.post("/api/detections/", {"image": fake_image()}, format="multipart").data
        r = self.client.post(f"/api/detections/{created['id']}/verify/", {"language": "en"}, format="json")
        self.assertEqual(r.status_code, 502)
        saved = self.client.get(f"/api/detections/{created['id']}/").data
        self.assertEqual(saved["top_label"], "Cassava Mosaic Disease")
        self.assertEqual(saved["verification"], {})


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


class SecondOpinionTests(SimpleTestCase):
    """advisor.judge turns Gemini's raw answer into a verdict; Gemini never gets to pick the verdict itself."""

    MSV = {"crop": "maize", "status": "disease", "top_label": "Maize Streak Virus", "top_confidence": 0.62}
    MOSAIC = {"crop": "cassava", "status": "disease", "top_label": "Cassava Mosaic Disease", "top_confidence": 0.9}

    def judge(self, facts, **answer):
        from apps.advisory.services import advisor

        answer = {"certainty": "high", "explanation": "x", **answer}
        with patch.object(crops, "is_available", return_value=True):
            return advisor.judge(facts, answer, "en")

    def test_agrees_when_crop_and_condition_match(self):
        self.assertEqual(self.judge(self.MOSAIC, crop="cassava", condition="Cassava Mosaic Disease")["verdict"], "agree")

    def test_a_cassava_leaf_the_detector_called_maize_is_a_disagreement(self):
        self.assertEqual(self.judge(self.MSV, crop="cassava", condition="Cassava Mosaic Disease")["verdict"], "disagree")

    def test_same_crop_different_disease_disagrees(self):
        self.assertEqual(self.judge(self.MOSAIC, crop="cassava", condition="Cassava Green Mottle")["verdict"], "disagree")

    def test_a_healthy_verdict_needs_gemini_to_see_a_healthy_leaf_of_the_same_crop(self):
        facts = {"crop": "cassava", "status": "healthy", "top_label": "Healthy cassava leaf", "top_confidence": 0.8}
        self.assertEqual(self.judge(facts, crop="cassava", condition="Healthy cassava leaf")["verdict"], "agree")
        self.assertEqual(self.judge(facts, crop="cassava", condition="Cassava Bacterial Blight")["verdict"], "disagree")

    def test_when_the_detector_found_nothing_gemini_agrees_only_if_it_sees_no_problem_either(self):
        facts = {"crop": "maize", "status": "none", "top_label": "", "top_confidence": None}
        self.assertEqual(self.judge(facts, crop="maize", condition="Healthy maize leaf")["verdict"], "agree")
        missed = self.judge(facts, crop="maize", condition="Maize Leaf Blight")
        self.assertEqual(missed["verdict"], "disagree")

    def test_a_low_certainty_answer_is_never_a_disagreement(self):
        self.assertEqual(self.judge(self.MSV, crop="cassava", condition="Cassava Mosaic Disease", certainty="low")["verdict"], "unsure")

    def test_not_a_leaf_and_another_plant_have_their_own_verdicts(self):
        self.assertEqual(self.judge(self.MSV, crop="not_a_plant", condition="Cannot tell")["verdict"], "not_leaf")
        self.assertEqual(self.judge(self.MSV, crop="other_plant", condition="Cannot tell")["verdict"], "other_crop")

    def test_invented_values_are_clamped_to_unsure_and_the_explanation_is_tidied(self):
        v = self.judge(self.MSV, crop="banana", condition="Banana Wilt", certainty="very sure", explanation="  a \n b  " + "z" * 900)
        self.assertEqual((v["verdict"], v["crop"], v["condition"], v["certainty"]), ("unsure", "unclear", "Cannot tell", "low"))
        self.assertTrue(v["explanation"].startswith("a b z"))
        self.assertLessEqual(len(v["explanation"]), 500)

    def test_the_plant_name_is_kept_only_for_another_plant_and_made_harmless(self):
        v = self.judge(self.MSV, crop="other_plant", condition="Cannot tell", plant_name="  Tomato <b>plant</b>; DROP TABLE  ")
        self.assertEqual((v["verdict"], v["plant_name"]), ("other_crop", "tomato bplantb drop table"))
        self.assertEqual(self.judge(self.MSV, crop="cassava", condition="Cassava Mosaic Disease", plant_name="tomato")["plant_name"], "")
        self.assertEqual(self.judge(self.MSV, crop="other_plant", condition="Cannot tell", plant_name="x" * 90)["plant_name"], "x" * 40)

    def test_a_condition_from_the_wrong_crop_is_not_accepted(self):
        v = self.judge(self.MSV, crop="cassava", condition="Maize Leaf Blight")  # not a cassava condition
        self.assertEqual((v["condition"], v["verdict"]), ("Cannot tell", "unsure"))

    def test_a_disease_name_from_gemini_is_kept_only_for_another_problem_and_made_harmless(self):
        v = self.judge(self.MSV, crop="maize", condition="Other problem", problem_name="  gray leaf <b>spot</b>; DROP TABLE  ")
        self.assertEqual((v["verdict"], v["problem_name"]), ("disagree", "Gray leaf bspotb DROP TABLE"))
        self.assertEqual(self.judge(self.MSV, crop="maize", condition="Maize Leaf Blight", problem_name="Gray leaf spot")["problem_name"], "")
        self.assertEqual(self.judge(self.MSV, crop="maize", condition="Other problem", problem_name="x" * 90)["problem_name"], "X" + "x" * 59)

    def test_useless_or_already_known_names_are_dropped(self):
        for name in ("", "unknown", "Other problem", "Cannot tell", "Maize Leaf Blight", None):
            self.assertEqual(self.judge(self.MSV, crop="maize", condition="Other problem", problem_name=name)["problem_name"], "", name)

    def test_the_prompt_asks_gemini_to_name_a_problem_the_app_does_not_know(self):
        from apps.advisory.services import advisor

        self.assertIn('"problem_name"', advisor.build_verify_prompt(self.MSV, "en"))

    def test_json_parsing_accepts_fences_and_lists_and_rejects_junk(self):
        from apps.advisory.services import advisor

        self.assertEqual(advisor._parse_json('```json\n{"crop": "maize"}\n```'), {"crop": "maize"})
        self.assertEqual(advisor._parse_json('[{"crop": "maize"}]'), {"crop": "maize"})
        with self.assertRaises(ExternalServiceError):
            advisor._parse_json("I think it is maize")

    def test_the_prompt_tells_gemini_what_the_detector_said_and_to_not_trust_it(self):
        from apps.advisory.services import advisor

        prompt = advisor.build_verify_prompt(self.MSV, "fr")
        self.assertIn('"Maize Streak Virus" (62% sure)', prompt)
        self.assertIn("French", prompt)
        self.assertIn("do NOT assume", prompt)
        for name in ("Maize Leaf Blight", "Healthy maize leaf", "Cassava Mosaic Disease", "Healthy cassava leaf"):
            self.assertIn(name, prompt)


class DecisionTests(SimpleTestCase):
    """decision.decide picks ONE final answer. Crop identity is Gemini's call; the disease is the detector's unless weak."""

    def detector(self, crop="maize", label="Maize Streak Virus", confidence=0.62, status="disease"):
        results = [{"label": label, "confidence": confidence, "healthy": status == "healthy", "bbox": [0, 0, 5, 5]}] if label else []
        return {"crop": crop, "status": status, "top_label": label, "top_confidence": confidence if label else None, "results": results}

    def gemini(self, crop, condition, certainty="high", verdict="disagree"):
        return {"verdict": verdict, "crop": crop, "condition": condition, "certainty": certainty, "explanation": "x"}

    def decide(self, detector, gemini, rerun=None, trust=0.80):
        from .services import decision

        with override_settings(VERIFY_DETECTOR_TRUST=trust):
            return decision.decide(detector, gemini, rerun or (lambda crop: None))

    def cassava_rerun(self, label="Cassava Mosaic Disease", confidence=0.9):
        return lambda crop: [{"label": label, "confidence": confidence, "healthy": False, "bbox": [0, 0, 9, 9]}]

    def test_agreement_confirms_the_detectors_answer(self):
        out = self.decide(self.detector(), self.gemini("maize", "Maize Streak Virus", verdict="agree"))
        self.assertEqual((out["resolution"]["winner"], out["resolution"]["basis"]), ("detector", "confirmed"))
        self.assertEqual(out["final"]["top_label"], "Maize Streak Virus")

    def test_an_unsure_gemini_leaves_the_detector_unconfirmed(self):
        out = self.decide(self.detector(), self.gemini("unclear", "Cannot tell", "low", "unsure"))
        self.assertEqual((out["resolution"]["winner"], out["resolution"]["basis"]), ("detector", "unconfirmed"))

    def test_a_cassava_leaf_called_maize_is_rechecked_by_the_cassava_detector(self):
        out = self.decide(self.detector(), self.gemini("cassava", "Cassava Mosaic Disease"), self.cassava_rerun())
        self.assertEqual(out["final"]["crop"], "cassava")
        self.assertEqual((out["final"]["top_label"], out["final"]["top_confidence"]), ("Cassava Mosaic Disease", 0.9))
        self.assertTrue(out["final"]["results"])  # the new detector's box is kept
        self.assertEqual(
            (out["resolution"]["winner"], out["resolution"]["basis"], out["resolution"]["crop_changed"]),
            ("detector", "confirmed", True),
        )
        self.assertEqual(out["resolution"]["detector"]["top_label"], "Maize Streak Virus")

    def test_after_a_crop_fix_a_sure_detector_beats_gemini_on_which_disease(self):
        out = self.decide(self.detector(), self.gemini("cassava", "Cassava Mosaic Disease"), self.cassava_rerun("Cassava Green Mottle", 0.93))
        self.assertEqual((out["final"]["crop"], out["final"]["top_label"]), ("cassava", "Cassava Green Mottle"))
        self.assertEqual((out["resolution"]["winner"], out["resolution"]["basis"]), ("detector", "detector_more_certain"))

    def test_after_a_crop_fix_with_nothing_found_a_highly_certain_gemini_names_the_disease(self):
        out = self.decide(self.detector(), self.gemini("cassava", "Cassava Mosaic Disease"), lambda crop: [])
        self.assertEqual((out["final"]["crop"], out["final"]["top_label"], out["final"]["top_confidence"]), ("cassava", "Cassava Mosaic Disease", None))
        self.assertEqual(out["final"]["results"], [])
        self.assertEqual((out["resolution"]["winner"], out["resolution"]["basis"], out["resolution"]["crop_changed"]), ("gemini", "gemini_more_certain", True))

    def test_after_a_crop_fix_with_nothing_found_a_medium_gemini_does_not_invent_a_disease(self):
        out = self.decide(self.detector(), self.gemini("cassava", "Cassava Mosaic Disease", "medium"), lambda crop: [])
        self.assertEqual((out["final"]["crop"], out["final"]["status"], out["final"]["top_label"]), ("cassava", "none", ""))
        self.assertEqual(out["resolution"]["basis"], "unconfirmed")

    def test_if_the_other_detector_cannot_run_gemini_decides_when_highly_certain(self):
        out = self.decide(self.detector(), self.gemini("cassava", "Cassava Mosaic Disease"), lambda crop: None)
        self.assertEqual((out["final"]["crop"], out["final"]["top_label"]), ("cassava", "Cassava Mosaic Disease"))
        self.assertEqual(out["resolution"]["winner"], "gemini")

    def test_same_crop_a_weak_detector_loses_to_a_highly_certain_gemini(self):
        out = self.decide(self.detector("cassava", "Cassava Green Mottle", 0.55), self.gemini("cassava", "Cassava Mosaic Disease"))
        self.assertEqual((out["final"]["top_label"], out["final"]["top_confidence"]), ("Cassava Mosaic Disease", None))
        self.assertEqual((out["resolution"]["winner"], out["resolution"]["basis"]), ("gemini", "gemini_more_certain"))
        self.assertFalse(out["resolution"]["crop_changed"])

    def test_same_crop_a_sure_detector_beats_even_a_highly_certain_gemini(self):
        out = self.decide(self.detector("cassava", "Cassava Green Mottle", 0.95), self.gemini("cassava", "Cassava Mosaic Disease"))
        self.assertEqual(out["final"]["top_label"], "Cassava Green Mottle")
        self.assertEqual((out["resolution"]["winner"], out["resolution"]["basis"]), ("detector", "detector_more_certain"))

    def test_the_trust_level_is_configurable(self):
        d, g = self.detector("cassava", "Cassava Green Mottle", 0.85), self.gemini("cassava", "Cassava Mosaic Disease")
        self.assertEqual(self.decide(d, g, trust=0.80)["resolution"]["winner"], "detector")
        self.assertEqual(self.decide(d, g, trust=0.90)["resolution"]["winner"], "gemini")

    def test_a_medium_certainty_gemini_never_overrules_a_weak_detector(self):
        out = self.decide(self.detector("cassava", "Cassava Green Mottle", 0.55), self.gemini("cassava", "Cassava Mosaic Disease", "medium"))
        self.assertEqual((out["final"]["top_label"], out["resolution"]["winner"], out["resolution"]["basis"]), ("Cassava Green Mottle", "detector", "unconfirmed"))

    def test_when_the_detector_found_nothing_a_highly_certain_gemini_can_name_the_disease(self):
        out = self.decide(self.detector("maize", "", None, "none"), self.gemini("maize", "Maize Leaf Blight"))
        self.assertEqual((out["final"]["status"], out["final"]["top_label"]), ("disease", "Maize Leaf Blight"))
        self.assertEqual(out["resolution"]["winner"], "gemini")

    def test_a_highly_certain_healthy_reading_beats_a_weak_disease_detection(self):
        out = self.decide(self.detector("cassava", "Cassava Bacterial Blight", 0.6), self.gemini("cassava", "Healthy cassava leaf"))
        self.assertEqual((out["final"]["status"], out["final"]["top_label"]), ("healthy", "Healthy cassava leaf"))

    def test_another_problem_gemini_cannot_name_replaces_a_weak_detection_only_when_gemini_is_highly_certain(self):
        out = self.decide(self.detector("cassava", "Cassava Green Mottle", 0.55), self.gemini("cassava", "Other problem"))
        self.assertEqual((out["final"]["status"], out["final"]["top_label"], out["final"]["top_confidence"]), ("disease", "Other leaf problem (not Cassava Green Mottle)", None))
        self.assertEqual((out["resolution"]["winner"], out["resolution"]["basis"]), ("gemini", "gemini_more_certain"))
        self.assertEqual(out["resolution"]["detector"]["top_label"], "Cassava Green Mottle")  # what was set aside is still shown

    def test_the_disease_name_gemini_suggests_becomes_the_answer(self):
        g = {**self.gemini("maize", "Other problem"), "problem_name": "Gray leaf spot"}
        out = self.decide(self.detector("maize", "Maize Streak Virus", 0.55), g)
        self.assertEqual((out["final"]["status"], out["final"]["top_label"], out["final"]["top_confidence"]), ("disease", "Gray leaf spot", None))
        self.assertEqual((out["resolution"]["winner"], out["resolution"]["basis"]), ("gemini", "gemini_more_certain"))
        self.assertEqual(out["resolution"]["detector"]["top_label"], "Maize Streak Virus")

    def test_another_problem_never_replaces_a_detector_that_is_sure_or_a_gemini_that_is_not(self):
        sure = self.decide(self.detector("cassava", "Cassava Green Mottle", 0.9), self.gemini("cassava", "Other problem"))
        self.assertEqual((sure["final"]["top_label"], sure["resolution"]["basis"]), ("Cassava Green Mottle", "detector_more_certain"))
        medium = self.decide(self.detector("cassava", "Cassava Green Mottle", 0.55), self.gemini("cassava", "Other problem", "medium"))
        self.assertEqual((medium["final"]["top_label"], medium["resolution"]["basis"]), ("Cassava Green Mottle", "unconfirmed"))

    def test_gemini_always_intervenes_when_the_leaf_is_not_maize_or_cassava(self):
        for certainty in ("high", "medium"):
            out = self.decide(self.detector(confidence=0.97), self.gemini("other_plant", "Cannot tell", certainty, "other_crop"))
            self.assertEqual((out["final"]["crop"], out["final"]["status"], out["final"]["top_label"]), ("other", "other", "Not a maize or cassava leaf"))
            self.assertEqual((out["final"]["top_confidence"], out["final"]["results"]), (None, []))
            self.assertEqual((out["resolution"]["winner"], out["resolution"]["basis"]), ("gemini", "not_supported"))
            self.assertEqual(out["resolution"]["detector"]["top_label"], "Maize Streak Virus")  # what it wrongly said is kept

    def test_no_leaf_at_all_is_its_own_outcome(self):
        out = self.decide(self.detector(), self.gemini("not_a_plant", "Cannot tell", "high", "not_leaf"))
        self.assertEqual((out["final"]["status"], out["final"]["top_label"]), ("other", "No leaf found in the photo"))
        self.assertEqual(out["resolution"]["basis"], "not_a_leaf")

    def test_it_intervenes_even_when_the_detector_found_nothing(self):
        out = self.decide(self.detector("maize", "", None, "none"), self.gemini("other_plant", "Cannot tell", "medium", "other_crop"))
        self.assertEqual((out["final"]["status"], out["resolution"]["winner"]), ("other", "gemini"))

    def test_a_guess_that_it_might_be_another_plant_does_not_intervene(self):
        # low certainty is judged "unsure" before it reaches the decision, so the detector's answer stays (unconfirmed)
        from apps.advisory.services import advisor

        verdict = advisor.judge(self.detector(), {"crop": "other_plant", "condition": "Cannot tell", "certainty": "low"}, "en")
        self.assertEqual(verdict["verdict"], "unsure")
        out = self.decide(self.detector(), verdict)
        self.assertEqual((out["final"]["top_label"], out["resolution"]["basis"]), ("Maize Streak Virus", "unconfirmed"))

    def test_the_detectors_original_answer_is_always_recorded(self):
        out = self.decide(self.detector("cassava", "Cassava Green Mottle", 0.55), self.gemini("cassava", "Cassava Mosaic Disease"))
        self.assertEqual(out["resolution"]["detector"], {"crop": "cassava", "status": "disease", "top_label": "Cassava Green Mottle", "top_confidence": 0.55})


class PhotoNameTests(SimpleTestCase):
    def test_photos_get_random_unguessable_names_keeping_a_safe_extension(self):
        import re
        from .models import detection_photo_path

        a, b = detection_photo_path(None, "leaf.jpg"), detection_photo_path(None, "leaf.jpg")
        self.assertRegex(a, r"^detections/\d{4}/\d{2}/[0-9a-f]{32}\.jpg$")
        self.assertNotEqual(a, b)
        self.assertTrue(detection_photo_path(None, "LEAF.PNG").endswith(".png"))
        for hostile in ("leaf.php", "../../etc/passwd", "noextension", "x.html"):
            self.assertRegex(detection_photo_path(None, hostile), r"^detections/\d{4}/\d{2}/[0-9a-f]{32}\.jpg$")

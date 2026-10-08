import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase

from apps.accounts.models import User


def fake_image():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "green").save(buf, "JPEG")
    return SimpleUploadedFile("leaf.jpg", buf.getvalue(), content_type="image/jpeg")


FAKE_OUTCOME = {
    "width": 64,
    "height": 64,
    "results": [{"label": "Northern Leaf Blight", "confidence": 0.91, "bbox": [1, 2, 30, 40]}],
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
        self.assertEqual(r.data["top_label"], "Northern Leaf Blight")

        r = self.client.get("/api/detections/")
        self.assertEqual(r.data["count"], 1)

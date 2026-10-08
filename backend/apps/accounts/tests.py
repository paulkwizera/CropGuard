from rest_framework.test import APITestCase


class AuthFlowTests(APITestCase):
    def test_register_login_me(self):
        r = self.client.post(
            "/api/auth/register/",
            {"username": "farmer1", "password": "Str0ng-pass!", "district": "Musanze"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertNotIn("password", r.data)

        r = self.client.post(
            "/api/auth/login/", {"username": "farmer1", "password": "Str0ng-pass!"}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

        r = self.client.get("/api/auth/me/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["username"], "farmer1")

    def test_me_requires_login(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

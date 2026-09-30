from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class AuthenticationTests(APITestCase):
    def test_signup_login_and_me_flow(self):
        signup_response = self.client.post(
            "/api/auth/signup/",
            {
                "email": "Patient@Example.com",
                "first_name": "Asha",
                "last_name": "Mehta",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(signup_response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="patient@example.com")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password("StrongPass123!"))

        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "patient@example.com", "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)
        self.assertIn("refresh", login_response.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
        me_response = self.client.get("/api/auth/me/")

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], "patient@example.com")

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

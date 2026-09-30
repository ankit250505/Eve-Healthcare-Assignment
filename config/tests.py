from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class FrontendTests(TestCase):
    def test_homepage_renders_patient_interface(self):
        response = self.client.get(reverse("frontend-home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EVE Healthcare")
        self.assertContains(response, "Available tests")
        self.assertContains(response, "Simulated payment")

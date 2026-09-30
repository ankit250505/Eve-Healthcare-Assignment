from decimal import Decimal

from django.core.management.base import BaseCommand

from catalogue.models import CentreTest, DiagnosticCentre, DiagnosticTest


class Command(BaseCommand):
    help = "Create a small demo catalogue for local development."

    def handle(self, *args, **options):
        centres = [
            {
                "name": "EVE Diagnostics Green Park",
                "city": "Delhi",
                "address": "A-18 Green Park Main, New Delhi",
            },
            {
                "name": "EVE Diagnostics HSR",
                "city": "Bengaluru",
                "address": "27th Main Road, HSR Layout, Bengaluru",
            },
        ]
        tests = [
            {"name": "Complete Blood Count", "code": "cbc", "description": "Blood cell count screening."},
            {"name": "Thyroid Profile", "code": "thyroid-profile", "description": "T3, T4, and TSH panel."},
            {"name": "Liver Function Test", "code": "lft", "description": "Liver enzyme and protein panel."},
        ]
        prices = {
            "cbc": Decimal("499.00"),
            "thyroid-profile": Decimal("899.00"),
            "lft": Decimal("749.00"),
        }

        centre_objs = [
            DiagnosticCentre.objects.update_or_create(
                name=item["name"],
                city=item["city"],
                address=item["address"],
                defaults={"is_active": True},
            )[0]
            for item in centres
        ]
        test_objs = [
            DiagnosticTest.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "description": item["description"],
                    "is_active": True,
                },
            )[0]
            for item in tests
        ]

        created = 0
        for centre in centre_objs:
            for test in test_objs:
                _, was_created = CentreTest.objects.update_or_create(
                    centre=centre,
                    test=test,
                    defaults={"price": prices[test.code], "is_active": True},
                )
                created += int(was_created)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(centre_objs)} centres, {len(test_objs)} tests, {created} new offerings."))

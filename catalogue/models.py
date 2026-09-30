from django.core.validators import MinValueValidator
from django.db import models


class DiagnosticCentre(models.Model):
    name = models.CharField(max_length=160)
    city = models.CharField(max_length=80)
    address = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=("name", "city", "address"), name="unique_centre_location"),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"


class DiagnosticTest(models.Model):
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class CentreTest(models.Model):
    centre = models.ForeignKey(DiagnosticCentre, related_name="offerings", on_delete=models.PROTECT)
    test = models.ForeignKey(DiagnosticTest, related_name="offerings", on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("centre__name", "test__name")
        constraints = [
            models.UniqueConstraint(fields=("centre", "test"), name="unique_test_per_centre"),
        ]

    def __str__(self):
        return f"{self.test} at {self.centre}"

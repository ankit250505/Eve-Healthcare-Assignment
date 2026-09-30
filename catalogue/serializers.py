from rest_framework import serializers

from catalogue.models import CentreTest, DiagnosticCentre, DiagnosticTest


class DiagnosticCentreSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticCentre
        fields = ("id", "name", "city", "address", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class DiagnosticTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticTest
        fields = ("id", "name", "code", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class CentreTestSerializer(serializers.ModelSerializer):
    centre = DiagnosticCentreSerializer(read_only=True)
    test = DiagnosticTestSerializer(read_only=True)
    centre_id = serializers.PrimaryKeyRelatedField(
        queryset=DiagnosticCentre.objects.all(), source="centre", write_only=True
    )
    test_id = serializers.PrimaryKeyRelatedField(
        queryset=DiagnosticTest.objects.all(), source="test", write_only=True
    )

    class Meta:
        model = CentreTest
        fields = (
            "id",
            "centre",
            "test",
            "centre_id",
            "test_id",
            "price",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        centre = attrs.get("centre", getattr(self.instance, "centre", None))
        test = attrs.get("test", getattr(self.instance, "test", None))
        if centre and not centre.is_active:
            raise serializers.ValidationError({"centre_id": "Inactive centres cannot be used for offerings."})
        if test and not test.is_active:
            raise serializers.ValidationError({"test_id": "Inactive tests cannot be used for offerings."})
        return attrs

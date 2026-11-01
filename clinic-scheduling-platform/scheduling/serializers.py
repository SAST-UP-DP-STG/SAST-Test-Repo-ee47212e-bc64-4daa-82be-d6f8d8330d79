from rest_framework import serializers

from .models import Appointment, Clinic, Encounter, Patient, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "is_staff", "clinic"]


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ["id", "full_name", "clinic", "date_of_birth", "contact_email"]


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = "__all__"


class EncounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Encounter
        fields = "__all__"


class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ["id", "name", "location", "status", "owner", "weekly_capacity"]

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import EncounterManager

ROLE_RECEPTIONIST = "receptionist"
ROLE_CLINICIAN = "clinician"
ROLE_CLINIC_ADMIN = "clinic_admin"

ROLE_CHOICES = [
    (ROLE_RECEPTIONIST, "Receptionist"),
    (ROLE_CLINICIAN, "Clinician"),
    (ROLE_CLINIC_ADMIN, "Clinic Admin"),
]


class User(AbstractUser):
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_RECEPTIONIST)
    clinic = models.ForeignKey(
        "Clinic", null=True, blank=True, on_delete=models.SET_NULL, related_name="staff"
    )
    mfa_enabled = models.BooleanField(default=False)
    security_version = models.IntegerField(default=1)

    @property
    def is_clinic_admin(self):
        return self.role == ROLE_CLINIC_ADMIN


class Clinic(models.Model):
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=32, default="active")
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_clinics"
    )
    intake_notes = models.TextField(blank=True)
    weekly_capacity = models.IntegerField(default=120)

    class Meta:
        permissions = [
            ("change_panel", "Can change clinic configuration"),
            ("export_appointment", "Can export appointments"),
            ("approve_appointment", "Can approve appointment overrides"),
        ]

    def __str__(self):
        return self.name


class Patient(models.Model):
    full_name = models.CharField(max_length=120)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="patients")
    date_of_birth = models.DateField(null=True, blank=True)
    contact_email = models.EmailField(blank=True)

    def __str__(self):
        return self.full_name


class Appointment(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="appointments")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    clinician = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="appointments"
    )
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_appointments"
    )
    scheduled_for = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=32, default="scheduled")
    approval_status = models.CharField(max_length=32, default="pending")
    billing_status = models.CharField(max_length=32, default="unbilled")
    override_approved = models.BooleanField(default=False)
    internal_billing_note = models.TextField(blank=True)

    def __str__(self):
        return f"Appointment #{self.pk}"


class Encounter(models.Model):
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="encounters"
    )
    clinician = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="encounters"
    )
    note = models.TextField(blank=True)
    confidential = models.BooleanField(default=False)
    draft = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = EncounterManager()

    def __str__(self):
        return f"Encounter #{self.pk}"


class ClinicDocument(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="documents")
    encounter = models.ForeignKey(
        Encounter, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents"
    )
    title = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=32, default="intake")
    content = models.TextField(blank=True)
    confidential = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class InsuranceClaim(models.Model):
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="insurance_claims"
    )
    status = models.CharField(max_length=32, default="submitted")
    submitted_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"InsuranceClaim #{self.pk}"

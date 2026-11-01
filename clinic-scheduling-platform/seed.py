import os
from datetime import datetime, timedelta, timezone

import django
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth.models import Permission  # noqa: E402
from guardian.shortcuts import assign_perm  # noqa: E402

from scheduling.models import (  # noqa: E402
    Appointment,
    Clinic,
    ClinicDocument,
    Encounter,
    Patient,
    User,
)

PASSWORD = "Welcome@123"

ACCOUNTS = [
    ("admin_a", "admin.a@riverside-clinic.example", "clinic_admin", "A", True),
    ("reception_a", "reception.a@riverside-clinic.example", "receptionist", "A", False),
    ("clinician_a", "clinician.a@riverside-clinic.example", "clinician", "A", False),
    ("admin_b", "admin.b@hilltop-medical.example", "clinic_admin", "B", True),
    ("reception_b", "reception.b@hilltop-medical.example", "receptionist", "B", False),
    ("clinician_b", "clinician.b@hilltop-medical.example", "clinician", "B", False),
]


def run():
    ClinicDocument.objects.all().delete()
    Encounter.objects.all().delete()
    Appointment.objects.all().delete()
    Patient.objects.all().delete()
    User.objects.all().delete()
    Clinic.objects.all().delete()

    clinic_a = Clinic.objects.create(name="Riverside Family Clinic", location="Riverside", weekly_capacity=140)
    clinic_b = Clinic.objects.create(name="Hilltop Medical Center", location="Hilltop", weekly_capacity=100)
    clinics = {"A": clinic_a, "B": clinic_b}

    users = {}
    for username, email, role, clinic_key, is_staff in ACCOUNTS:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=PASSWORD,
            role=role,
            clinic=clinics[clinic_key],
            is_staff=is_staff,
        )
        users[username] = user

    clinic_a.owner = users["admin_a"]
    clinic_a.save()
    clinic_b.owner = users["admin_b"]
    clinic_b.save()

    perm_codenames = ["change_panel", "export_appointment", "approve_appointment", "view_clinic"]
    perms = {code: Permission.objects.get(codename=code) for code in perm_codenames}
    for username in ("admin_a", "admin_b"):
        users[username].user_permissions.add(*perms.values())

    for username, user in users.items():
        if user.clinic_id:
            assign_perm("scheduling.view_clinic", user, Clinic.objects.get(pk=user.clinic_id))

    base = datetime.now(timezone.utc).replace(microsecond=0)
    patients = {}
    for key, clinic in clinics.items():
        for index in range(1, 3):
            patient = Patient.objects.create(
                full_name=f"{clinic.name.split()[0]} Patient {index}",
                clinic=clinic,
                contact_email=f"patient{index}.{key.lower()}@example.com",
            )
            patients[(key, index)] = patient

    appointment_specs = [
        ("A", 1, "clinician_a", "reception_a", "Annual checkup"),
        ("A", 2, "clinician_a", "reception_a", "Follow-up visit"),
        ("B", 1, "clinician_b", "reception_b", "New patient intake"),
        ("B", 2, "clinician_b", "reception_b", "Lab review"),
    ]
    appointments = []
    for offset, (key, pindex, clinician_name, reception_name, reason) in enumerate(appointment_specs):
        appointment = Appointment.objects.create(
            clinic=clinics[key],
            patient=patients[(key, pindex)],
            clinician=users[clinician_name],
            created_by=users[reception_name],
            scheduled_for=base + timedelta(days=offset + 1),
            reason=reason,
            internal_billing_note=f"Internal billing note for {reason}",
        )
        appointments.append(appointment)

    Encounter.objects.create(
        appointment=appointments[0],
        clinician=users["clinician_a"],
        note="Patient stable. Routine vitals recorded.",
        confidential=False,
        draft=False,
    )
    Encounter.objects.create(
        appointment=appointments[1],
        clinician=users["clinician_a"],
        note="Confidential mental health assessment notes.",
        confidential=True,
        draft=True,
    )
    Encounter.objects.create(
        appointment=appointments[2],
        clinician=users["clinician_b"],
        note="Initial intake summary.",
        confidential=False,
        draft=False,
    )
    Encounter.objects.create(
        appointment=appointments[3],
        clinician=users["clinician_b"],
        note="Confidential lab interpretation pending sign-off.",
        confidential=True,
        draft=True,
    )

    encounters = list(Encounter.objects.order_by("id"))
    document_specs = [
        (clinic_a, encounters[0], "Riverside Intake Summary", "intake", False,
         "Patient intake summary for Riverside annual checkup. Vitals within normal range."),
        (clinic_a, encounters[1], "Riverside Behavioral Health Report", "report", True,
         "Confidential behavioral health assessment. Restricted to assigned clinician."),
        (clinic_b, encounters[2], "Hilltop New Patient Intake", "intake", False,
         "New patient intake notes for Hilltop. Insurance verified."),
        (clinic_b, encounters[3], "Hilltop Lab Interpretation", "report", True,
         "Confidential lab interpretation pending physician sign-off."),
    ]
    for clinic, encounter, title, doc_type, confidential, content in document_specs:
        ClinicDocument.objects.create(
            clinic=clinic,
            encounter=encounter,
            title=title,
            doc_type=doc_type,
            confidential=confidential,
            content=content,
        )

    print("Seed complete.")
    print(f"Clinics: {clinic_a.id} {clinic_a.name}, {clinic_b.id} {clinic_b.name}")
    for username, user in users.items():
        print(f"User {user.id}: {username} / {PASSWORD} ({user.role}, clinic {user.clinic_id})")
    for appointment in appointments:
        print(f"Appointment {appointment.id}: clinic {appointment.clinic_id}, clinician {appointment.clinician_id}")
    for encounter in Encounter.objects.all():
        print(f"Encounter {encounter.id}: appointment {encounter.appointment_id}, confidential={encounter.confidential}")


if __name__ == "__main__":
    run()

import threading
from types import SimpleNamespace

from django.db import connection

from services.shared_auth import issue_token

SERVICE_IDENTITY = "service-account"


def _service_principal():
    return SimpleNamespace(
        id=None,
        username=SERVICE_IDENTITY,
        email="service@internal.local",
        role="service_account",
        clinic_id=None,
    )


def _run(appointment_id, actor):
    from scheduling.models import Appointment, InsuranceClaim

    try:
        appointment = Appointment.objects.filter(pk=appointment_id).first()
        if appointment is None:
            return
        issue_token(_service_principal())
        InsuranceClaim.objects.create(
            appointment=appointment,
            status="submitted",
            submitted_by=SERVICE_IDENTITY,
        )
    finally:
        connection.close()


def dispatch_claim_submission(appointment_id, actor):
    thread = threading.Thread(target=_run, args=(appointment_id, actor), daemon=True)
    thread.start()
    return thread

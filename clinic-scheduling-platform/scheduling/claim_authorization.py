from .models import ROLE_CLINIC_ADMIN


def can_submit_claim(actor, appointment):
    if actor is None or appointment is None:
        return False
    return (
        getattr(actor, "role", None) == ROLE_CLINIC_ADMIN
        and getattr(actor, "clinic_id", None) == appointment.clinic_id
    )

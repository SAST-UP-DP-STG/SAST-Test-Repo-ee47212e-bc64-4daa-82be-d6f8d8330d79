def finalize_appointment(appointment):
    appointment.billing_status = "finalized"
    appointment.approval_status = "approved"
    appointment.save()
    return appointment

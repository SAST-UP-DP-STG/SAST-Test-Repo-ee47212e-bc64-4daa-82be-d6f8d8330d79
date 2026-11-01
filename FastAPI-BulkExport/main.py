from __future__ import annotations

from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI(title="FastAPI-BulkExport")

JWT_SECRET = "bulkexport-dev-secret"
JWT_ALGORITHM = "HS256"
bearer_scheme = HTTPBearer()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

engine = create_engine("sqlite:///./bulkexport.db", connect_args={"check_same_thread": False})
Base = declarative_base()
db = sessionmaker(bind=engine)()


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    owner_id = Column(String, index=True)
    client = Column(String)
    amount = Column(Integer)
    details = Column(String)


USERS = {
    "u1": {"id": "u1", "email": "alice@export.io"},
    "u2": {"id": "u2", "email": "bob@export.io"},
    "u3": {"id": "u3", "email": "carol@export.io"},
}

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
db.add_all([
    Invoice(id=201, owner_id="u1", client="Acme Corp",     amount=14500, details="Consulting Q1"),
    Invoice(id=202, owner_id="u1", client="Globex Ltd",    amount=8200,  details="Software license"),
    Invoice(id=203, owner_id="u2", client="Initech Inc",   amount=31000, details="Annual retainer"),
    Invoice(id=204, owner_id="u2", client="Umbrella Corp", amount=5500,  details="Support contract"),
    Invoice(id=205, owner_id="u3", client="Cyberdyne",     amount=99000, details="R&D partnership"),
])
db.commit()

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def issue_token(user_id: str, email: str) -> str:
    return jwt.encode({"sub": user_id, "email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = USERS.get(payload["sub"])
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str

class BulkExportRequest(BaseModel):
    invoice_ids: List[int]
    format: str = "pdf"

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/auth/login")
def login(body: LoginRequest):
    user = next((u for u in USERS.values() if u["email"] == body.email), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": issue_token(user["id"], user["email"])}


@app.get("/api/invoices")
def list_invoices(current_user: dict = Depends(get_current_user)):
    """Return only the caller's own invoices — safe."""
    return db.query(Invoice).filter_by(owner_id=current_user["id"]).all()


@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: int, current_user: dict = Depends(get_current_user)):
    """Fetch a single invoice scoped to the caller — safe."""
    invoice = db.query(Invoice).filter_by(id=invoice_id, owner_id=current_user["id"]).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@app.post("/api/invoices/export")
def bulk_export(
    body: BulkExportRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Export a set of invoices in bulk.

    VULNERABLE: iterates over the caller-supplied list of invoice_ids and
    fetches each one by ID with no per-item ownership check.

    The single-item GET endpoint above correctly enforces ownership.  The bulk
    endpoint does not, because the developer assumed the client would only send
    IDs it already has access to.

    A caller who knows (or enumerates) another user's invoice ID can include it
    in the batch and receive the full invoice details in the response.
    """
    results = []
    not_found = []

    for invoice_id in body.invoice_ids:
        # VULNERABLE: no ownership check — any authenticated user can export
        # any invoice by including its ID in the batch request.
        invoice = db.get(Invoice, invoice_id)
        if invoice:
            results.append(invoice)
        else:
            not_found.append(invoice_id)

    return {
        "format": body.format,
        "exported": results,
        "not_found": not_found,
    }

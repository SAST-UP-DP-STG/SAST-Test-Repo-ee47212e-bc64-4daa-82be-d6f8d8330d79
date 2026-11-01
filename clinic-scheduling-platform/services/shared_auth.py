import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv

load_dotenv()

SHARED_JWT_SECRET = os.environ.get("SHARED_JWT_SECRET", "clinic-scheduling-shared-jwt-secret")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_TTL_MINUTES = int(os.environ.get("JWT_TTL_MINUTES", "480"))

ROLE_SCOPES = {
    "clinic_admin": ["reports:admin", "reports:read", "metrics:write"],
    "clinician": ["reports:read"],
    "receptionist": ["reports:read"],
}


def issue_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "clinic_id": user.clinic_id,
        "scopes": ROLE_SCOPES.get(user.role, []),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_TTL_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, SHARED_JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    return jwt.decode(token, SHARED_JWT_SECRET, algorithms=[JWT_ALGORITHM])

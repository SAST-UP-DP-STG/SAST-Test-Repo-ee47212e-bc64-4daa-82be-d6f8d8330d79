import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .shared_auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload

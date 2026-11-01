import jwt
from rest_framework import authentication, exceptions

from services.shared_auth import decode_token


class SharedJWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        token = header.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            raise exceptions.AuthenticationFailed("Invalid token")

        from .models import User

        try:
            user = User.objects.get(pk=payload.get("sub"))
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("Unknown user")
        return (user, token)

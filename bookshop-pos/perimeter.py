import re

from flask import request

from auth import require_auth

_PROTECTED = re.compile(r"^/ops/[^/]+$")


def register_perimeter(app):
    @app.before_request
    def ops_perimeter_guard():
        if _PROTECTED.match(request.path):
            return require_auth()
        return None

import os

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from asgiref.wsgi import WsgiToAsgi
from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from services.analytics_service import app as analytics_app
from services.finance_service import app as finance_flask_app

django_app = get_asgi_application()
finance_app = WsgiToAsgi(finance_flask_app)

application = Starlette(
    routes=[
        Mount("/static", app=StaticFiles(directory="static"), name="static"),
        Mount("/svc/analytics", app=analytics_app),
        Mount("/svc/finance", app=finance_app),
        Mount("/", app=django_app),
    ]
)

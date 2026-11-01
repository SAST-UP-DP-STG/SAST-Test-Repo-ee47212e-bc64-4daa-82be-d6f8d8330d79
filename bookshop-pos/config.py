import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COMMANDS_DIR = os.path.join(DATA_DIR, "commands")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "bookshop-pos-backoffice-key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(DATA_DIR, "bookshop.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    STORE_ID = os.environ.get("STORE_ID", "STORE-01")
    SETUP_MODE = os.environ.get("SETUP_MODE", "1") == "1"

    POS_CMD_INBOX = os.path.join(COMMANDS_DIR, "incoming")
    POS_CMD_PROCESSED = os.path.join(COMMANDS_DIR, "processed")
    POS_CMD_FAILED = os.path.join(COMMANDS_DIR, "failed")
    POS_CMD_OUTBOX = os.path.join(COMMANDS_DIR, "outbox")
    POS_CMD_POLL_SECONDS = 2

    SERVICE_HOST = os.environ.get("SERVICE_HOST", "0.0.0.0")
    POS_TCP_CMD_PORT = int(os.environ.get("POS_TCP_CMD_PORT", "9100"))
    POS_BROKER_PORT = int(os.environ.get("POS_BROKER_PORT", "9110"))
    POS_CACHE_PORT = int(os.environ.get("POS_CACHE_PORT", "9120"))
    POS_RPC_PORT = int(os.environ.get("POS_RPC_PORT", "9130"))

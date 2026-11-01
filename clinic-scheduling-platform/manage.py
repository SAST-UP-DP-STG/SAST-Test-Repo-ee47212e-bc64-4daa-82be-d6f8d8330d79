import os
import sys

from dotenv import load_dotenv


def main():
    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Could not import Django. Are you sure it is installed and available "
            "on your PYTHONPATH environment variable?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

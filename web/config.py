"""App configuration."""

import os

# Secret key for session cookies – change this in production!
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-abc123")

# Login credentials – change these!
APP_USERNAME = os.environ.get("APP_USERNAME", "couple")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "expenses123")

# Database path
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "expenses.db"))

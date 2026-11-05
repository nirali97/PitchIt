"""Runs before any test module imports `app`. Makes tests hermetic:
in-memory DB (never touches pitchit.db) and no real Groq key from .env."""
import os
os.environ["JWT_SECRET"] = "test-secret-long-enough-for-local-tests-123456789"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["GROQ_API_KEY"] = ""

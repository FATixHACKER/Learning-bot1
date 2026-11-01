"""All settings live here. Edit the .env file, not this file."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# --- Required -------------------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

# --- Optional -------------------------------------------------------------
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().lstrip("-").isdigit()}
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "UTC").strip() or "UTC"

# --- Paths ----------------------------------------------------------------
DB_PATH = BASE_DIR / "studybot.sqlite3"

# --- App behaviour --------------------------------------------------------
FOCUS_PRESETS = [15, 25, 45, 60]
DEFAULT_FOCUS_MINUTES = 25
MAX_FOCUS_MINUTES = 180
QUIZ_QUESTION_COUNT = 5
DEFAULT_REMINDER_TIME = "19:00"
BOT_NAME = "StudyMate"
BOT_USERNAME = "study"


def token_present() -> bool:
    return bool(TELEGRAM_TOKEN)

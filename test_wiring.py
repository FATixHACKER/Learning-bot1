"""Wiring test — builds the real Application and checks every handler registers.

    python test_wiring.py

This catches the classic beginner bug: referencing a class in a handler
without importing it (NameError only shows up at startup).
"""
import os
import sys
import tempfile
from pathlib import Path

tmpdir = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(tmpdir, "test.sqlite3")
os.environ.setdefault("TELEGRAM_TOKEN", "123456:FAKE-TOKEN-FOR-TESTS")

import database  # noqa: E402

database.DB_PATH = Path(os.environ["DB_PATH"])

from telegram.ext import Application  # noqa: E402

import bot  # noqa: E402
from handlers import cards, focus, quiz, stats, tasks  # noqa: E402
from keyboards import back_to_menu, focus_presets, main_menu, task_list_keyboard  # noqa: E402

PASS, FAIL = 0, 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} {detail}")


print("\n── Handler registration ────────────────────────")
# build the REAL application, exactly as bot.py does at startup
app = bot.build_application("123456:FAKE-TOKEN")

check("application builds", app is not None)
check("error handler attached", len(app.error_handlers) == 1)

for name, module in [
    ("tasks", tasks), ("focus", focus), ("quiz", quiz),
    ("cards", cards), ("stats", stats),
]:
    check(f"{name} module present", module is not None)

print("\n── Handler inventory ───────────────────────────")
total = sum(len(v) for v in app.handlers.values())
check("handlers registered", total >= 15, f"only {total}")
for group, entries in app.handlers.items():
    print(f"     {group}: {len(entries)}")

print("\n── Keyboards build ─────────────────────────────")
for label, kb in [
    ("main menu", main_menu()),
    ("focus presets", focus_presets()),
    ("back to menu", back_to_menu()),
    ("task list", task_list_keyboard([{"id": 1, "title": "t", "status": "pending"}])),
]:
    check(f"{label} builds", len(kb.inline_keyboard) > 0)

print("\n── Command routing (real check_update) ───────────")
from datetime import datetime, timezone  # noqa: E402

from telegram import Chat, Message, MessageEntity, Update, User  # noqa: E402

all_handlers = []
for entries in app.handlers.values():
    all_handlers.extend(entries)


class FakeTelegramBot:
    """PTB handlers check update.get_bot().username — this stands in for it."""

    username = "studymate"
    id = 123456


def routing_matches(update):
    for h in all_handlers:
        try:
            if h.check_update(update):
                return True
        except Exception:
            continue
    return False


def cmd_update(text):
    """Build an update that looks like a real Telegram command."""
    u = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=Chat(id=555, type="private"),
            from_user=User(id=555, first_name="Bro", is_bot=False),
            text=text,
            entities=[MessageEntity(type="bot_command", offset=0, length=len(text))],
        ),
    )
    u.set_bot(FakeTelegramBot())
    u.message.set_bot(FakeTelegramBot())
    return u


for cmd in ["start", "help", "add", "tasks", "today", "done", "del", "focus", "stop",
            "quiz", "card", "cards", "review", "delcard", "stats", "remind", "timezone"]:
    check(f"/{cmd} routes to a handler", routing_matches(cmd_update(f"/{cmd}")))

print(f"\n{'=' * 46}")
print(f"  {PASS} passed, {FAIL} failed")
print(f"{'=' * 46}\n")
sys.exit(1 if FAIL else 0)

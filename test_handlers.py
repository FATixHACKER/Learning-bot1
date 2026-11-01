"""Integration test for the bot handlers (Telegram API is mocked).

    python test_handlers.py

Feeds fake updates through the real handler functions and checks what the
bot would have sent back.
"""
import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

tmpdir = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(tmpdir, "test.sqlite3")
os.environ.setdefault("TELEGRAM_TOKEN", "123456:FAKE-TOKEN-FOR-TESTS")

import database  # noqa: E402

database.DB_PATH = Path(os.environ["DB_PATH"])

from telegram import CallbackQuery, Chat, Message, Update, User  # noqa: E402

from bot import cmd_help, cmd_start, menu_callback  # noqa: E402
from handlers import cards, focus, quiz, stats, tasks  # noqa: E402

PASS, FAIL = 0, 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} {detail}")


class Recorder:
    """Captures reply_text / edit_message_text calls."""

    def __init__(self):
        self.replies = []
        self.edits = []

    def reset(self):
        self.replies.clear()
        self.edits.clear()


CURRENT = Recorder()


async def _fake_reply_text(self, text, **kwargs):
    CURRENT.replies.append((text, kwargs))


async def _fake_edit_message_text(self, text, **kwargs):
    CURRENT.edits.append((text, kwargs))


async def _fake_answer(self, *args, **kwargs):
    return True


# Telegram objects use __slots__, so we patch the classes for the whole test run
Message.reply_text = _fake_reply_text
CallbackQuery.edit_message_text = _fake_edit_message_text
CallbackQuery.answer = _fake_answer


# --------------------------------------------------------------------------
# fake Telegram plumbing
# --------------------------------------------------------------------------
class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id=None, text=None, **kwargs):
        self.sent.append({"chat_id": chat_id, "text": text, **kwargs})
        return Message(
            message_id=len(self.sent),
            date=datetime.now(timezone.utc),
            chat=Chat(id=chat_id or 1, type="private"),
            text=text,
        )


class FakeJobQueue:
    def __init__(self):
        self.once = []
        self.daily = []

    def run_once(self, callback, when, data=None, name=None, **kw):
        self.once.append({"callback": callback, "when": when, "data": data, "name": name})

    def run_daily(self, callback, time, data=None, name=None, **kw):
        self.daily.append({"callback": callback, "time": time, "data": data, "name": name})

    def get_jobs_by_name(self, name):
        return []


class FakeContext:
    def __init__(self, bot, user_data=None, args=None):
        self.bot = bot
        self.user_data = user_data if user_data is not None else {}
        self.args = args if args is not None else []
        self.job_queue = FakeJobQueue()
        self.job = None


def make_user(uid=555, username="bro"):
    return User(id=uid, first_name="Bro", username=username, is_bot=False)


def make_update(text, uid=555):
    chat = Chat(id=uid, type="private")
    msg = Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=chat,
        from_user=make_user(uid),
        text=text,
    )
    return Update(update_id=1, message=msg)


def make_callback(data, uid=555):
    chat = Chat(id=uid, type="private")
    msg = Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=chat,
        from_user=make_user(uid),
        text="",
    )
    cq = CallbackQuery(
        id="1",
        from_user=make_user(uid),
        chat_instance="ci",
        data=data,
        message=msg,
    )
    return Update(update_id=2, callback_query=cq)


# --------------------------------------------------------------------------
async def run():
    print("\n── /start and /help ───────────────────────────")
    CURRENT.reset()
    await cmd_start(make_update("/start"), FakeContext(FakeBot()))
    check("/start replies", len(CURRENT.replies) == 1)
    check("/start shows menu buttons", "reply_markup" in CURRENT.replies[0][1])
    CURRENT.reset()
    await cmd_help(make_update("/help"), FakeContext(FakeBot()))
    check("/help lists commands", "/focus" in CURRENT.replies[0][0])

    print("\n── Tasks: quick add ───────────────────────────")
    CURRENT.reset()
    ctx = FakeContext(FakeBot())
    await tasks.cmd_add(make_update("/add Finish calculus chapter 3 | Math | High"), ctx)
    check("quick add creates task", "Added task" in CURRENT.replies[0][0], CURRENT.replies[0][0])
    check("subject echoed", "Math" in CURRENT.replies[0][0])
    check("priority echoed", "High" in CURRENT.replies[0][0])

    saved = database.list_tasks(555)
    check("task stored in db", len(saved) == 1 and saved[0]["title"] == "Finish calculus chapter 3")
    task_id = saved[0]["id"]

    print("\n── Tasks: list, complete, delete ───────────────")
    CURRENT.reset()
    await tasks.cmd_tasks(make_update("/tasks"), FakeContext(FakeBot()))
    check("/tasks lists the task", "Finish calculus chapter 3" in CURRENT.replies[0][0])
    check("/tasks attaches buttons", "reply_markup" in CURRENT.replies[0][1])

    CURRENT.reset()
    await tasks.cmd_done(make_update(f"/done {task_id}"), FakeContext(FakeBot(), args=[str(task_id)]))
    check("/done confirms", "done" in CURRENT.replies[0][0].lower())
    check("db status flipped", database.get_task(555, task_id)["status"] == "done")

    CURRENT.reset()
    await tasks.cmd_today(make_update("/today"), FakeContext(FakeBot()))
    check("/today renders", "Today" in CURRENT.replies[0][0])
    check("/today shows counts", "pending" in CURRENT.replies[0][0].lower())

    print("\n── Tasks: button callback ──────────────────────")
    CURRENT.reset()
    await tasks.task_callback(make_callback(f"task:done:{task_id}"), FakeContext(FakeBot()))
    check("button edit produced text", len(CURRENT.edits) == 1)

    print("\n── Focus timer ─────────────────────────────────")
    CURRENT.reset()
    ctx = FakeContext(FakeBot(), args=["25"])
    await focus.cmd_focus(make_update("/focus 25"), ctx)
    check("/focus 25 starts", "25 min" in CURRENT.replies[0][0])
    check("timer job scheduled", len(ctx.job_queue.once) == 1)
    if ctx.job_queue.once:
        check("job named focus_end", ctx.job_queue.once[0]["name"] == "focus_end")
    else:
        check("job named focus_end", False)

    CURRENT.reset()
    await focus.cmd_focus(make_update("/focus"), FakeContext(FakeBot()))
    check("/focus without args shows presets", "reply_markup" in CURRENT.replies[0][1])

    CURRENT.reset()
    await focus.cmd_focus(make_update("/focus abc"), FakeContext(FakeBot(), args=["abc"]))
    check("bad minutes rejected", "number" in CURRENT.replies[0][0].lower())

    CURRENT.reset()
    await focus.cmd_stop(make_update("/stop"), ctx)
    check("/stop stops timer", "stopped" in CURRENT.replies[0][0].lower())
    check("minutes logged on stop", database.total_minutes(555) >= 25)

    print("\n── Quiz ────────────────────────────────────────")
    CURRENT.reset()
    ctx = FakeContext(FakeBot(), args=["Math"])
    await quiz.cmd_quiz(make_update("/quiz Math"), ctx)
    check("/quiz sends a question", len(CURRENT.replies) == 1)
    check("question has options", "1." in CURRENT.replies[0][0])
    check("options as buttons", "reply_markup" in CURRENT.replies[0][1])
    check("quiz state saved", ctx.user_data.get("quiz", {}).get("total") == 1)

    CURRENT.reset()
    await quiz.cmd_quiz(make_update("/quiz Astrology"), FakeContext(FakeBot(), args=["Astrology"]))
    check("unknown subject rejected", "Unknown subject" in CURRENT.replies[0][0])

    print("\n── Flashcards ──────────────────────────────────")
    CURRENT.reset()
    await cards.cmd_card(make_update("/card Capital of France | Paris | Geography"), FakeContext(FakeBot()))
    check("/card saves", "saved" in CURRENT.replies[0][0].lower())
    check("card in db", database.flashcard_count(555) == 1)

    CURRENT.reset()
    await cards.cmd_cards(make_update("/cards"), FakeContext(FakeBot()))
    check("/cards lists", "Capital of France" in CURRENT.replies[0][0])

    CURRENT.reset()
    ctx = FakeContext(FakeBot())
    await cards.cmd_review(make_update("/review"), ctx)
    check("/review starts", "Card 1/1" in CURRENT.replies[0][0])

    CURRENT.reset()
    await cards.card_callback(make_callback("card:reveal:1"), ctx)
    check("reveal shows answer", "Paris" in CURRENT.edits[0][0])

    print("\n── Guided add flow (state machine) ─────────────")
    from telegram.ext import ConversationHandler

    CURRENT.reset()
    ctx = FakeContext(FakeBot())
    state = await tasks.cmd_add(make_update("/add"), ctx)
    check("/add with no args starts the guide", state == tasks.ADD_TITLE, str(state))
    check("asks for the title", "What's the task" in CURRENT.replies[0][0])

    CURRENT.reset()
    state = await tasks.add_title(make_update("Finish lab report"), ctx)
    check("title captured, moves to subject", state == tasks.ADD_SUBJECT, str(state))
    check("subject buttons shown", "reply_markup" in CURRENT.replies[0][1])

    CURRENT.reset()
    update = make_callback("add:subject:Physics")
    state = await tasks.add_subject(update, ctx)
    check("subject captured, moves to priority", state == tasks.ADD_PRIORITY, str(state))
    check("priority buttons shown", "reply_markup" in CURRENT.edits[0][1])

    CURRENT.reset()
    update = make_callback("add:priority:High")
    state = await tasks.add_priority(update, ctx)
    check("priority captured, conversation ends", state == ConversationHandler.END, str(state))

    guided = database.list_tasks(555)
    check("guided task saved with right fields",
          any(t["title"] == "Finish lab report" and t["subject"] == "Physics"
              and t["priority"] == "High" for t in guided),
          str(guided))

    print("\n── Stats ───────────────────────────────────────")
    CURRENT.reset()
    await stats.cmd_stats(make_update("/stats"), FakeContext(FakeBot()))
    check("/stats renders", "Streak" in CURRENT.replies[0][0])
    check("/stats shows chart", "Last 7 days" in CURRENT.replies[0][0])

    print("\n── Reminders ───────────────────────────────────")
    CURRENT.reset()
    ctx = FakeContext(FakeBot(), args=["19:00"])
    await stats.cmd_remind(make_update("/remind 19:00"), ctx)
    check("/remind sets time", "19:00" in CURRENT.replies[0][0])
    check("daily job scheduled", len(ctx.job_queue.daily) == 1)
    check("reminder stored", database.get_user(555)["reminder_time"] == "19:00")

    CURRENT.reset()
    await stats.cmd_remind(make_update("/remind off"), FakeContext(FakeBot(), args=["off"]))
    check("/remind off clears", "off" in CURRENT.replies[0][0].lower())
    check("reminder removed from db", database.get_user(555)["reminder_time"] is None)

    CURRENT.reset()
    await stats.cmd_remind(make_update("/remind 25:99"), FakeContext(FakeBot(), args=["25:99"]))
    check("bad time rejected", "HH:MM" in CURRENT.replies[0][0])

    print("\n── Timezone ────────────────────────────────────")
    CURRENT.reset()
    await stats.cmd_timezone(make_update("/timezone Asia/Karachi"), FakeContext(FakeBot(), args=["Asia/Karachi"]))
    check("timezone saved", database.get_user(555)["timezone"] == "Asia/Karachi")

    CURRENT.reset()
    await stats.cmd_timezone(make_update("/timezone Not/AZone"), FakeContext(FakeBot(), args=["Not/AZone"]))
    check("bad timezone rejected", "valid timezone" in CURRENT.replies[0][0])

    print("\n── Menu buttons ────────────────────────────────")
    for section in ["home", "tasks", "focus", "quiz", "cards", "stats", "reminder"]:
        CURRENT.reset()
        await menu_callback(make_callback(f"menu:{section}"), FakeContext(FakeBot()))
        ok = len(CURRENT.edits) == 1 and bool(CURRENT.edits[0][0])
        check(f"menu:{section} responds", bool(ok))

    print(f"\n{'=' * 46}")
    print(f"  {PASS} passed, {FAIL} failed")
    print(f"{'=' * 46}\n")
    return 1 if FAIL else 0


sys.exit(asyncio.run(run()))

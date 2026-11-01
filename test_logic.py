"""Self-test for the pure logic (no Telegram needed).

    python test_logic.py

Checks the database layer, task parsing, quiz building and streak logic.
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

# use a throwaway database so we never touch your real data
tmpdir = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(tmpdir, "test.sqlite3")

import database  # noqa: E402
import quiz_data  # noqa: E402

database.DB_PATH = __import__("pathlib").Path(os.environ["DB_PATH"])

PASS, FAIL = 0, 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} {detail}")


print("\n── Database layer ──────────────────────────────")
uid = 999001
database.init_db()
database.ensure_user(uid, "tester")

check("user row created", database.get_user(uid).get("user_id") == uid)

tid = database.add_task(uid, "Finish chapter 3", "Math", "High")
check("task added", tid is not None)
check("task is pending", database.get_task(uid, tid)["status"] == "pending")

database.set_task_status(uid, tid, "done")
check("task marked done", database.get_task(uid, tid)["status"] == "done")

counts = database.task_counts(uid)
check("counts correct", counts["done"] == 1 and counts["pending"] == 0, str(counts))

t2 = database.add_task(uid, "Second task", "Physics", "Low")
database.delete_task(uid, t2)
check("task deleted", database.get_task(uid, t2) is None)

card_id = database.add_flashcard(uid, "Capital of France?", "Paris", "Geography")
check("flashcard added", card_id is not None)
check("flashcard found", database.flashcard_count(uid) == 1)

database.log_study(uid, 25, "Focus")
check("study minutes logged", database.total_minutes(uid) == 25)
check("streak is 1 day", database.streak(uid) == 1)

week = database.last_days(uid, 7)
check("7 day series returned", len(week) == 7)
check("today has the minutes", week[-1][1] == 25)

database.log_quiz(uid, 4, 5)
q = database.quiz_totals(uid)
check("quiz score recorded", q["correct"] == 4 and q["total"] == 5 and q["percent"] == 80, str(q))

database.set_timezone(uid, "Asia/Karachi")
check("timezone saved", database.get_user(uid)["timezone"] == "Asia/Karachi")

database.set_reminder(uid, "19:00")
check("reminder saved", database.get_user(uid)["reminder_time"] == "19:00")
database.clear_reminder(uid)
check("reminder cleared", database.get_user(uid)["reminder_time"] is None)

print("\n── Task argument parsing ───────────────────────")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from handlers.tasks import parse_task_args

    t, s, p = parse_task_args("Finish chapter 3 | Math | High")
    check("title parsed", t == "Finish chapter 3", t)
    check("subject parsed", s == "Math", s)
    check("priority parsed", p == "High", p)

    t, s, p = parse_task_args("Just a title")
    check("default subject", s == "General", s)
    check("default priority", p == "Medium", p)

    t, s, p = parse_task_args("Title | physics | low")
    check("lowercase subject normalised", s == "Physics", s)
    check("lowercase priority normalised", p == "Low", p)
except Exception as e:
    check("task parsing module loads", False, repr(e))

print("\n── Quiz bank ───────────────────────────────────")
check("8 subjects available", len(quiz_data.SUBJECTS) == 8)
total_q = sum(len(v) for v in quiz_data.QUESTION_BANK.values())
check("bank has 40+ questions", total_q >= 40, str(total_q))

bad = []
for subject, entries in quiz_data.QUESTION_BANK.items():
    for e in entries:
        if e["answer"] not in e["options"]:
            bad.append((subject, e["q"]))
        if len(e["options"]) < 2:
            bad.append((subject, e["q"], "too few options"))
check("every answer is inside its options", not bad, str(bad[:3]))

try:
    from handlers.quiz import build_question

    q = build_question("Math")
    check("question built", "q" in q and len(q["options"]) >= 2)
    check("correct answer among options", q["answer"] in q["options"])
    check("options not duplicated", len(q["options"]) == len(set(q["options"])))
except Exception as e:
    check("quiz module loads", False, repr(e))

print(f"\n{'=' * 46}")
print(f"  {PASS} passed, {FAIL} failed")
print(f"{'=' * 46}\n")
sys.exit(1 if FAIL else 0)

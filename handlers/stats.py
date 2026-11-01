"""Stats + daily reminders."""
from datetime import time, timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

import config
import database
from keyboards import back_to_menu

BARS = "▁▂▃▄▅▆▇█"


def build_stats_text(user_id: int) -> str:
    """Render the stats block as HTML. Shared by /stats and the menu button."""
    database.ensure_user(user_id)

    week = database.last_days(user_id, 7)
    total = database.total_minutes(user_id)
    streak = database.streak(user_id)
    counts = database.task_counts(user_id)
    quiz = database.quiz_totals(user_id)

    peak = max([m for _, m in week] + [1])
    chart = "".join(BARS[min(7, int(m / peak * 7))] if m else "·" for _, m in week)
    labels = " ".join(d[5:] for d, _ in week)  # MM-DD

    week_total = sum(m for _, m in week)
    goal_pct = min(100, round(week_total / (7 * 60) * 100))

    quiz_line = (
        f"🧠 Quiz: {quiz['correct']}/{quiz['total']} ({quiz['percent']}%)"
        if quiz["total"]
        else "🧠 Quiz: no attempts yet"
    )

    return (
        f"📊 <b>Your stats</b>\n\n"
        f"🔥 Streak: <b>{streak}</b> day{'s' if streak != 1 else ''}\n"
        f"⏱ Total focused: <b>{total // 60}h {total % 60}m</b>\n"
        f"📅 This week: <b>{week_total} min</b> ({goal_pct}% of a 7h goal)\n\n"
        f"<b>Last 7 days</b>\n"
        f"<code>{chart}</code>\n"
        f"<code>{labels}</code>\n\n"
        f"📝 Tasks: {counts['done']} done / {counts['pending']} pending\n"
        f"{quiz_line}"
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    await update.message.reply_text(
        build_stats_text(user_id),
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )


async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /remind 19:00 -> daily study reminder at 7pm (server local time). """
    user_id = update.effective_user.id
    args = context.args

    if not args:
        user = database.get_user(user_id)
        current = user.get("reminder_time")
        state = f"⏰ Reminder is set for <b>{current}</b> daily." if current else "⏰ No daily reminder set."
        await update.message.reply_text(
            f"{state}\n\nSet one with <code>/remind 19:00</code>\n"
            "Remove it with <code>/remind off</code>",
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )
        return

    raw = args[0].strip().lower()
    if raw in ("off", "no", "cancel", "stop"):
        database.clear_reminder(user_id)
        _cancel_reminder_job(context, user_id)
        await update.message.reply_text("🔕 Daily reminder turned off.", reply_markup=back_to_menu())
        return

    try:
        hh, mm = raw.split(":")
        hh, mm = int(hh), int(mm)
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "Time format should be <code>HH:MM</code> — for example <code>/remind 19:00</code>",
            parse_mode="HTML",
        )
        return

    hhmm = f"{hh:02d}:{mm:02d}"
    database.set_reminder(user_id, hhmm)
    _schedule_reminder(context, user_id, update.effective_chat.id, hh, mm)
    await update.message.reply_text(
        f"⏰ Reminder set for <b>{hhmm}</b> every day. I'll ping you. ✅",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )


def _cancel_reminder_job(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    if not context.job_queue:
        return
    for job in context.job_queue.get_jobs_by_name("daily_reminder"):
        if job.data and job.data.get("user_id") == user_id:
            job.schedule_removal()


def _schedule_reminder(context, user_id: int, chat_id: int, hh: int, mm: int) -> None:
    """Run the reminder every day at hh:mm (UTC-based, simple + reliable)."""
    if not context.job_queue:
        return
    _cancel_reminder_job(context, user_id)
    context.job_queue.run_daily(
        reminder_job,
        time=time(hour=hh, minute=mm, second=0, tzinfo=timezone.utc),
        data={"user_id": user_id, "chat_id": chat_id},
        name="daily_reminder",
    )


async def reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.get("data") or {}
    chat_id = data.get("chat_id")
    if chat_id is None:
        return
    counts = database.task_counts(data.get("user_id"))
    pending = counts["pending"]
    msg = "⏰ <b>Study time!</b>\n\n"
    if pending:
        msg += f"You have <b>{pending}</b> task{'s' if pending != 1 else ''} pending. Let's clear one."
    else:
        msg += "No tasks pending — perfect time to review flashcards or do extra reading. 📚"
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")


async def cmd_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        user = database.get_user(update.effective_user.id)
        await update.message.reply_text(
            f"🌍 Your timezone: <code>{user.get('timezone', 'UTC')}</code>\n\n"
            "Change it with <code>/timezone Europe/London</code>",
            parse_mode="HTML",
        )
        return

    tz = args[0].strip()
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(tz)
    except Exception:
        await update.message.reply_text(
            "That doesn't look like a valid timezone.\n"
            "Try <code>Asia/Karachi</code>, <code>Europe/London</code>, <code>America/New_York</code> or <code>UTC</code>",
            parse_mode="HTML",
        )
        return

    database.set_timezone(update.effective_user.id, tz)
    await update.message.reply_text(f"🌍 Timezone set to <code>{tz}</code>", parse_mode="HTML", reply_markup=back_to_menu())


def register(app) -> None:
    app.add_handler(MessageHandler(filters.Regex(r"^/stats(@\w+)?(\s|$)"), cmd_stats))
    app.add_handler(MessageHandler(filters.Regex(r"^/remind(@\w+)?(\s|$)"), cmd_remind))
    app.add_handler(MessageHandler(filters.Regex(r"^/timezone(@\w+)?(\s|$)"), cmd_timezone))

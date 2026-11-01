"""Focus timer: /focus 25 starts a Pomodoro session that pings you when it's done."""
from datetime import timedelta

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes, JobQueue, MessageHandler, filters

import config
import database
from keyboards import back_to_menu, focus_presets


def _bar(done: int, total: int, width: int = 20) -> str:
    filled = int(width * done / total) if total else 0
    return "█" * filled + "░" * (width - filled)


async def cmd_focus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "⏱ <b>Focus timer</b>\n\nHow many minutes? Pick one or type "
            "<code>/focus 25</code>",
            parse_mode="HTML",
            reply_markup=focus_presets(),
        )
        return

    try:
        minutes = int(args[0])
    except ValueError:
        await update.message.reply_text("Minutes must be a number, e.g. <code>/focus 25</code>", parse_mode="HTML")
        return

    if minutes < 1 or minutes > config.MAX_FOCUS_MINUTES:
        await update.message.reply_text(
            f"Pick between 1 and {config.MAX_FOCUS_MINUTES} minutes."
        )
        return

    await start_focus(update, context, minutes)


async def focus_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    minutes = int(q.data.split(":")[2])
    context.user_data["focus"] = {"minutes": minutes, "message_id": None}
    await q.edit_message_text(
        f"⏱ <b>Focus session started: {minutes} min</b>\n\n"
        "Put the phone down. You got this. 🔥",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )
    await _schedule(update, context, minutes)


async def start_focus(update: Update, context: ContextTypes.DEFAULT_TYPE, minutes: int) -> None:
    user_id = update.effective_user.id
    database.ensure_user(user_id, update.effective_user.username)
    context.user_data["focus"] = {"minutes": minutes, "message_id": None}

    await update.message.reply_text(
        f"⏱ <b>Focus session started: {minutes} min</b>\n\n"
        "Put the phone down. You got this. 🔥",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )
    await _schedule(update, context, minutes)


async def _schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, minutes: int) -> None:
    """Set up the countdown job + a repeating progress ticker."""
    user_data = context.user_data.setdefault("focus", {})
    job_queue: JobQueue = context.job_queue

    # cancel any previous timer for this user
    for name in ("focus_end", "focus_tick"):
        old = job_queue.get_jobs_by_name(name)
        for job in old:
            if job.data and job.data.get("user_id") == update.effective_user.id:
                job.schedule_removal()

    user_data["end_time"] = None
    user_data["chat_id"] = update.effective_chat.id
    user_data["started"] = True

    job_queue.run_once(
        finish_job,
        timedelta(minutes=minutes),
        data={"user_id": update.effective_user.id, "chat_id": update.effective_chat.id, "minutes": minutes},
        name="focus_end",
    )


async def finish_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called by the job queue when the timer hits zero."""
    data = context.job.get("data") or {}
    chat_id = data.get("chat_id")
    minutes = data.get("minutes", 0)
    user_id = data.get("user_id")

    if chat_id is None:
        return

    database.log_study(user_id, minutes, "Focus")
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"⏰ <b>Time's up!</b>\n\n"
            f"You focused for {minutes} minutes. Logged to your stats. 🎉\n"
            "Take a 5-minute break, then go again."
        ),
        parse_mode="HTML",
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    focus = context.user_data.get("focus", {})
    minutes = focus.get("minutes", 0)
    if not focus.get("started"):
        await update.message.reply_text("No timer running. Start one with /focus 25")
        return

    job_queue: JobQueue = context.job_queue
    for name in ("focus_end", "focus_tick"):
        for job in job_queue.get_jobs_by_name(name):
            if job.data and job.data.get("user_id") == update.effective_user.id:
                job.schedule_removal()

    context.user_data["focus"] = {}
    text = "⏹ Timer stopped."
    if minutes:
        database.log_study(update.effective_user.id, minutes, "Focus")
        text += f"\nLogged {minutes} minutes anyway. Partial counts!"
    await update.message.reply_text(text, reply_markup=back_to_menu())


async def focus_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("🚫 No timer started.", reply_markup=back_to_menu())


def register(app) -> None:
    app.add_handler(MessageHandler(filters.Regex(r"^/focus(@\w+)?(\s|$)"), cmd_focus))
    app.add_handler(MessageHandler(filters.Regex(r"^/stop(@\w+)?(\s|$)"), cmd_stop))
    app.add_handler(CallbackQueryHandler(focus_button, pattern=r"^focus:start:"))
    app.add_handler(CallbackQueryHandler(focus_cancel, pattern=r"^focus:cancel$"))

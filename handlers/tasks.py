"""Task management: /add, /tasks, /done, /del, /today."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database
from keyboards import PRIORITY_EMOJI, SUBJECT_EMOJI, back_to_menu, task_list_keyboard
from utils import strip_command

ADD_TITLE, ADD_SUBJECT, ADD_PRIORITY = range(3)

VALID_SUBJECTS = [
    "Math", "Physics", "Chemistry", "Biology",
    "History", "English", "Programming", "General",
]
VALID_PRIORITIES = ["High", "Medium", "Low"]

CANCEL_TEXT = "❌ Cancelled. Nothing added."


def _normalize_subject(raw: str) -> str:
    for s in VALID_SUBJECTS:
        if s.lower() == raw.strip().lower():
            return s
    return raw.strip().title() or "General"


def _normalize_priority(raw: str) -> str:
    for p in VALID_PRIORITIES:
        if p.lower() == raw.strip().lower():
            return p
    return "Medium"


def parse_task_args(text: str) -> tuple[str, str, str]:
    """'Finish math hw | Math | High' -> ('Finish math hw', 'Math', 'High')"""
    parts = [p.strip() for p in text.split("|")]
    title = parts[0] if parts else ""
    subject = _normalize_subject(parts[1]) if len(parts) > 1 and parts[1] else "General"
    priority = _normalize_priority(parts[2]) if len(parts) > 2 and parts[2] else "Medium"
    return title, subject, priority


def render_task(t: dict) -> str:
    emoji = PRIORITY_EMOJI.get(t["priority"], "🟠")
    sub = SUBJECT_EMOJI.get(t["subject"], "📚")
    check = "✅" if t["status"] == "done" else "▫️"
    line = f"{check} <b>#{t['id']}</b> {t['title']}"
    line += f"\n     {sub} {t['subject']}  {emoji} {t['priority']}"
    if t.get("due_date"):
        line += f"  📅 {t['due_date']}"
    return line


def _task_list_text(tasks: list[dict], title: str = "📝 Your tasks") -> str:
    if not tasks:
        return f"{title}\n\nNothing here yet. Add one with <code>/add Finish chapter 3 | Math</code>"
    pending = [t for t in tasks if t["status"] == "pending"]
    done = [t for t in tasks if t["status"] == "done"]
    out = [f"{title}\n"]
    if pending:
        out.append("<b>Pending</b>")
        out += [render_task(t) for t in pending]
    if done:
        out.append("\n<b>Completed</b>")
        out += [render_task(t) for t in done]
    return "\n".join(out)


# --------------------------------------------------------------------------
# handlers
# --------------------------------------------------------------------------
async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Interactive add: /add with no args asks for title -> subject -> priority."""
    user_id = update.effective_user.id
    database.ensure_user(user_id, update.effective_user.username)

    # raw text so multi-word titles and '|' separators work
    body = strip_command(update.message.text, "add")

    if body:
        title, subject, priority = parse_task_args(body)
        if not title:
            await update.message.reply_text(CANCEL_TEXT)
            return ConversationHandler.END
        task_id = database.add_task(user_id, title, subject, priority)
        await update.message.reply_text(
            f"✅ Added task <b>#{task_id}</b>\n"
            f"   {SUBJECT_EMOJI.get(subject, '📚')} {subject}  "
            f"{PRIORITY_EMOJI.get(priority, '🟠')} {priority}",
            reply_markup=back_to_menu(),
        )
        return ConversationHandler.END

    context.user_data["draft_subject"] = "General"
    context.user_data["draft_priority"] = "Medium"
    await update.message.reply_text(
        "📝 <b>New task</b>\n\nWhat's the task? (send /cancel to stop)",
        reply_markup=back_to_menu(),
    )
    return ADD_TITLE


async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text("Empty task. Send /cancel to stop.")
        return ADD_TITLE
    context.user_data["draft_title"] = title
    buttons = [
        InlineKeyboardButton(s, callback_data=f"add:subject:{s}") for s in VALID_SUBJECTS[:4]
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(s, callback_data=f"add:subject:{s}") for s in VALID_SUBJECTS[4:]])
    rows.append([InlineKeyboardButton("⏭ Skip", callback_data="add:subject:General")])
    await update.message.reply_text(
        f"Task: <b>{title}</b>\n\nWhich subject?",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return ADD_SUBJECT


async def add_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    subject = update.callback_query.data.split(":")[2]
    context.user_data["draft_subject"] = subject
    buttons = [
        InlineKeyboardButton(f"{PRIORITY_EMOJI[p]} {p}", callback_data=f"add:priority:{p}")
        for p in VALID_PRIORITIES
    ]
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"Task: <b>{context.user_data['draft_title']}</b>\n"
        f"Subject: {SUBJECT_EMOJI.get(subject, '📚')} {subject}\n\nPriority?",
        reply_markup=InlineKeyboardMarkup([[b] for b in buttons]),
    )
    return ADD_PRIORITY


async def add_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    priority = update.callback_query.data.split(":")[2]
    title = context.user_data.get("draft_title", "")
    subject = context.user_data.get("draft_subject", "General")
    task_id = database.add_task(update.effective_user.id, title, subject, priority)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"✅ Task <b>#{task_id}</b> added!\n"
        f"   {SUBJECT_EMOJI.get(subject, '📚')} {subject}  "
        f"{PRIORITY_EMOJI.get(priority, '🟠')} {priority}",
        reply_markup=back_to_menu(),
    )
    return ConversationHandler.END


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tasks = database.list_tasks(user_id)
    await update.message.reply_text(
        _task_list_text(tasks),
        reply_markup=task_list_keyboard(tasks),
        parse_mode="HTML",
    )


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from datetime import datetime, timezone

    user_id = update.effective_user.id
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    due = database.tasks_due(user_id, today)
    counts = database.task_counts(user_id)
    week = database.last_days(user_id, 7)
    today_minutes = week[-1][1] if week else 0

    lines = ["📅 <b>Today</b>", f"📅 {today}", ""]
    if due:
        lines.append("<b>Due now</b>")
        lines += [render_task(t) for t in due]
    else:
        lines.append("✅ No tasks due. Enjoy the breathing room.")
    lines += [
        "",
        f"📈 Tasks: {counts['pending']} pending / {counts['done']} done",
        f"⏱ Studied today: {today_minutes} min",
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu())


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Usage: <code>/done 3</code> (task id)")
        return
    try:
        task_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Task id must be a number.")
        return
    ok = database.set_task_status(update.effective_user.id, task_id, "done")
    await update.message.reply_text("✅ Marked as done!" if ok else "❌ No such task.")


async def cmd_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Usage: <code>/del 3</code> (task id)")
        return
    try:
        task_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Task id must be a number.")
        return
    ok = database.delete_task(update.effective_user.id, task_id)
    await update.message.reply_text("🗑 Deleted." if ok else "❌ No such task.")


async def task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the ✅ / 🗑 buttons next to each task."""
    q = update.callback_query
    await q.answer()
    _, action, task_id = q.data.split(":")
    task_id = int(task_id)
    user_id = update.effective_user.id

    if action == "done":
        database.set_task_status(user_id, task_id, "done")
        note = "✅ Done!"
    elif action == "del":
        database.delete_task(user_id, task_id)
        note = "🗑 Deleted."
    else:
        return

    tasks = database.list_tasks(user_id)
    try:
        await q.edit_message_text(
            _task_list_text(tasks), reply_markup=task_list_keyboard(tasks), parse_mode="HTML"
        )
    except Exception:
        pass


# --------------------------------------------------------------------------
# wiring
# --------------------------------------------------------------------------
def register(app) -> None:
    app.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(r"^/add(@\w+)?(\s|$)"), cmd_add)],
            states={
                ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
                ADD_SUBJECT: [CallbackQueryHandler(add_subject, pattern=r"^add:subject:")],
                ADD_PRIORITY: [CallbackQueryHandler(add_priority, pattern=r"^add:priority:")],
            },
            fallbacks=[MessageHandler(filters.Regex(r"^/cancel$"), cancel_add)],
            allow_reentry=True,
            conversation_timeout=300,
        )
    )
    app.add_handler(MessageHandler(filters.Regex(r"^/tasks(@\w+)?(\s|$)"), cmd_tasks))
    app.add_handler(MessageHandler(filters.Regex(r"^/today(@\w+)?(\s|$)"), cmd_today))
    app.add_handler(MessageHandler(filters.Regex(r"^/done(@\w+)?(\s|$)"), cmd_done))
    app.add_handler(MessageHandler(filters.Regex(r"^/del(@\w+)?(\s|$)"), cmd_del))
    app.add_handler(CallbackQueryHandler(task_callback, pattern=r"^task:"))


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(CANCEL_TEXT, reply_markup=back_to_menu())
    return ConversationHandler.END

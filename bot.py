"""
StudyMate — a Telegram study helper bot.

Run it:
    pip install -r requirements.txt
    cp .env.example .env     # then paste your token
    python bot.py

Everything is driven by /help. Try /start to get the menu.
"""
import asyncio
import logging
import warnings

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import InvalidToken, NetworkError
from telegram.warnings import PTBUserWarning
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database
from handlers import cards, focus, quiz, stats, tasks
from keyboards import back_to_menu, focus_presets, main_menu, task_list_keyboard
from handlers.tasks import _task_list_text
from quiz_data import SUBJECTS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("studybot")

# The guided /add flow uses buttons inside a ConversationHandler. With the
# default per_message=False the conversation is tracked per (chat, user),
# which is exactly right here because the button sits on the bot's message,
# not the user's. The warning is noise for this design, so we hide it.
warnings.filterwarnings(
    "ignore", message=r".*CallbackQueryHandler.*", category=PTBUserWarning
)

HELP_TEXT = (
    "<b>📚 StudyMate — command list</b>\n\n"
    "<b>Tasks</b>\n"
    "<code>/add Finish chapter 3 | Math | High</code> — quick add\n"
    "<code>/add</code> — guided add (ask me for details)\n"
    "<code>/tasks</code> — your list\n"
    "<code>/today</code> — what's due + today's summary\n"
    "<code>/done 3</code> / <code>/del 3</code>\n\n"
    "<b>Focus</b>\n"
    "<code>/focus 25</code> — start a 25 minute focus session\n"
    "<code>/stop</code> — stop the timer (partial minutes still count)\n\n"
    "<b>Quiz & cards</b>\n"
    "<code>/quiz</code> — random quiz\n"
    "<code>/quiz Math</code> — quiz on one subject\n"
    "<code>/card What is 2+2? | 4 | Math</code> — add a flashcard\n"
    "<code>/cards</code> — view your deck\n"
    "<code>/review</code> — review your flashcards\n\n"
    "<b>Stats & settings</b>\n"
    "<code>/stats</code> — streaks, totals, 7 day chart\n"
    "<code>/remind 19:00</code> — daily reminder (use <code>/remind off</code> to cancel)\n"
    "<code>/timezone Asia/Karachi</code>\n\n"
    "<b>Subjects:</b> Math, Physics, Chemistry, Biology, History, English, Programming, General"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    database.ensure_user(user.id, user.username)
    name = user.first_name or "there"
    await update.message.reply_text(
        f"Hey {name}! 👋 I'm <b>StudyMate</b> — your study sidekick.\n\n"
        "Here's what I can do:\n"
        "• Track your tasks and deadlines\n"
        "• Run focus timers and log your study minutes\n"
        "• Quiz you and review your flashcards\n"
        "• Show your streak and stats\n\n"
        "Tap a button below or type <code>/help</code>.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML", reply_markup=back_to_menu())


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the main-menu buttons."""
    q = update.callback_query
    await q.answer()
    section = q.data.split(":")[1]

    if section == "home":
        await q.edit_message_text(
            "🏠 <b>Main menu</b>\n\nWhat do you want to do?",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
        return

    if section == "tasks":
        user_tasks = database.list_tasks(update.effective_user.id)
        await q.edit_message_text(
            _task_list_text(user_tasks),
            parse_mode="HTML",
            reply_markup=task_list_keyboard(user_tasks),
        )
        return

    if section == "focus":
        await q.edit_message_text(
            "⏱ <b>Focus timer</b>\n\nHow long do you want to study?",
            parse_mode="HTML",
            reply_markup=focus_presets(),
        )
        return

    if section == "quiz":
        await q.edit_message_text(
            "🧠 <b>Quiz</b>\n\nPick a subject, or type <code>/quiz</code> for a mixed one.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(s, callback_data=f"quizsubject:{s}")]
                for s in SUBJECTS
            ]),
        )
        return

    if section == "cards":
        count = database.flashcard_count(update.effective_user.id)
        await q.edit_message_text(
            f"🗂 <b>Flashcards</b>\n\nYou have <b>{count}</b> card{'s' if count != 1 else ''}.\n\n"
            "• <code>/card Question | Answer | Subject</code>\n"
            "• <code>/review</code> — review them\n"
            "• <code>/cards</code> — list them",
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )
        return

    if section == "stats":
        await q.edit_message_text(
            stats.build_stats_text(update.effective_user.id),
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )
        return

    if section == "reminder":
        user = database.get_user(update.effective_user.id)
        current = user.get("reminder_time")
        state = f"⏰ Reminder: <b>{current}</b> daily." if current else "⏰ No daily reminder set."
        await q.edit_message_text(
            f"{state}\n\nSet with <code>/remind 19:00</code>, clear with <code>/remind off</code>",
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )
        return


async def quiz_subject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subject picked from the quiz menu -> start that quiz."""
    q = update.callback_query
    await q.answer()
    subject = q.data.split(":")[1]
    context.user_data["_uid"] = update.effective_user.id
    await quiz.start_quiz(update, context, subject)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error", exc_info=context.error)
    try:
        if update and hasattr(update, "effective_message") and update.effective_message:
            await update.effective_message.reply_text("⚠️ Something broke on my side. Try that again.")
    except Exception:
        pass


def build_application(token: str | None = None) -> Application:
    """Build the Application and register every handler.

    Kept separate from main() so tests can build the real thing.
    """
    app = (
        Application.builder()
        .token(token or config.TELEGRAM_TOKEN)
        .concurrent_updates(False)
        .build()
    )

    # core commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))

    # feature modules
    tasks.register(app)
    focus.register(app)
    quiz.register(app)
    cards.register(app)
    stats.register(app)

    # shared buttons
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(quiz_subject_callback, pattern=r"^quizsubject:"))

    app.add_error_handler(error_handler)
    return app


def print_invalid_token_help() -> None:
    print("=" * 60)
    print("❌ Telegram rejected your token.")
    print("")
    print("That usually means one of:")
    print("  • you copied it with a typo or missing characters")
    print("  • you pasted 'BotFather' instead of the token itself")
    print("  • you revoked it — run /revoke in BotFather for a new one")
    print("")
    print("Your token looks like: 123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print("=" * 60)


def verify_token() -> str | None:
    """Ask Telegram who this bot is. Returns the username, or None if broken."""
    try:
        me = asyncio.run(Bot(config.TELEGRAM_TOKEN).get_me())
        return me.username
    except InvalidToken:
        print_invalid_token_help()
        return None
    except NetworkError:
        print("⚠️  Can't reach Telegram to verify the token — starting anyway.")
        return "unknown"
    except Exception:
        return "unknown"


def main() -> None:
    if not config.token_present():
        print("=" * 60)
        print("❌ No Telegram token found!")
        print("")
        print("Fix it in 30 seconds:")
        print("  1. Open Telegram, message @BotFather")
        print("  2. Send /newbot, follow the prompts")
        print("  3. Copy the token it gives you")
        print("  4. Copy .env.example to .env and paste the token")
        print("  5. Run: python bot.py")
        print("=" * 60)
        return

    username = verify_token()
    if username is None:
        return

    database.init_db()
    app = build_application()

    logger.info("StudyMate is starting up...")
    print(f"✅ StudyMate is running as @{username}. Press Ctrl+C to stop.\n")
    try:
        app.run_polling(drop_pending_updates=True)
    except InvalidToken:
        print_invalid_token_help()
    except NetworkError as err:
        print(f"❌ Can't reach Telegram right now: {err}")
        print("Check your internet connection and try again.")


if __name__ == "__main__":
    main()

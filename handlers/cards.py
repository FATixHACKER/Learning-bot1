"""Flashcards: build your own deck and review it."""
import random

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

import database
from keyboards import back_to_menu, flashcard_review
from utils import strip_command

REVIEW_SIZE = 10


async def cmd_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /card What is 2+2? | 4 | Math """
    user_id = update.effective_user.id
    database.ensure_user(user_id, update.effective_user.username)

    # read the raw text: questions and answers can contain spaces
    raw = strip_command(update.message.text, "card")
    if "|" not in raw:
        await update.message.reply_text(
            "Usage: <code>/card Question | Answer | Subject</code>\n\n"
            "Example: <code>/card Capital of France | Paris | Geography</code>"
        )
        return

    parts = [p.strip() for p in raw.split("|")]
    question = parts[0]
    answer = parts[1] if len(parts) > 1 else ""
    subject = parts[2] if len(parts) > 2 and parts[2] else "General"

    if not question or not answer:
        await update.message.reply_text(
            "Both a question and an answer are needed.\n"
            "Example: <code>/card Capital of France | Paris</code>"
        )
        return

    card_id = database.add_flashcard(user_id, question, answer, subject)
    await update.message.reply_text(
        f"🗂 Card <b>#{card_id}</b> saved!\n\n"
        f"<b>Q:</b> {question}\n<b>A:</b> {answer}\n\n"
        "Review the deck with /review",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )


async def cmd_cards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    count = database.flashcard_count(user_id)
    cards = database.list_flashcards(user_id, limit=20)
    if not cards:
        await update.message.reply_text(
            "🗂 Your deck is empty.\n\nAdd one with <code>/card Question | Answer</code>",
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )
        return

    lines = [f"🗂 <b>Your flashcards</b> ({count} total)", ""]
    for c in cards[:15]:
        lines.append(f"<b>#{c['id']}</b> {c['question']}")
        lines.append(f"    → {c['answer']}  <i>({c['subject']})</i>")
    if count > 15:
        lines.append(f"\n<i>...and {count - 15} more</i>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu())


async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    cards = database.list_flashcards(user_id, limit=REVIEW_SIZE)
    if not cards:
        await update.message.reply_text(
            "🗂 No flashcards to review yet. Add some with <code>/card Q | A</code>",
            parse_mode="HTML",
        )
        return

    session = {
        "cards": cards,
        "index": 0,
        "known": 0,
        "again": 0,
        "revealed": False,
    }
    context.user_data["review"] = session
    await _send_card(update, context)


async def _send_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = context.user_data.get("review")
    if not session:
        return
    cards = session["cards"]
    if session["index"] >= len(cards):
        total = session["known"] + session["again"]
        pct = round(session["known"] * 100 / total) if total else 0
        await update.message.reply_text(
            f"🏁 <b>Review done!</b>\n\n"
            f"✅ Known: {session['known']}\n"
            f"❌ Again: {session['again']}\n\n"
            f"Recall: <b>{pct}%</b>",
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )
        context.user_data.pop("review", None)
        return

    card = cards[session["index"]]
    session["revealed"] = False
    await update.message.reply_text(
        f"🗂 <b>Card {session['index'] + 1}/{len(cards)}</b>\n"
        f"Subject: {card['subject']}\n\n"
        f"<b>{card['question']}</b>",
        parse_mode="HTML",
        reply_markup=flashcard_review(session["index"] + 1, card["id"]),
    )


async def card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()

    parts = q.data.split(":")
    action = parts[1]
    session = context.user_data.get("review")
    if not session:
        await q.edit_message_text("Review session ended. Start again with /review", reply_markup=back_to_menu())
        return

    card = session["cards"][session["index"]]

    if action == "reveal":
        session["revealed"] = True
        await q.edit_message_text(
            f"🗂 <b>Card {session['index'] + 1}/{len(session['cards'])}</b>\n\n"
            f"<b>{card['question']}</b>\n\n"
            f"👉 <b>{card['answer']}</b>",
            parse_mode="HTML",
            reply_markup=flashcard_review(session["index"] + 1, card["id"]),
        )
        return

    if action == "known":
        session["known"] += 1
    elif action == "again":
        session["again"] += 1
    else:
        return

    session["index"] += 1
    await _send_card(update, context)


async def cmd_delcard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Usage: <code>/delcard 3</code>")
        return
    try:
        card_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Card id must be a number.")
        return
    ok = database.delete_flashcard(update.effective_user.id, card_id)
    await update.message.reply_text("🗑 Card deleted." if ok else "❌ No such card.")


def register(app) -> None:
    app.add_handler(MessageHandler(filters.Regex(r"^/card(@\w+)?(\s|$)"), cmd_card))
    app.add_handler(MessageHandler(filters.Regex(r"^/cards(@\w+)?(\s|$)"), cmd_cards))
    app.add_handler(MessageHandler(filters.Regex(r"^/review(@\w+)?(\s|$)"), cmd_review))
    app.add_handler(MessageHandler(filters.Regex(r"^/delcard(@\w+)?(\s|$)"), cmd_delcard))
    app.add_handler(CallbackQueryHandler(card_callback, pattern=r"^card:"))

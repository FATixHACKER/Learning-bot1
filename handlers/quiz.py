"""Quiz mode: /quiz pulls questions and marks you in Telegram."""
import random

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

import database
from keyboards import back_to_menu, quiz_options
from quiz_data import QUESTION_BANK, SUBJECTS


def build_question(subject: str) -> dict:
    """Turn a bank entry into a shuffled multiple-choice question."""
    entry = random.choice(QUESTION_BANK[subject])
    options = list(entry["options"])
    answer = entry["answer"]
    if answer not in options:
        options.append(answer)
    random.shuffle(options)
    return {
        "q": entry["q"],
        "options": options,
        "answer": answer,
        "subject": subject,
    }


def next_question(context: ContextTypes.DEFAULT_TYPE, subject: str | None = None) -> dict | None:
    """Pull the next question. Mixes bank questions with your own flashcards."""
    pool_subject = subject or random.choice(SUBJECTS)

    # 40% chance to use one of the user's own flashcards if they have any
    cards = database.list_flashcards(context.user_data.get("_uid", 0), pool_subject)
    if cards and random.random() < 0.4:
        card = random.choice(cards)
        answer = card["answer"]
        distractors = [c["answer"] for c in cards if c["answer"] != answer]
        if len(distractors) < 3:
            for entry in QUESTION_BANK.get(pool_subject, []):
                if entry["answer"] != answer and entry["answer"] not in distractors:
                    distractors.append(entry["answer"])
                if len(distractors) >= 3:
                    break
        options = [answer] + distractors[:3]
        random.shuffle(options)
        return {"q": card["question"], "options": options, "answer": answer, "subject": pool_subject}

    return build_question(pool_subject)


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    database.ensure_user(user_id, update.effective_user.username)
    context.user_data["_uid"] = user_id

    subject = None
    if context.args:
        raw = context.args[0].strip().title()
        if raw in QUESTION_BANK:
            subject = raw
        else:
            matches = [s for s in SUBJECTS if s.lower().startswith(raw.lower())]
            if matches:
                subject = matches[0]
            else:
                await update.message.reply_text(
                    f"Unknown subject <code>{raw}</code>.\n"
                    f"Try one of: {', '.join(SUBJECTS)}"
                )
                return

    await start_quiz(update, context, subject)


async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, subject: str | None = None) -> None:
    """Begin a quiz session. subject=None means mixed subjects."""
    context.user_data["quiz"] = {
        "subject": subject,
        "index": 0,
        "correct": 0,
        "total": 0,
        "current": None,
    }
    await _send_question(update, context)


async def _send_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quiz = context.user_data.setdefault("quiz", {})
    q = next_question(context, quiz.get("subject"))
    if q is None:
        await update.message.reply_text("No questions available.")
        return

    quiz["current"] = q
    quiz["total"] += 1

    options = "\n".join(f"{i+1}. {o}" for i, o in enumerate(q["options"]))
    text = (
        f"🧠 <b>Question {quiz['total']}</b> — {q['subject']}\n\n"
        f"<b>{q['q']}</b>\n\n{options}"
    )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=quiz_options(quiz["total"], q["options"]),
    )


async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()

    _, _, idx, choice = q.data.split(":")
    idx, choice = int(idx), int(choice)

    quiz = context.user_data.get("quiz", {})
    current = quiz.get("current")
    if not current:
        await q.edit_message_text("Session expired. Start again with /quiz", reply_markup=back_to_menu())
        return

    picked = current["options"][choice]
    correct = picked == current["answer"]

    if correct:
        quiz["correct"] = quiz.get("correct", 0) + 1
        head = "✅ <b>Correct!</b>"
    else:
        head = f"❌ <b>Not quite.</b> The answer is <b>{current['answer']}</b>"

    await q.edit_message_text(
        f"{head}\n\n<b>{current['q']}</b>",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )

    # next question
    if quiz.get("total", 0) >= 5:
        correct_n = quiz.get("correct", 0)
        total_n = quiz.get("total", 0)
        database.log_quiz(context.user_data.get("_uid", 0), correct_n, total_n)
        pct = round(correct_n * 100 / total_n)
        bar = "🟩" * correct_n + "🟥" * (total_n - correct_n)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"🏁 <b>Quiz finished!</b>\n\n"
                f"{bar}\n\n"
                f"Score: <b>{correct_n}/{total_n}</b> ({pct}%)\n\n"
                + ("🔥 You're on fire. Keep it up!" if pct >= 80 else "📚 Review the ones you missed and try again.")
            ),
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )
        context.user_data.pop("quiz", None)
    else:
        await _send_question(update, context)


def register(app) -> None:
    app.add_handler(MessageHandler(filters.Regex(r"^/quiz(@\w+)?(\s|$)"), cmd_quiz))
    app.add_handler(CallbackQueryHandler(quiz_answer, pattern=r"^quiz:ans:"))

"""Inline keyboards — the buttons you tap under a message."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import FOCUS_PRESETS

# emoji for each priority level
PRIORITY_EMOJI = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
SUBJECT_EMOJI = {
    "Math": "➗", "Physics": "⚛️", "Chemistry": "🧪", "Biology": "🧬",
    "History": "🏛️", "English": "📖", "Programming": "💻", "General": "📚",
}


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Tasks", callback_data="menu:tasks"),
            InlineKeyboardButton("⏱ Focus", callback_data="menu:focus"),
        ],
        [
            InlineKeyboardButton("🧠 Quiz", callback_data="menu:quiz"),
            InlineKeyboardButton("📊 Stats", callback_data="menu:stats"),
        ],
        [
            InlineKeyboardButton("🗂 Flashcards", callback_data="menu:cards"),
            InlineKeyboardButton("⏰ Reminder", callback_data="menu:reminder"),
        ],
    ])


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Menu", callback_data="menu:home")],
    ])


def focus_presets() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(f"{m} min", callback_data=f"focus:start:{m}")
        for m in FOCUS_PRESETS
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("✖️ Cancel timer", callback_data="focus:cancel")])
    return InlineKeyboardMarkup(rows)


def task_list_keyboard(tasks: list[dict]) -> InlineKeyboardMarkup:
    """One 'Done' button per pending task plus a delete button."""
    rows = []
    for t in tasks:
        if t["status"] == "pending":
            rows.append([
                InlineKeyboardButton(
                    f"✅ {t['title'][:28]}",
                    callback_data=f"task:done:{t['id']}",
                ),
                InlineKeyboardButton("🗑", callback_data=f"task:del:{t['id']}"),
            ])
    rows.append([InlineKeyboardButton("🏠 Menu", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def quiz_options(question_id: int, options: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(opt[:40], callback_data=f"quiz:ans:{question_id}:{i}")]
        for i, opt in enumerate(options)
    ]
    rows.append([InlineKeyboardButton("🏠 Menu", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def flashcard_review(question_id: int, card_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👀 Show answer", callback_data=f"card:reveal:{question_id}"),
        ],
        [
            InlineKeyboardButton("✅ I knew it", callback_data=f"card:known:{question_id}"),
            InlineKeyboardButton("❌ Again", callback_data=f"card:again:{question_id}"),
        ],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu:home")],
    ])

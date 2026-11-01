# 🎓 StudyMate — a Telegram bot for studying

A working study assistant for Telegram: track tasks, run focus timers, quiz
yourself, review flashcards, and watch your streak grow.

Built with Python + `python-telegram-bot`. **No database server needed** —
everything lives in one SQLite file next to the code.

---

## What it does

| Feature | Commands |
|---|---|
| **Tasks** — add, list, complete, delete, see what's due today | `/add`, `/tasks`, `/today`, `/done 3`, `/del 3` |
| **Focus timer** — Pomodoro sessions that log your minutes | `/focus 25`, `/stop` |
| **Quiz** — 46 built-in questions across 8 subjects | `/quiz`, `/quiz Math` |
| **Flashcards** — build your own deck and review it | `/card`, `/cards`, `/review`, `/delcard 3` |
| **Stats** — streak, totals, a 7-day chart | `/stats` |
| **Reminders** — a daily nudge at the time you choose | `/remind 19:00`, `/remind off` |
| **Settings** — timezone | `/timezone Asia/Karachi` |

---

## Setup (about 5 minutes)

### 1. Get a bot token

1. Open Telegram, search for **@BotFather**, start it.
2. Send `/newbot`.
3. Give it a name → `StudyMate`
4. Give it a username → `studymate_bot` (must end in `bot`)
5. BotFather replies with a token like `7123456789:AAHx...`

### 2. Install Python 3.11+

Check with `python3 --version`. If it's older, grab it from python.org.

### 3. Get the code

```bash
cd study-bot
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Add your token

```bash
cp .env.example .env
```

Open `.env` in any text editor and paste your token:

```
TELEGRAM_TOKEN=7123456789:AAHxYourTokenHere
```

### 5. Run it

```bash
python bot.py
```

You should see:

```
✅ StudyMate is running as @studymate_bot. Press Ctrl+C to stop.
```

### 6. Talk to it

Open Telegram, search for your bot's username, hit **Start**, and send `/help`.

---

## Project layout

```
study-bot/
├── bot.py            ← entry point: builds the app, wires up handlers
├── config.py         ← all settings live here
├── database.py       ← SQLite storage (5 tables)
├── keyboards.py      ← the inline buttons under messages
├── quiz_data.py      ← the built-in question bank
├── utils.py          ← small helpers
├── handlers/
│   ├── tasks.py      ← /add /tasks /today /done /del
│   ├── focus.py      ← /focus /stop
│   ├── quiz.py       ← /quiz
│   ├── cards.py      ← /card /cards /review
│   └── stats.py      ← /stats /remind /timezone
├── test_logic.py     ← 29 tests: database + parsing
├── test_handlers.py  ← 56 tests: every command, Telegram mocked
├── test_wiring.py    ← 29 tests: routing + startup
└── requirements.txt
```

Run all tests:

```bash
python test_logic.py && python test_handlers.py && python test_wiring.py
```

---

## Data & privacy

- Everything is stored in `studybot.sqlite3` in this folder.
- Delete that file to wipe all data.
- The bot works one-on-one in private chats. In groups, it responds to commands
  addressed to it.

---

## Common problems

**"No Telegram token found"** — you didn't create `.env`, or the token is empty.
Run `cp .env.example .env` and paste your token in.

**"Telegram rejected your token"** — typo in the token, or you revoked it.
Run `/revoke` in BotFather to get a new one.

**`ModuleNotFoundError: No module named 'telegram'`** — the virtualenv isn't
active. Run `source .venv/bin/activate` first.

**Bot doesn't respond** — check the terminal where it's running for errors.
Also make sure you sent the command as `/tasks`, not just "tasks".

**Reminder fires at the wrong hour** — reminders use UTC. Set your timezone
with `/timezone Asia/Karachi` (note: this stores the setting, but the daily
reminder currently runs on the server clock).

---

## Ideas to extend it

Each of these is a small, self-contained change — great practice:

- 📚 **Due dates** — `/add Homework | Math | High | tomorrow`
- 📧 **Weekly summary** — a job that posts your Sunday stats
- 🏆 **Leaderboard** — a table of who studied most this week
- 🎨 **Custom themes** — change the emoji in `keyboards.py`
- 🤖 **AI tutoring** — hook up an LLM API for custom explanations
- 📊 **Export** — dump your study log to CSV

---

## Want to keep it running 24/7?

The bot stops when you close the terminal. To keep it alive:

- **Free & easy** — run it on a Raspberry Pi or old laptop
- **Free tier** — Railway, Fly.io, or PythonAnywhere (background task)
- **Cheapest VPS** — DigitalOcean/Hetzner, ~$4/month, then use `systemd` or
  `screen` to keep it running

---

Happy studying! 🚀

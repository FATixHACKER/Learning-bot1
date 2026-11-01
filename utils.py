"""Small helpers shared across handlers."""
import re


def strip_command(text: str | None, command: str) -> str:
    """
    Remove the leading '/command' (plus any @botname) from a message.

    Telegram splits arguments on spaces, so '/card Capital of France | Paris'
    arrives as ['Capital', 'of', 'France', '|', 'Paris'].
    For anything multi-word we read the raw message text instead and split
    it ourselves — this helper grabs that raw remainder.

        strip_command('/card Capital of France | Paris', 'card')
        -> 'Capital of France | Paris'
    """
    if not text:
        return ""
    pattern = rf"^/{re.escape(command)}(@\w+)?\s*(.*)$"
    match = re.match(pattern, text.strip(), re.S)
    return match.group(2).strip() if match else ""

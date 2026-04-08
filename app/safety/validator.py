"""
app/safety/validator.py
SQL safety layer — whitelist-only approach.
Rejects dangerous SQL before execution.
"""

import re
from pathlib import Path
from typing import Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import ALLOWED_SQL_COMMANDS, BLOCKED_SQL_COMMANDS
from logger import get_logger

log = get_logger("safety")


def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Returns (is_safe: bool, reason: str).
    Only SELECT, INSERT, UPDATE are allowed.
    """
    if not sql or not sql.strip():
        return False, "SQL is empty"

    clean = sql.strip().rstrip(";")

    # Extract first keyword
    first_word = re.split(r"\s+", clean.upper())[0]

    # Block dangerous commands
    if first_word in BLOCKED_SQL_COMMANDS:
        msg = f"Blocked operation: {first_word}"
        log.warning("SAFETY BLOCK: %s | SQL: %s", msg, sql[:100])
        return False, msg

    # Must be in allow-list
    if first_word not in ALLOWED_SQL_COMMANDS:
        msg = f"Unknown/disallowed SQL command: {first_word}"
        log.warning("SAFETY BLOCK: %s | SQL: %s", msg, sql[:100])
        return False, msg

    # Deep scan: catch embedded dangerous keywords (SQL injection patterns)
    upper_sql = clean.upper()
    for bad in BLOCKED_SQL_COMMANDS:
        # Match as whole word to avoid false positives (e.g. 'CREATED')
        if re.search(rf"\b{bad}\b", upper_sql):
            msg = f"Embedded dangerous keyword: {bad}"
            log.warning("SAFETY BLOCK: %s | SQL: %s", msg, sql[:100])
            return False, msg

    # Block multiple statements (semicolons in middle = injection attempt)
    if ";" in clean:
        msg = "Multiple statements not allowed"
        log.warning("SAFETY BLOCK: %s | SQL: %s", msg, sql[:100])
        return False, msg

    log.debug("SQL passed safety: %s", sql[:80])
    return True, "ok"


def safe_error_hinglish(reason: str) -> str:
    """Return a user-friendly Hinglish error for blocked SQL."""
    return f"⚠️  Yeh kaam nahi kar sakta: {reason}. Kripya dobara try karein."

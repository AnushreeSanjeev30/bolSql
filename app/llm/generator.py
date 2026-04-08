"""
app/llm/generator.py
LLM integration — SQL generation + Hinglish response generation.
Supports Groq (free) and Ollama (offline) backends.
"""

import re
import json
from typing import Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import (
    LLM_PROVIDER, GROQ_API_KEY, LLM_MODEL,
    OLLAMA_MODEL, DB_SCHEMA
)
from logger import get_logger

log = get_logger("llm")


# ── SQL Generation Prompt ─────────────────────────────────────────────────────

SQL_SYSTEM_PROMPT = """You are a Text-to-SQL assistant for an Indian kirana (grocery) shop.
You convert Hinglish (Hindi + English mixed) voice commands into SQLite SQL queries.

{schema}

STRICT RULES:
1. Output ONLY the SQL query — no explanation, no markdown, no backticks
2. Only use SELECT, INSERT, UPDATE — never DELETE, DROP, ALTER
3. Always use LOWER(name) for item name comparisons
4. For quantity changes: use "quantity + X" or "quantity - X", never hard-code absolute values
5. If item name is ambiguous, use LIKE: WHERE LOWER(name) LIKE '%item%'
6. For listing all items: SELECT name, quantity, unit FROM inventory ORDER BY name
7. For low stock: WHERE quantity < 5

SIMILAR EXAMPLES FROM DATABASE:
{examples}

EXTRACTED INFO:
Intent: {intent}
Item: {item}
Quantity: {quantity}
Unit: {unit}
"""

# ── Response Generation Prompt ────────────────────────────────────────────────

RESPONSE_SYSTEM_PROMPT = """You are a helpful assistant for an Indian kirana shop.
Convert database results into natural, friendly Hinglish (Hindi + English mix).

Rules:
- Keep responses SHORT (1-2 sentences max)
- Use Hinglish naturally: "ho gaya", "bacha hai", "available hai"
- Include numbers and units clearly
- Be shopkeeper-friendly and warm
- Never use English only — always mix Hindi

Examples:
- Stock added: "50kg atta successfully add ho gaya ✓"
- Stock sold: "10 packet biscuit ka sale record ho gaya ✓"
- Stock check: "Aapke paas 30kg chawal bacha hai"
- Low stock: "Warning: atta sirf 2kg bacha hai, restock karo"
- Not found: "Yeh item inventory mein nahi mila"
"""


class LLMClient:
    def __init__(self):
        self._groq_client = None
        self._provider = LLM_PROVIDER.lower()
        self._init_client()

    def _init_client(self):
        if self._provider == "groq":
            if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
                log.warning("GROQ_API_KEY not set. LLM features will be limited.")
                return
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=GROQ_API_KEY)
                log.info("Groq LLM client initialized (model: %s)", LLM_MODEL)
            except ImportError:
                log.error("groq package not installed. Run: pip install groq")
        elif self._provider == "ollama":
            log.info("Using Ollama backend (model: %s)", OLLAMA_MODEL)
        else:
            log.warning("Unknown LLM_PROVIDER: %s", self._provider)

    def _call_groq(self, system: str, user: str, max_tokens: int = 200) -> Optional[str]:
        if not self._groq_client:
            return None
        try:
            resp = self._groq_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.05,   # Low temp = deterministic SQL
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error("Groq API call failed: %s", e)
            return None

    def _call_ollama(self, system: str, user: str) -> Optional[str]:
        try:
            import urllib.request
            payload = json.dumps({
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": 0.05},
            }).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data["message"]["content"].strip()
        except Exception as e:
            log.error("Ollama call failed: %s", e)
            return None

    def _call_llm(self, system: str, user: str, max_tokens: int = 200) -> Optional[str]:
        if self._provider == "groq":
            return self._call_groq(system, user, max_tokens)
        elif self._provider == "ollama":
            return self._call_ollama(system, user)
        return None

    def generate_sql(
        self,
        raw_query: str,
        intent: str,
        item: Optional[str],
        quantity: Optional[float],
        unit: Optional[str],
        examples_text: str,
        max_retries: int = 2,
    ) -> Optional[str]:
        """
        Generate SQL from the parsed query. Retries on invalid SQL.
        Returns cleaned SQL string or None.
        """
        system = SQL_SYSTEM_PROMPT.format(
            schema=DB_SCHEMA,
            examples=examples_text or "No similar examples found.",
            intent=intent,
            item=item or "unknown",
            quantity=quantity or "unknown",
            unit=unit or "unknown",
        )

        for attempt in range(max_retries + 1):
            raw = self._call_llm(system, raw_query)
            if not raw:
                log.warning("LLM returned empty response (attempt %d)", attempt + 1)
                continue

            sql = self._clean_sql(raw)
            if sql:
                log.info("LLM generated SQL (attempt %d): %s", attempt + 1, sql[:100])
                return sql
            else:
                log.warning("LLM returned invalid SQL (attempt %d): %s", attempt + 1, raw[:100])

        log.error("SQL generation failed after %d attempts", max_retries + 1)
        return None

    def generate_response(self, raw_query: str, sql: str, db_result: list, intent: str) -> str:
        """
        Generate a natural Hinglish response from DB results.
        Falls back to template-based response if LLM unavailable.
        """
        result_summary = json.dumps(db_result[:5], ensure_ascii=False, indent=2)
        user_prompt = f"""
User said: "{raw_query}"
SQL executed: {sql}
Database result: {result_summary}
Intent: {intent}

Generate a short, friendly Hinglish response.
"""
        response = self._call_llm(RESPONSE_SYSTEM_PROMPT, user_prompt, max_tokens=100)
        if response:
            return response

        # Template fallback (no LLM needed)
        return self._template_response(intent, db_result, raw_query)

    def _template_response(self, intent: str, results: list, query: str) -> str:
        """Hardcoded Hinglish templates when LLM unavailable."""
        if not results:
            return "✓ Kaam ho gaya"

        if intent == "QUERY" and results:
            row = results[0]
            if "name" in row and "quantity" in row:
                name = row.get("name", "item")
                qty = row.get("quantity", "?")
                unit = row.get("unit", "")
                return f"Aapke paas {qty} {unit} {name} bacha hai"
            # Multiple rows
            if len(results) > 1:
                items = ", ".join(
                    f"{r.get('name','?')} ({r.get('quantity','?')} {r.get('unit','')})"
                    for r in results[:5]
                )
                return f"Stock: {items}"

        if intent == "ADD":
            return "✓ Stock mein add ho gaya"
        if intent == "SELL":
            return "✓ Sale record ho gaya"

        return "✓ Kaam ho gaya"

    @staticmethod
    def _clean_sql(raw: str) -> Optional[str]:
        """Strip markdown, extra text; return clean SQL or None."""
        # Remove markdown code fences
        sql = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip()
        sql = sql.strip("`").strip()

        # Take only the first line that looks like SQL
        for line in sql.split("\n"):
            line = line.strip()
            if re.match(r"^(SELECT|INSERT|UPDATE|WITH)\b", line, re.IGNORECASE):
                return line.rstrip(";")

        # Try whole string
        if re.match(r"^(SELECT|INSERT|UPDATE|WITH)\b", sql, re.IGNORECASE):
            return sql.rstrip(";")

        return None


# Singleton
_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client

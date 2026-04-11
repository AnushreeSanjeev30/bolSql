"""
app/llm/generator.py
LLM integration — SQL generation + Multi-language response generation.
Supports Groq (free) and Ollama (offline) backends.
Supports Hinglish, Hindi, and Tamil responses.
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
8. For price updates: UPDATE inventory SET price = price + X WHERE LOWER(name) LIKE '%item%'
9. For price check: SELECT name, price FROM inventory WHERE LOWER(name) LIKE '%item%'
10. For orders: SELECT item_name, quantity, timestamp FROM transactions WHERE DATE(timestamp) = DATE('now')
11. For category price updates: UPDATE inventory SET price = price * 1.1 WHERE category LIKE '%category%'
12. For price rollback: SELECT old_price FROM price_history WHERE item_id = (SELECT id FROM inventory WHERE LOWER(name) LIKE '%item%') ORDER BY changed_at DESC LIMIT 1
13. For expiry checks: SELECT name, expiry_date FROM inventory WHERE expiry_date IS NOT NULL AND datetime(expiry_date) <= datetime('now', '+7 days')
14. For viewing orders: SELECT * FROM orders WHERE status = 'pending' ORDER BY order_date DESC
15. You MAY use JOINs and subqueries. Prefer these joins when needed:
    - transactions.customer_id = customers.customer_id
    - transactions.item_id = inventory.id
    - customer_segments.customer_id = customers.customer_id
    - orders.customer_id = customers.customer_id

EXAMPLES:
- Stock correction: UPDATE inventory SET quantity = 30 WHERE LOWER(name) LIKE '%dal%'
- Price update: UPDATE inventory SET price = price + 5 WHERE LOWER(name) LIKE '%atta%'
- Price check: SELECT name, price FROM inventory WHERE LOWER(name) LIKE '%atta%'
- Low stock: SELECT name, quantity FROM inventory WHERE quantity < 5 ORDER BY quantity
- Pending orders: SELECT item_name, quantity FROM transactions WHERE DATE(timestamp) = DATE('now')
- Category price update: UPDATE inventory SET price = price * 1.1 WHERE category LIKE '%masala%'
- Price rollback: SELECT old_price FROM price_history WHERE item_id = (SELECT id FROM inventory WHERE LOWER(name) LIKE '%atta%') ORDER BY changed_at DESC LIMIT 1
- Expiry check: SELECT name, expiry_date FROM inventory WHERE expiry_date IS NOT NULL AND datetime(expiry_date) <= datetime('now', '+7 days') ORDER BY expiry_date
- View all orders: SELECT * FROM orders WHERE status = 'pending' ORDER BY order_date DESC

SIMILAR EXAMPLES FROM DATABASE:
{examples}

EXTRACTED INFO:
Intent: {intent}
Item: {item}
Quantity: {quantity}
Unit: {unit}
"""

# ── Response Generation Prompts ────────────────────────────────────────────────

RESPONSE_SYSTEM_PROMPT_HINGLISH = """You are a helpful assistant for an Indian kirana shop.
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

RESPONSE_SYSTEM_PROMPT_TAMIL = """You are a helpful assistant for an Indian kirana shop.
Convert database results into natural, friendly Tamil.

Rules:
- Keep responses SHORT (1-2 sentences max)
- Use Tamil naturally: "aagum", "irukku", "pannathu", "koduthu"
- Include numbers and units clearly
- Be shopkeeper-friendly and warm
- Always respond in Tamil script and Roman Tamil mix (Tamglish)

Examples:
- Stock added: "50kg aatta successfully add pannathu ✓"
- Stock sold: "10 packet biscuit sale record pannathu ✓"
- Stock check: "Unakku 30kg arisi irukku"
- Low stock: "Warning: aatta sirf 2kg irukku, puthiya stock vaangikola"
- Not found: "Ivar item inventory la illai"
"""

RESPONSE_SYSTEM_PROMPT = RESPONSE_SYSTEM_PROMPT_HINGLISH  # Default


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

    def generate_response(self, raw_query: str, sql: str, db_result: list, intent: str, language: str = "hinglish") -> str:
        """
        Generate a natural response from DB results in the specified language.
        Falls back to template-based response if LLM unavailable.
        
        Args:
            raw_query: Original user query
            sql: Generated SQL
            db_result: Database query results
            intent: Query intent
            language: "hinglish", "hindi", or "tamil" (default: "hinglish")
        """
        # Select appropriate prompt
        if language.lower() == "tamil":
            system_prompt = RESPONSE_SYSTEM_PROMPT_TAMIL
            lang_instruction = "Generate a short, friendly Tamil response in Tamglish (Tamil + Roman mix)."
        else:
            system_prompt = RESPONSE_SYSTEM_PROMPT_HINGLISH
            lang_instruction = "Generate a short, friendly Hinglish response."
        
        result_summary = json.dumps(db_result[:5], ensure_ascii=False, indent=2)
        user_prompt = f"""
User said: "{raw_query}"
SQL executed: {sql}
Database result: {result_summary}
Intent: {intent}

{lang_instruction}
"""
        response = self._call_llm(system_prompt, user_prompt, max_tokens=100)
        if response:
            return response

        # Template fallback (no LLM needed)
        return self._template_response(intent, db_result, raw_query, language=language)

    def _template_response(self, intent: str, results: list, query: str, language: str = "hinglish") -> str:
        """
        Hardcoded response templates when LLM unavailable.
        
        Args:
            intent: Query intent
            results: Database results
            query: Original query
            language: "hinglish", "hindi", or "tamil" (default: "hinglish")
        """
        # Tamil templates
        if language.lower() == "tamil":
            return self._template_response_tamil(intent, results)
        
        # Default Hinglish templates
        return self._template_response_hinglish(intent, results)
    
    def _template_response_tamil(self, intent: str, results: list) -> str:
        """Hardcoded Tamil templates when LLM unavailable."""
        if not results:
            if intent == "PRICE":
                return "❌ Item kaaga vidham vela database la illa"
            elif intent == "CORRECTION":
                return "❌ Stock correction panaka mudiyala"
            elif intent == "ORDER":
                return "❌ Order data illa"
            elif intent == "ROLLBACK":
                return "❌ Price history illa, rollback panaka mudiyala"
            elif intent == "EXPIRY":
                return "✓ Yaar item expire aagum kalai illa ippothu"
            return "✓ Pannathu aagum"

        if intent == "QUERY" and results:
            row = results[0]
            if "name" in row and "quantity" in row:
                name = row.get("name", "item")
                qty = row.get("quantity", "?")
                unit = row.get("unit", "")
                if len(results) == 1:
                    return f"Unakku {qty} {unit} {name} irukku"
            
            if len(results) > 1:
                items_list = []
                for r in results:
                    name = r.get('name', '?')
                    qty = r.get('quantity', '?')
                    unit = r.get('unit', '')
                    items_list.append(f"{qty}{unit} {name}" if unit else f"{qty} {name}")
                
                if len(results) > 8:
                    items_text = "\n  • " + "\n  • ".join(items_list)
                    return f"Un inventory la ivan {len(results)} items irukku:\n  • {items_text}"
                else:
                    items_text = ", ".join(items_list)
                    return f"Un inventory la: {items_text}"

        if intent == "ADD":
            return "✓ Stock add pannathu aagum"
        
        if intent == "SELL":
            return "✓ Sale record pannathu aagum"
        
        if intent == "PRICE":
            row = results[0] if results else {}
            item = row.get("name", "item")
            price = row.get("price", "?")
            return f"{item} kaaga vidham vela: ₹{price}"
        
        if intent == "CORRECTION":
            row = results[0] if results else {}
            item = row.get("name", "item")
            qty = row.get("quantity", "?")
            unit = row.get("unit", "")
            return f"✓ {item} stock correct pannathu aagum: {qty} {unit}"
        
        if intent == "ORDER":
            orders_text = "\n  • ".join(
                f"{r.get('item', '?')}: {r.get('qty', '?')} {r.get('unit', '')}"
                for r in results[:10]
            )
            return f"Inrum kaaga pending orders:\n  • {orders_text}"
        
        if intent == "ROLLBACK":
            row = results[0] if results else {}
            old_price = row.get("old_price", "?")
            return f"✓ Price rollback pannathu aagum previous rate la: ₹{old_price}"
        
        if intent == "EXPIRY":
            items_list = []
            for r in results:
                name = r.get('name', '?')
                expiry = r.get('expiry_date', '?')
                items_list.append(f"{name} (expiry: {expiry})")
            
            items_text = "\n  • ".join(items_list)
            return f"Ivan {len(results)} items expire aagum:\n  • {items_text}"
        
        if intent == "CATEGORY":
            return f"✓ Category kaaga price update pannathu aagum"

        return "✓ Pannathu aagum"

    def _template_response_hinglish(self, intent: str, results: list) -> str:
        """Hardcoded Hinglish templates when LLM unavailable."""
        if not results:
            if intent == "PRICE":
                return "❌ Item ka price nahi mila database mein"
            elif intent == "CORRECTION":
                return "❌ Stock correction nahi ho saka"
            elif intent == "ORDER":
                return "❌ Order data nahi mila"
            elif intent == "ROLLBACK":
                return "❌ Price history nahi mila, rollback nahi ho saka"
            elif intent == "EXPIRY":
                return "✓ Koi item expire hone wala nahi hai aaj kal"
            return "✓ Kaam ho gaya"

        if intent == "QUERY" and results:
            row = results[0]
            if "name" in row and "quantity" in row:
                name = row.get("name", "item")
                qty = row.get("quantity", "?")
                unit = row.get("unit", "")
                # Single item query
                if len(results) == 1:
                    return f"Aapke paas {qty} {unit} {name} bacha hai"
            
            # Multiple rows - list all items
            if len(results) > 1:
                items_list = []
                for r in results:  # Show ALL items
                    name = r.get('name', '?')
                    qty = r.get('quantity', '?')
                    unit = r.get('unit', '')
                    items_list.append(f"{qty}{unit} {name}" if unit else f"{qty} {name}")
                
                # Format nicely with line breaks for many items
                if len(results) > 8:
                    items_text = "\n  • " + "\n  • ".join(items_list)
                    return f"Aapke inventory mein yeh {len(results)} items available hain:\n  • {items_text}"
                else:
                    items_text = ", ".join(items_list)
                    return f"Aapke inventory mein: {items_text}"

        if intent == "ADD":
            return "✓ Stock mein add ho gaya"
        
        if intent == "SELL":
            return "✓ Sale record ho gaya"
        
        if intent == "PRICE":
            row = results[0] if results else {}
            item = row.get("name", "item")
            price = row.get("price", "?")
            return f"{item} ka current rate: ₹{price}"
        
        if intent == "CORRECTION":
            row = results[0] if results else {}
            item = row.get("name", "item")
            qty = row.get("quantity", "?")
            unit = row.get("unit", "")
            return f"✓ {item} ka stock correct ho gaya: {qty} {unit}"
        
        if intent == "ORDER":
            # Show pending orders
            orders_text = "\n  • ".join(
                f"{r.get('item', '?')}: {r.get('qty', '?')} {r.get('unit', '')}"
                for r in results[:10]
            )
            return f"Aaj ke pending orders:\n  • {orders_text}"
        
        if intent == "ROLLBACK":
            row = results[0] if results else {}
            old_price = row.get("old_price", "?")
            return f"✓ Price rollback ho gaya previous rate pe: ₹{old_price}"
        
        if intent == "EXPIRY":
            items_list = []
            for r in results:
                name = r.get('name', '?')
                expiry = r.get('expiry_date', '?')
                items_list.append(f"{name} (expiry: {expiry})")
            
            items_text = "\n  • ".join(items_list)
            return f"Yeh {len(results)} items expire hone wale hain:\n  • {items_text}"
        
        if intent == "CATEGORY":
            return f"✓ Category ka price update ho gaya"

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

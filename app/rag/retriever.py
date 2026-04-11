"""
app/rag/retriever.py
RAG layer — FAISS index over Hinglish→SQL examples.
Retrieves top-k similar examples to enrich the LLM prompt.
Falls back gracefully if FAISS/embeddings unavailable.
"""

import json
import pickle
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import RAG_INDEX_PATH, RAG_TOP_K
from logger import get_logger

log = get_logger("rag")

# ── Curated Hinglish → SQL examples ──────────────────────────────────────────
# 30+ real-world shop query examples covering ADD, SELL, QUERY intents

EXAMPLES = [
    # ── ADD (restock) ──
    {
        "query": "50kg atta add karo",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 50 WHERE LOWER(name) = 'atta'",
        "response": "50kg atta successfully add ho gaya"
    },
    {
        "query": "20 litre tel daal do",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 20 WHERE LOWER(name) = 'tel'",
        "response": "20 litre tel stock mein add ho gaya"
    },
    {
        "query": "100 packet biscuit enter karo",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 100 WHERE LOWER(name) = 'biscuit'",
        "response": "100 packet biscuit add ho gaya"
    },
    {
        "query": "5kg dal stock mein daalo",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 5 WHERE LOWER(name) = 'dal'",
        "response": "5kg dal stock mein add ho gaya"
    },
    {
        "query": "10 kilo chawal aaya hai",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 10 WHERE LOWER(name) = 'chawal'",
        "response": "10kg chawal stock mein aa gaya"
    },
    {
        "query": "30 kg chini add karo",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 30 WHERE LOWER(name) = 'chini'",
        "response": "30kg chini stock mein add ho gaya"
    },
    {
        "query": "doodh 15 litre aaya",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 15 WHERE LOWER(name) = 'doodh'",
        "response": "15 litre doodh stock mein add ho gaya"
    },
    {
        "query": "sabun 50 piece restock karo",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 50 WHERE LOWER(name) = 'sabun'",
        "response": "50 piece sabun add ho gaya"
    },
    {
        "query": "5 kilo haldi kharida hai",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 5 WHERE LOWER(name) = 'haldi'",
        "response": "5kg haldi stock mein add ho gaya"
    },
    {
        "query": "chai 2 kg aur daal do",
        "intent": "ADD",
        "sql": "UPDATE inventory SET quantity = quantity + 2 WHERE LOWER(name) = 'chai'",
        "response": "2kg chai stock mein add ho gaya"
    },

    # ── SELL (reduce stock) ──
    {
        "query": "10 packet biscuit becha",
        "intent": "SELL",
        "sql": "UPDATE inventory SET quantity = quantity - 10 WHERE LOWER(name) = 'biscuit'",
        "response": "10 packet biscuit ka sale record ho gaya"
    },
    {
        "query": "2kg atta gaya",
        "intent": "SELL",
        "sql": "UPDATE inventory SET quantity = quantity - 2 WHERE LOWER(name) = 'atta'",
        "response": "2kg atta sale record ho gaya"
    },
    {
        "query": "5 litre doodh diya customer ko",
        "intent": "SELL",
        "sql": "UPDATE inventory SET quantity = quantity - 5 WHERE LOWER(name) = 'doodh'",
        "response": "5 litre doodh sale record ho gaya"
    },
    {
        "query": "1kg chini becho",
        "intent": "SELL",
        "sql": "UPDATE inventory SET quantity = quantity - 1 WHERE LOWER(name) = 'chini'",
        "response": "1kg chini sale record ho gaya"
    },
    {
        "query": "3 piece sabun nikala",
        "intent": "SELL",
        "sql": "UPDATE inventory SET quantity = quantity - 3 WHERE LOWER(name) = 'sabun'",
        "response": "3 piece sabun sale record ho gaya"
    },
    {
        "query": "tel 1 litre bika",
        "intent": "SELL",
        "sql": "UPDATE inventory SET quantity = quantity - 1 WHERE LOWER(name) = 'tel'",
        "response": "1 litre tel sale record ho gaya"
    },
    {
        "query": "5kg chawal de diya",
        "intent": "SELL",
        "sql": "UPDATE inventory SET quantity = quantity - 5 WHERE LOWER(name) = 'chawal'",
        "response": "5kg chawal sale record ho gaya"
    },
    {
        "query": "250 gram chai becha",
        "intent": "SELL",
        "sql": "UPDATE inventory SET quantity = quantity - 0.25 WHERE LOWER(name) = 'chai'",
        "response": "250 gram chai sale record ho gaya"
    },

    # ── QUERY (check stock) ──
    {
        "query": "chawal kitna bacha hai",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE LOWER(name) = 'chawal'",
        "response": "aapke paas {quantity}{unit} chawal bacha hai"
    },
    {
        "query": "milk kitna hai",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE LOWER(name) = 'doodh'",
        "response": "aapke paas {quantity} litre doodh bacha hai"
    },
    {
        "query": "atta stock check karo",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE LOWER(name) = 'atta'",
        "response": "aapke paas {quantity}kg atta bacha hai"
    },
    {
        "query": "sab items ki list dikhao",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory ORDER BY name",
        "response": "yeh hai aapka poora stock"
    },
    {
        "query": "kaunsa saman kam hai",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE quantity < 5 ORDER BY quantity",
        "response": "yeh items khatam hone wale hain"
    },
    {
        "query": "tel bacha hai kya",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE LOWER(name) = 'tel'",
        "response": "aapke paas {quantity} litre tel bacha hai"
    },
    {
        "query": "dal kitni baaki hai",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE LOWER(name) = 'dal'",
        "response": "aapke paas {quantity}kg dal bacha hai"
    },
    {
        "query": "sabhi items ka stock batao",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit, price FROM inventory ORDER BY name",
        "response": "yeh hai poora inventory"
    },
    {
        "query": "kya stock available hai",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE quantity > 0 ORDER BY name",
        "response": "yeh items abhi available hain"
    },
    {
        "query": "namak kitna bacha",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE LOWER(name) = 'namak'",
        "response": "aapke paas {quantity}kg namak bacha hai"
    },
    {
        "query": "biscuit kitne packet hain",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE LOWER(name) = 'biscuit'",
        "response": "aapke paas {quantity} packet biscuit hain"
    },
    {
        "query": "haldi check karo",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE LOWER(name) = 'haldi'",
        "response": "aapke paas {quantity}kg haldi bacha hai"
    },
    {
        "query": "chini khatam ho rahi hai",
        "intent": "QUERY",
        "sql": "SELECT name, quantity, unit FROM inventory WHERE LOWER(name) = 'chini'",
        "response": "aapke paas {quantity}kg chini bacha hai"
    },

    # ── ADVANCED JOIN / NESTED ANALYTICS (inventory ↔ transactions) ──
    {
        "query": "pichle 7 din mein kaunse items sabse zyada bika, quantity aur revenue ke saath dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT i.name, "
            "       SUM(t.quantity) AS total_qty, "
            "       SUM(t.quantity * t.price) AS revenue "
            "FROM transactions t "
            "JOIN inventory i ON i.id = t.item_id "
            "WHERE t.type = 'sale' "
            "  AND DATE(t.timestamp) >= DATE('now', '-7 days') "
            "GROUP BY i.name "
            "ORDER BY revenue DESC "
            "LIMIT 20"
        ),
        "response": "yeh hai last 7 din ke top selling items with quantity aur revenue"
    },
    {
        "query": "jin items ka stock kam hai lekin pichle 30 din mein sale high tha, unki priority list dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT i.name, i.quantity, i.unit, "
            "       COALESCE(s.sold_qty, 0) AS last_30d_sold "
            "FROM inventory i "
            "LEFT JOIN ( "
            "  SELECT item_id, SUM(quantity) AS sold_qty "
            "  FROM transactions "
            "  WHERE type = 'sale' AND DATE(timestamp) >= DATE('now', '-30 days') "
            "  GROUP BY item_id "
            ") s ON s.item_id = i.id "
            "WHERE i.quantity < 10 "
            "  AND COALESCE(s.sold_qty, 0) > 0 "
            "ORDER BY s.sold_qty DESC, i.quantity ASC "
            "LIMIT 20"
        ),
        "response": "yeh items fast moving hain aur stock kam hai, inko jaldi restock karo"
    },
    {
        "query": "pichle mahine ke total revenue mein se kaunse items 20 percent se zyada contribute kar rahe hain, list dikhao",
        "intent": "QUERY",
        "sql": (
            "WITH item_rev AS ( "
            "  SELECT i.name, SUM(t.quantity * t.price) AS revenue "
            "  FROM transactions t "
            "  JOIN inventory i ON i.id = t.item_id "
            "  WHERE t.type = 'sale' "
            "    AND strftime('%Y-%m', t.timestamp) = strftime('%Y-%m', 'now', '-1 month') "
            "  GROUP BY i.name "
            "), total AS ( "
            "  SELECT SUM(revenue) AS total_revenue FROM item_rev "
            ") "
            "SELECT ir.name, ir.revenue, "
            "       ROUND((ir.revenue * 100.0) / total.total_revenue, 1) AS revenue_percent "
            "FROM item_rev ir, total "
            "WHERE total.total_revenue > 0 "
            "  AND (ir.revenue * 100.0) / total.total_revenue >= 20.0 "
            "ORDER BY ir.revenue DESC"
        ),
        "response": "yeh items pichle mahine ke revenue ka 20% se zyada hissa le rahe hain"
    },
    {
        "query": "jin items ka daily average sale high hai aur stock sirf 3 din ke liye bacha hai, unki list dikhao",
        "intent": "QUERY",
        "sql": (
            "WITH daily AS ( "
            "  SELECT item_id, DATE(timestamp) AS day, SUM(quantity) AS qty "
            "  FROM transactions "
            "  WHERE type = 'sale' AND DATE(timestamp) >= DATE('now', '-30 days') "
            "  GROUP BY item_id, DATE(timestamp) "
            "), avg_daily AS ( "
            "  SELECT item_id, AVG(qty) AS avg_per_day "
            "  FROM daily "
            "  GROUP BY item_id "
            ") "
            "SELECT i.name, i.quantity, i.unit, a.avg_per_day, "
            "       CASE WHEN a.avg_per_day > 0 THEN ROUND(i.quantity / a.avg_per_day, 1) ELSE NULL END AS days_of_stock "
            "FROM inventory i "
            "JOIN avg_daily a ON a.item_id = i.id "
            "WHERE a.avg_per_day >= 1 "
            "  AND a.avg_per_day IS NOT NULL "
            "  AND (i.quantity / a.avg_per_day) <= 3 "
            "ORDER BY days_of_stock ASC, a.avg_per_day DESC"
        ),
        "response": "yeh items high demand mein hain aur sirf 3 din ka stock bacha hai"
    },
    {
        "query": "kaunse din biscuit ki sale uske average daily sale se zyada thi, dates aur quantity dikhao",
        "intent": "QUERY",
        "sql": (
            "WITH daily AS ( "
            "  SELECT DATE(t.timestamp) AS day, SUM(t.quantity) AS qty "
            "  FROM transactions t "
            "  JOIN inventory i ON i.id = t.item_id "
            "  WHERE t.type = 'sale' AND LOWER(i.name) = 'biscuit' "
            "  GROUP BY DATE(t.timestamp) "
            "), avg_val AS ( "
            "  SELECT AVG(qty) AS avg_qty FROM daily "
            ") "
            "SELECT d.day, d.qty, ROUND(a.avg_qty, 2) AS avg_daily_qty "
            "FROM daily d, avg_val a "
            "WHERE d.qty > a.avg_qty "
            "ORDER BY d.day DESC"
        ),
        "response": "yeh dates par biscuit ki sale uske average se zyada thi"
    },

    # ── CUSTOMER + ITEM CO-PURCHASE (joins on customers + transactions + inventory) ──
    {
        "query": "jin customers ne ek hi din dal aur chawal dono kharida, unki list dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT DISTINCT c.customer_id, c.name, DATE(t1.timestamp) AS purchase_date "
            "FROM transactions t1 "
            "JOIN transactions t2 ON t1.customer_id = t2.customer_id "
            "  AND DATE(t1.timestamp) = DATE(t2.timestamp) "
            "JOIN inventory i1 ON i1.id = t1.item_id "
            "JOIN inventory i2 ON i2.id = t2.item_id "
            "LEFT JOIN customers c ON c.customer_id = t1.customer_id "
            "WHERE LOWER(i1.name) LIKE '%dal%' "
            "  AND LOWER(i2.name) LIKE '%chawal%' "
            "  AND t1.type = 'sale' AND t2.type = 'sale' "
            "ORDER BY purchase_date DESC"
        ),
        "response": "yeh customers ne ek hi din dal aur chawal saath kharida hai"
    },
]


class RAGRetriever:
    """
    FAISS-backed similarity retriever for Hinglish→SQL examples.
    Falls back to keyword matching if FAISS/sentence-transformers unavailable.
    """

    def __init__(self):
        self._index = None
        self._model = None
        self._embeddings = None
        self._ready = False
        self._try_init_faiss()

    def _try_init_faiss(self):
        """Try to load FAISS + sentence-transformers. Gracefully degrade if unavailable."""
        try:
            import faiss
            from sentence_transformers import SentenceTransformer
            import numpy as np

            index_file = Path(RAG_INDEX_PATH).with_suffix(".faiss")
            emb_file = Path(RAG_INDEX_PATH).with_suffix(".pkl")

            if index_file.exists() and emb_file.exists():
                log.info("Loading existing FAISS index from %s", index_file)
                self._index = faiss.read_index(str(index_file))
                with open(emb_file, "rb") as f:
                    self._embeddings = pickle.load(f)
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            else:
                log.info("Building FAISS index from %d examples", len(EXAMPLES))
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                queries = [e["query"] for e in EXAMPLES]
                vecs = self._model.encode(queries, show_progress_bar=False)
                vecs = np.array(vecs, dtype="float32")

                dim = vecs.shape[1]
                self._index = faiss.IndexFlatL2(dim)
                self._index.add(vecs)
                self._embeddings = vecs

                # Persist index
                index_file.parent.mkdir(parents=True, exist_ok=True)
                faiss.write_index(self._index, str(index_file))
                with open(emb_file, "wb") as f:
                    pickle.dump(self._embeddings, f)
                log.info("FAISS index saved to %s", index_file)

            self._ready = True
            log.info("RAG retriever ready (FAISS mode)")

        except ImportError as e:
            log.warning("FAISS/sentence-transformers not available (%s). Using keyword fallback.", e)
            self._ready = False
        except Exception as e:
            log.warning("RAG init failed: %s. Using keyword fallback.", e)
            self._ready = False

    def retrieve(self, query: str, top_k: int = RAG_TOP_K) -> list[dict]:
        """Return top-k most relevant examples for the given query."""
        if self._ready:
            return self._faiss_retrieve(query, top_k)
        return self._keyword_retrieve(query, top_k)

    def _faiss_retrieve(self, query: str, top_k: int) -> list[dict]:
        import numpy as np
        vec = self._model.encode([query], show_progress_bar=False)
        vec = np.array(vec, dtype="float32")
        distances, indices = self._index.search(vec, min(top_k, len(EXAMPLES)))
        results = []
        for idx in indices[0]:
            if 0 <= idx < len(EXAMPLES):
                results.append(EXAMPLES[idx])
        log.debug("FAISS retrieved %d examples for '%s'", len(results), query[:40])
        return results

    def _keyword_retrieve(self, query: str, top_k: int) -> list[dict]:
        """Simple overlap-based fallback when FAISS unavailable."""
        query_words = set(query.lower().split())
        scored = []
        for ex in EXAMPLES:
            ex_words = set(ex["query"].lower().split())
            score = len(query_words & ex_words)
            scored.append((score, ex))
        scored.sort(key=lambda x: -x[0])
        results = [ex for _, ex in scored[:top_k] if _ > 0]
        if not results:
            results = EXAMPLES[:top_k]
        log.debug("Keyword fallback retrieved %d examples", len(results))
        return results

    def format_for_prompt(self, examples: list[dict]) -> str:
        """Format retrieved examples as a prompt-ready string."""
        lines = []
        for i, ex in enumerate(examples, 1):
            lines.append(f"Example {i}:")
            lines.append(f"  User: {ex['query']}")
            lines.append(f"  SQL: {ex['sql']}")
        return "\n".join(lines)


# Singleton
_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever

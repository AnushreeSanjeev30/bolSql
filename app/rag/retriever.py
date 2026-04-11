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
    
    # ── ADVANCED ANALYTICS & JOINS ──
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
    {
        "query": "pichle mahine ke hisaab se category wise customer cohort dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT strftime('%Y-%m', t.timestamp) AS month, i.category, "
            "       COUNT(DISTINCT t.customer_id) AS active_customers, "
            "       SUM(t.quantity * t.price) AS revenue "
            "FROM transactions t "
            "JOIN inventory i ON i.id = t.item_id "
            "WHERE t.type = 'sale' "
            "GROUP BY month, i.category "
            "ORDER BY month DESC, revenue DESC"
        ),
        "response": "yeh hai month aur category ke hisaab se customer cohorts aur revenue"
    },
    {
        "query": "jo customers heavy buyers the par 30 din se kuch nahi kharida, unki list dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT c.customer_id, c.name, c.last_visit, c.total_lifetime_value "
            "FROM customers c "
            "WHERE c.total_lifetime_value >= 5000 "
            "  AND julianday('now') - julianday(c.last_visit) > 30 "
            "ORDER BY c.total_lifetime_value DESC"
        ),
        "response": "yeh heavy buyers hai jo 30 din se shop par nahi aaye"
    },
    {
        "query": "kaunse customers high churn risk mein hain, top 20 dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT c.customer_id, c.name, cs.segment, cs.churn_risk, cs.recency_days "
            "FROM customer_segments cs "
            "JOIN customers c ON c.customer_id = cs.customer_id "
            "WHERE cs.churn_risk >= 0.7 "
            "ORDER BY cs.churn_risk DESC, cs.recency_days DESC "
            "LIMIT 20"
        ),
        "response": "yeh top customers high churn risk mein hain, inko wapas lana zaroori hai"
    },
    {
        "query": "pichle mahine ke top 10 customers kitna kharcha kiya, list dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT t.customer_id, c.name, "
            "       SUM(t.quantity * t.price) AS total_spend "
            "FROM transactions t "
            "LEFT JOIN customers c ON c.customer_id = t.customer_id "
            "WHERE t.type = 'sale' "
            "  AND strftime('%Y-%m', t.timestamp) = strftime('%Y-%m', 'now', '-1 month') "
            "GROUP BY t.customer_id, c.name "
            "ORDER BY total_spend DESC "
            "LIMIT 10"
        ),
        "response": "yeh hai pichle mahine ke top 10 kharchi customers"
    },
    {
        "query": "har customer ka average basket size aur total visits dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT t.customer_id, c.name, "
            "       COUNT(DISTINCT t.order_id) AS visits, "
            "       AVG(items_per_visit.cnt) AS avg_items_per_visit "
            "FROM transactions t "
            "JOIN ( "
            "  SELECT order_id, COUNT(*) AS cnt "
            "  FROM transactions "
            "  WHERE type = 'sale' AND order_id IS NOT NULL "
            "  GROUP BY order_id "
            ") AS items_per_visit ON items_per_visit.order_id = t.order_id "
            "LEFT JOIN customers c ON c.customer_id = t.customer_id "
            "WHERE t.type = 'sale' AND t.order_id IS NOT NULL "
            "GROUP BY t.customer_id, c.name "
            "ORDER BY avg_items_per_visit DESC"
        ),
        "response": "yeh customers ka visits aur average basket size hai"
    },
    {
        "query": "kaunse item pairs aksar saath bikte hain, top 20 batao",
        "intent": "QUERY",
        "sql": (
            "SELECT item_a, item_b, co_occurrence_count, lift_score "
            "FROM basket_pairs "
            "ORDER BY co_occurrence_count DESC, lift_score DESC "
            "LIMIT 20"
        ),
        "response": "yeh item pairs aksar ek saath bikte hain"
    },
    {
        "query": "dal ke saath sabse zyada kaunse items bikte hain, suggestion ke liye dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT CASE WHEN item_a = 'dal' THEN item_b ELSE item_a END AS paired_item, "
            "       co_occurrence_count, lift_score "
            "FROM basket_pairs "
            "WHERE item_a = 'dal' OR item_b = 'dal' "
            "ORDER BY co_occurrence_count DESC, lift_score DESC "
            "LIMIT 10"
        ),
        "response": "yeh items dal ke saath sabse zyada bikte hain"
    },
    {
        "query": "agla hafte ke liye predicted orders dikhao, customer aur item wise",
        "intent": "QUERY",
        "sql": (
            "SELECT p.customer_id, c.name, p.item_name, p.predicted_qty, p.predicted_date, p.confidence "
            "FROM predicted_orders p "
            "LEFT JOIN customers c ON c.customer_id = p.customer_id "
            "WHERE p.fulfilled = 0 "
            "  AND date(p.predicted_date) <= date('now', '+7 days') "
            "ORDER BY p.predicted_date, p.confidence DESC"
        ),
        "response": "yeh agle hafte ke liye predicted orders hain"
    },
    {
        "query": "har category ka pichle 3 mahine ka total revenue aur margin dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT i.category, "
            "       strftime('%Y-%m', t.timestamp) AS month, "
            "       SUM(t.quantity * t.price) AS revenue, "
            "       SUM(t.quantity * (t.price - t.cost_price)) AS margin "
            "FROM transactions t "
            "JOIN inventory i ON i.id = t.item_id "
            "WHERE t.type = 'sale' "
            "  AND t.timestamp >= date('now', '-3 months') "
            "GROUP BY i.category, month "
            "ORDER BY month DESC, revenue DESC"
        ),
        "response": "yeh hai category wise last 3 months ka revenue aur margin"
    },
    {
        "query": "subscription customers ya jo regular monthly order karte hain unki list dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT DISTINCT o.customer_id, c.name, o.is_subscription, COUNT(*) AS orders_count "
            "FROM orders o "
            "LEFT JOIN customers c ON c.customer_id = o.customer_id "
            "WHERE o.is_subscription = 1 "
            "   OR (strftime('%d', o.order_date) BETWEEN '01' AND '07') "
            "GROUP BY o.customer_id, c.name, o.is_subscription "
            "ORDER BY orders_count DESC"
        ),
        "response": "yeh customers regular subscription ya monthly pattern mein order karte hain"
    },
    {
        "query": "konse customers 90 din se nahi aaye par lifetime value high hai",
        "intent": "QUERY",
        "sql": (
            "SELECT c.customer_id, c.name, c.last_visit, c.total_lifetime_value "
            "FROM customers c "
            "WHERE c.total_lifetime_value >= 3000 "
            "  AND julianday('now') - julianday(c.last_visit) > 90 "
            "ORDER BY c.total_lifetime_value DESC"
        ),
        "response": "yeh high value customers 90 din se shop par nahi aaye"
    },
    {
        "query": "aaj ka total revenue aur kitne unique customers aaye, summary batao",
        "intent": "QUERY",
        "sql": (
            "SELECT DATE(t.timestamp) AS day, "
            "       SUM(t.quantity * t.price) AS revenue, "
            "       COUNT(DISTINCT COALESCE(t.customer_id, 'walk-in')) AS unique_customers "
            "FROM transactions t "
            "WHERE t.type = 'sale' AND DATE(t.timestamp) = DATE('now') "
            "GROUP BY day"
        ),
        "response": "yeh aaj ka total revenue aur unique customers ka summary hai"
    },
    {
        "query": "jo customers sirf ek hi baar aaye aur wapas nahi aaye unki list dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT c.customer_id, c.name, cs.frequency_count, cs.recency_days "
            "FROM customer_segments cs "
            "JOIN customers c ON c.customer_id = cs.customer_id "
            "WHERE cs.frequency_count = 1 "
            "  AND cs.recency_days > 30 "
            "ORDER BY cs.recency_days DESC"
        ),
        "response": "yeh one-time customers hain jo wapas nahi aaye"
    },
    {
        "query": "jin customers ka credit balance pending hai, unka total aur list dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT customer_id, name, credit_balance "
            "FROM customers "
            "WHERE credit_balance > 0 "
            "ORDER BY credit_balance DESC"
        ),
        "response": "yeh customers ka credit balance abhi pending hai"
    },
    {
        "query": "kaunse locality se sabse zyada revenue aata hai, top 5 areas dikhao",
        "intent": "QUERY",
        "sql": (
            "SELECT c.locality, SUM(t.quantity * t.price) AS revenue "
            "FROM transactions t "
            "JOIN customers c ON c.customer_id = t.customer_id "
            "WHERE t.type = 'sale' "
            "GROUP BY c.locality "
            "ORDER BY revenue DESC "
            "LIMIT 5"
        ),
        "response": "yeh top localities hain jahan se sabse zyada revenue aata hai"
    },
    {
        "query": "pichle 6 mahine mein har month ka repeat vs new customers ka breakdown dikhao",
        "intent": "QUERY",
        "sql": (
            "WITH first_purchase AS ( "
            "  SELECT customer_id, MIN(DATE(timestamp)) AS first_date "
            "  FROM transactions "
            "  WHERE type = 'sale' AND customer_id IS NOT NULL "
            "  GROUP BY customer_id "
            "), monthly AS ( "
            "  SELECT strftime('%Y-%m', t.timestamp) AS month, t.customer_id, "
            "         CASE WHEN DATE(t.timestamp) = fp.first_date THEN 1 ELSE 0 END AS is_new "
            "  FROM transactions t "
            "  JOIN first_purchase fp ON fp.customer_id = t.customer_id "
            "  WHERE t.type = 'sale' AND t.timestamp >= date('now', '-6 months') "
            ") "
            "SELECT month, "
            "       SUM(is_new) AS new_customers, "
            "       COUNT(DISTINCT customer_id) - SUM(is_new) AS repeat_customers "
            "FROM monthly "
            "GROUP BY month "
            "ORDER BY month DESC"
        ),
        "response": "yeh hai pichle 6 mahine ka new vs repeat customers ka breakdown"
    },
    {
        "query": "kaunse items ka stock fast moving hai, last 30 din ke sales ke hisaab se batao",
        "intent": "QUERY",
        "sql": (
            "SELECT i.name, i.category, SUM(t.quantity) AS sold_qty "
            "FROM transactions t "
            "JOIN inventory i ON i.id = t.item_id "
            "WHERE t.type = 'sale' AND t.timestamp >= date('now', '-30 days') "
            "GROUP BY i.name, i.category "
            "ORDER BY sold_qty DESC "
            "LIMIT 20"
        ),
        "response": "yeh fast moving items hain last 30 din ke sales ke hisaab se"
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

import sqlite3
from pathlib import Path
import sys

import pandas as pd
import numpy as np

# Ensure project root is on sys.path so we can import config when
# running this file directly (python app/trends/evaluator.py).
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import DB_PATH

try:
    from sklearn.metrics import f1_score
    HAS_SKLEARN = True
except ImportError:
    # sklearn not available - define a simple F1 helper
    def f1_score(y_true, y_pred):
        """Approximate F1 when sklearn is not installed."""
        if not y_true:
            return 0.0
        tp = fp = fn = 0
        for t, p in zip(y_true, y_pred):
            if t and p:
                tp += 1
            elif not t and p:
                fp += 1
            elif t and not p:
                fn += 1
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    HAS_SKLEARN = False


def _evaluate_stock_predictions(conn: sqlite3.Connection) -> None:
    """Evaluate stock-out date predictions using MAE/RMSE in days.

    Expects a stock_predictions table with predicted_date and actual_date
    columns that pandas can parse as datetimes.
    """
    query = """
        SELECT predicted_date, actual_date
        FROM stock_predictions
        WHERE actual_date IS NOT NULL
    """
    try:
        df_stock = pd.read_sql(query, conn)
    except Exception as e:
        print(f"⚠️  stock_predictions table missing or invalid, skipping stock evaluation: {e}")
        return

    if df_stock.empty:
        print("ℹ️  stock_predictions has no rows with actual_date; skipping stock evaluation.")
        return

    # Parse to datetime and drop invalid rows
    df_stock["predicted_date"] = pd.to_datetime(df_stock["predicted_date"], errors="coerce")
    df_stock["actual_date"] = pd.to_datetime(df_stock["actual_date"], errors="coerce")
    df_stock = df_stock.dropna(subset=["predicted_date", "actual_date"])

    if df_stock.empty:
        print("ℹ️  stock_predictions has no rows with valid predicted/actual dates; skipping.")
        return

    diff_days = (df_stock["actual_date"] - df_stock["predicted_date"]).dt.days.astype(float)
    mae = float(np.mean(np.abs(diff_days)))
    rmse = float(np.sqrt(np.mean(diff_days ** 2)))
    print(f"📊 Stock Prediction - MAE: {mae:.2f} days, RMSE: {rmse:.2f} days")


def _evaluate_churn(conn: sqlite3.Connection) -> None:
    """Evaluate churn classifier using F1-score.

    Expects a churn_history table with predicted_churn and actual_churn
    columns (0/1 or boolean).
    """
    query = "SELECT predicted_churn, actual_churn FROM churn_history"
    try:
        df_churn = pd.read_sql(query, conn)
    except Exception as e:
        print(f"⚠️  churn_history table missing or invalid, skipping churn evaluation: {e}")
        return

    if df_churn.empty:
        print("ℹ️  churn_history has no rows; skipping churn evaluation.")
        return

    y_true = df_churn["actual_churn"].tolist()
    y_pred = df_churn["predicted_churn"].tolist()
    score = f1_score(y_true, y_pred)
    if HAS_SKLEARN:
        print(f"🎯 Churn Classifier - F1-Score: {score:.2f}")
    else:
        print(f"🎯 Churn Classifier - F1-Score (approx, sklearn not installed): {score:.2f}")


# High-level evaluation metrics guide for the full system
PRIORITY_METRICS = [
    {
        "name": "Task Completion Rate",
        "priority": "⭐⭐⭐",
        "why": "Captures full pipeline health (NLP → SQL → DB → response)",
    },
    {
        "name": "SQL Execution Accuracy",
        "priority": "⭐⭐⭐",
        "why": "Core function of the app (generated queries vs ground truth)",
    },
    {
        "name": "Intent + Entity Accuracy",
        "priority": "⭐⭐",
        "why": "Catches Groq / NLP understanding failures before SQL stage",
    },
    {
        "name": "WER (Sarvam)",
        "priority": "⭐⭐",
        "why": "Catches voice transcription failures from ASR",
    },
    {
        "name": "Human Eval Score",
        "priority": "⭐",
        "why": "Ground truth for final response quality and usefulness",
    },
]


def _print_priority_metrics_guide() -> None:
    """Print a short guide of key evaluation metrics for reports.

    This does not compute the metrics (they depend on separate logs /
    annotation pipelines) but documents what should be tracked.
    """
    print("\n==== Evaluation Metrics Guide ====")
    for m in PRIORITY_METRICS:
        print(f"{m['priority']}  {m['name']}: {m['why']}")
    print("================================\n")


def evaluate_trends(db_path: str | None = None) -> None:
    """Run all available evaluation metrics against the analytics DB.

    If db_path is not provided, uses the unified DB configured in config.DB_PATH
    (usually kirana_trends.db).
    """
    if db_path is None:
        db_path = str(DB_PATH)

    print(f"Using DB: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        _evaluate_stock_predictions(conn)
        _evaluate_churn(conn)
    finally:
        conn.close()

    # Always print the high-level metrics guide at the end so you
    # can quickly copy it into a paper/report.
    _print_priority_metrics_guide()


if __name__ == "__main__":
    evaluate_trends()
    
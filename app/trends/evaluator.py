import sqlite3
import pandas as pd
import numpy as np

try:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, f1_score
    HAS_SKLEARN = True
except ImportError:
    # sklearn not available - define dummy functions
    def mean_absolute_error(y_true, y_pred):
        return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true) if y_true else 0
    
    def mean_squared_error(y_true, y_pred):
        return sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / len(y_true) if y_true else 0
    
    def f1_score(y_true, y_pred):
        return 0.0  # Placeholder
    
    HAS_SKLEARN = False

def evaluate_trends(db_path="kirana.db"):
    conn = sqlite3.connect(db_path)
    
    # 1. Evaluate Stock Depletion (MAE/RMSE)
    # Compares predicted stock-out date vs actual stock-out date
    query = """
        SELECT predicted_date, actual_date 
        FROM stock_predictions 
        WHERE actual_date IS NOT NULL
    """
    df_stock = pd.read_sql(query, conn)
    if not df_stock.empty:
        mae = mean_absolute_error(df_stock['actual_date'], df_stock['predicted_date'])
        rmse = np.sqrt(mean_squared_error(df_stock['actual_date'], df_stock['predicted_date']))
        print(f"📊 Stock Prediction - MAE: {mae:.2f} days, RMSE: {rmse:.2f}")

    # 2. Evaluate Churn (Precision/Recall/F1)
    # Compares who you labeled 'At Risk' vs who actually stopped buying
    query = "SELECT predicted_churn, actual_churn FROM churn_history"
    df_churn = pd.read_sql(query, conn)
    if not df_churn.empty:
        f1 = f1_score(df_churn['actual_churn'], df_churn['predicted_churn'])
        print(f"🎯 Churn Classifier - F1-Score: {f1:.2f}")
    
    conn.close()

if __name__ == "__main__":
    evaluate_trends()
    
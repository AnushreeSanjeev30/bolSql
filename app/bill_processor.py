"""
app/bill_processor.py
Validates and processes shopkeeper-uploaded JSON bills.
Handles inventory updates and sales recording with atomic transactions.
"""

import csv
import io
import sqlite3
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DB_PATH
from logger import get_logger
from app.db.database import canonicalize_name

log = get_logger("bill_processor")


@dataclass
class BillItem:
    """Validated bill item."""
    product_id: str
    name: str
    quantity: float
    price: float


@dataclass
class BillValidationResult:
    """Result of bill validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class BillProcessingResult:
    """Result of bill processing."""
    success: bool
    bill_id: str
    message: str
    items_processed: int
    sales_records_created: int
    inventory_updated: bool
    error: Optional[str] = None


class BillProcessor:
    """
    Validates and processes JSON bills into database.
    Ensures atomicity: all-or-nothing transaction handling.
    """

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Get DB connection with safety settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def validate_bill(self, bill: Dict) -> BillValidationResult:
        """
        Comprehensive validation of bill structure and data.
        
        Checks:
        - Required fields (bill_id, customer_id, items)
        - Bill ID uniqueness
        - Customer exists in DB
        - Product exists in DB
        - Stock available for each item
        - Timestamp is not in future
        - Numeric values are positive
        """
        errors = []
        warnings = []

        # 1. Check required fields
        required_fields = ["bill_id", "customer_id", "customer_name", "timestamp", "items"]
        for field in required_fields:
            if field not in bill:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return BillValidationResult(valid=False, errors=errors, warnings=warnings)

        bill_id = bill.get("bill_id", "").strip()
        customer_id = bill.get("customer_id", "").strip()
        timestamp_str = bill.get("timestamp", "").strip()
        items = bill.get("items", [])

        # 2. Validate bill_id format
        if not bill_id or len(bill_id) < 2:
            errors.append("bill_id must be non-empty and at least 2 characters")

        # 3. Validate customer_id format
        if not customer_id or len(customer_id) < 1:
            errors.append("customer_id must be non-empty")

        # 4. Validate timestamp format and not in future
        try:
            bill_dt = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            if bill_dt > now:
                errors.append(f"Timestamp cannot be in future (given: {timestamp_str})")
        except (ValueError, TypeError) as e:
            errors.append(f"Invalid timestamp format: {timestamp_str}. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

        # 5. Validate items list
        if not items or not isinstance(items, list):
            errors.append("items must be a non-empty list")
            return BillValidationResult(valid=False, errors=errors, warnings=warnings)

        if len(items) == 0:
            errors.append("Bill must contain at least one item")

        # 6. Check bill_id uniqueness in DB
        try:
            conn = self._get_conn()
            existing_bill = conn.execute(
                "SELECT COUNT(*) as cnt FROM transactions WHERE order_id=?",
                (bill_id,)
            ).fetchone()
            conn.close()
            
            if existing_bill and existing_bill["cnt"] > 0:
                errors.append(f"Bill ID '{bill_id}' already processed (duplicate)")
        except Exception as e:
            errors.append(f"Database error checking bill uniqueness: {str(e)}")

        # 7. Validate individual items
        validated_items = []
        for idx, item in enumerate(items):
            item_errors = self._validate_bill_item(item, idx)
            if item_errors:
                errors.extend(item_errors)
            else:
                # Item is valid, prepare it
                try:
                    validated_items.append(BillItem(
                        product_id=item["product_id"].strip(),
                        name=item["name"].strip(),
                        quantity=float(item["quantity"]),
                        price=float(item["price"])
                    ))
                except (KeyError, ValueError) as e:
                    errors.append(f"Item {idx}: Failed to parse - {str(e)}")

        # 8. Check stock availability for each item
        try:
            conn = self._get_conn()
            for idx, item in enumerate(validated_items):
                # Find product by product_id or name
                product = conn.execute(
                    "SELECT * FROM inventory WHERE LOWER(name) LIKE ?",
                    (f"%{item.name.lower()}%",)
                ).fetchone()
                
                if product:
                    if product["quantity"] < item.quantity:
                        errors.append(
                            f"Item '{item.name}' (Qty {item.quantity}): "
                            f"Insufficient stock. Available: {product['quantity']}"
                        )
                else:
                    # Product not found - warning, not error (allow recording)
                    warnings.append(f"Item '{item.name}' not found in inventory")
            conn.close()
        except Exception as e:
            errors.append(f"Database error checking stock: {str(e)}")

        # 9. Validate customer exists
        try:
            conn = self._get_conn()
            customer = conn.execute(
                "SELECT * FROM customers WHERE customer_id=?",
                (customer_id,)
            ).fetchone()
            conn.close()
            
            if not customer:
                warnings.append(f"Customer '{customer_id}' not in DB. Will be auto-created.")
        except Exception as e:
            warnings.append(f"Could not verify customer: {str(e)}")

        # Return result
        is_valid = len(errors) == 0
        return BillValidationResult(
            valid=is_valid,
            errors=errors,
            warnings=warnings
        )

    def _validate_bill_item(self, item: Dict, index: int) -> List[str]:
        """Validate a single bill item."""
        errors = []
        
        # Check required fields
        required = ["product_id", "name", "quantity", "price"]
        for field in required:
            if field not in item:
                errors.append(f"Item {index}: Missing field '{field}'")
        
        if errors:
            return errors

        # Check types and values
        try:
            product_id = str(item["product_id"]).strip()
            name = str(item["name"]).strip()
            quantity = float(item["quantity"])
            price = float(item["price"])

            if not product_id:
                errors.append(f"Item {index}: product_id cannot be empty")
            if not name:
                errors.append(f"Item {index}: name cannot be empty")
            if quantity <= 0:
                errors.append(f"Item {index}: quantity must be positive (got {quantity})")
            if price <= 0:
                errors.append(f"Item {index}: price must be positive (got {price})")

        except (ValueError, TypeError) as e:
            errors.append(f"Item {index}: Invalid numeric value - {str(e)}")

        return errors

    def process_bill(self, bill: Dict) -> BillProcessingResult:
        """
        Process validated bill: insert sales, update inventory.
        Atomic transaction: all-or-nothing.
        
        Returns BillProcessingResult with success status.
        """
        # Validate first
        validation = self.validate_bill(bill)
        if not validation.valid:
            error_msg = "; ".join(validation.errors)
            log.error(f"Bill validation failed: {error_msg}")
            return BillProcessingResult(
                success=False,
                bill_id=bill.get("bill_id", "UNKNOWN"),
                message="Bill validation failed",
                items_processed=0,
                sales_records_created=0,
                inventory_updated=False,
                error=error_msg
            )

        # Extract data
        bill_id = bill["bill_id"].strip()
        customer_id = bill["customer_id"].strip()
        customer_name = bill.get("customer_name", "").strip()
        timestamp_str = bill["timestamp"].strip()
        items = bill["items"]

        conn = None
        try:
            conn = self._get_conn()
            
            # Start transaction
            conn.execute("BEGIN TRANSACTION")

            # Ensure customer exists
            customer_check = conn.execute(
                "SELECT COUNT(*) as cnt FROM customers WHERE customer_id=?",
                (customer_id,)
            ).fetchone()
            
            if not customer_check or customer_check["cnt"] == 0:
                # Auto-create customer
                conn.execute(
                    "INSERT INTO customers (customer_id, name, first_visit) VALUES (?, ?, ?)",
                    (customer_id, customer_name, timestamp_str)
                )
                log.info(f"Auto-created customer: {customer_id}")

            sales_count = 0
            items_processed = 0

            # Process each item
            for item_data in items:
                product_id = item_data["product_id"].strip()
                name = item_data["name"].strip()
                quantity = float(item_data["quantity"])
                price = float(item_data["price"])
                total_price = quantity * price

                # Find product in inventory
                product = conn.execute(
                    "SELECT * FROM inventory WHERE LOWER(name) LIKE ?",
                    (f"%{name.lower()}%",)
                ).fetchone()

                if not product:
                    # Try exact match with product_id
                    product = conn.execute(
                        "SELECT * FROM inventory WHERE LOWER(name)=?",
                        (name.lower(),)
                    ).fetchone()

                if not product:
                    raise ValueError(f"Product '{name}' not found in inventory database")

                # Update inventory - deduct quantity
                new_stock = product["quantity"] - quantity
                if new_stock < 0:
                    raise ValueError(
                        f"Insufficient stock for '{name}': "
                        f"need {quantity}, have {product['quantity']}"
                    )
                
                conn.execute(
                    "UPDATE inventory SET quantity=? WHERE id=?",
                    (new_stock, product["id"])
                )
                log.info(f"Updated inventory: {name} qty={quantity}, new_stock={new_stock}")

                # Insert into transactions (sales record)
                conn.execute(
                    """INSERT INTO transactions 
                       (customer_id, item_id, item_name, type, quantity, price, timestamp, order_id, channel)
                       VALUES (?, ?, ?, 'sale', ?, ?, ?, ?, 'bill_upload')
                    """,
                    (customer_id, product["id"], name, 
                     quantity, total_price, timestamp_str, bill_id)
                )
                sales_count += 1
                items_processed += 1
                log.info(f"Recorded sale: {name} qty={quantity} price={total_price}")

            # Commit transaction
            conn.commit()
            log.info(f"Bill {bill_id} processed successfully: {items_processed} items")

            message = f"✅ Bill {bill_id} processed. {items_processed} items recorded. Inventory updated."
            return BillProcessingResult(
                success=True,
                bill_id=bill_id,
                message=message,
                items_processed=items_processed,
                sales_records_created=sales_count,
                inventory_updated=True,
                error=None
            )

        except Exception as e:
            # Rollback on error
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            
            error_msg = str(e)
            log.error(f"Bill processing failed: {error_msg}")
            return BillProcessingResult(
                success=False,
                bill_id=bill.get("bill_id", "UNKNOWN"),
                message="Bill processing failed",
                items_processed=0,
                sales_records_created=0,
                inventory_updated=False,
                error=error_msg
            )
        
        finally:
            if conn:
                conn.close()


# Convenience functions
def validate_and_process_bill(bill: Dict) -> Tuple[bool, str]:
    """
    High-level function: validate and process bill.
    
    Args:
        bill: Bill dictionary
        
    Returns:
        (success: bool, message: str)
    """
    processor = BillProcessor()
    result = processor.process_bill(bill)
    return result.success, result.message


def refresh_trends_after_bill(db_path: str = None) -> bool:
    """
    Trigger trends recalculation after bill processing.
    Called automatically after successful bill upload.
    Recalculates customer-level and core trends.
    """
    if db_path is None:
        db_path = str(DB_PATH)
    
    try:
        from app.trends.customer_engine import compute_rfm, compute_ltv, predict_churn
        from app.trends.engine import TrendsEngine
        
        # Update customer-level analytics (fast, essential)
        compute_rfm(db_path)
        compute_ltv(db_path)
        predict_churn(db_path)
        
        log.info("Trends refreshed after bill processing")
        return True
    except Exception as e:
        log.error(f"Failed to refresh trends: {str(e)}")
        return False


def _normalize_csv_header(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value).strip())
    return re.sub(r"_+", "_", normalized).strip("_")


def _clean_number(value: str) -> float:
    cleaned = str(value).strip().replace(",", "")
    lowered = cleaned.lower()
    for token in ("₹", "rs.", "rs", "inr", "rupees", "rupee"):
        lowered = lowered.replace(token, "")
    # Keep only numeric characters after currency/unit cleanup (e.g. "Rs 34/kg" -> "34").
    lowered = re.sub(r"[^0-9.\-]", "", lowered)
    if not lowered:
        raise ValueError("missing numeric value")
    return float(lowered)


def _parse_timestamp(date_text: str = "", time_text: str = "") -> str:
    raw_date = str(date_text or "").strip()
    raw_time = str(time_text or "").strip()

    candidates = []
    if raw_date and raw_time:
        candidates.append(f"{raw_date} {raw_time}")
        candidates.append(f"{raw_date}T{raw_time}")
    elif raw_date:
        candidates.append(raw_date)

    candidates.extend([candidate.replace(" ", "T") for candidate in candidates])

    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate).replace(microsecond=0).isoformat()
        except ValueError:
            pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(f"{raw_date} {raw_time}".strip(), fmt).replace(microsecond=0).isoformat()
        except ValueError:
            continue

    raise ValueError(f"Unsupported timestamp format: {raw_date} {raw_time}".strip())


def _parse_transaction_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"restock", "stock_in", "stock in", "purchase", "buy", "in", "add"}:
        return "restock"
    if normalized in {"sale", "sold", "sell", "out", "remove"}:
        return "sale"
    return "sale"


def _extract_field(row: dict, keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _extract_price_text(row: dict) -> str:
    explicit = _extract_field(row, [
        "price",
        "price_usd",
        "price_us",
        "rate",
        "mrp",
        "cost",
        "unit_price",
        "selling_price",
        "amount",
        "total_amount",
        "line_total",
    ])
    if explicit:
        return explicit

    for key, value in row.items():
        if not value:
            continue
        k = str(key or "").lower()
        if any(token in k for token in ("price", "mrp", "rate", "cost", "amount")):
            return str(value).strip()
    return ""


def process_sales_csv(csv_text: str, db_path: str = None, inventory_mode: str = "transaction") -> dict:
    """Import a shop CSV and update inventory + transactions for trends."""
    target_db = db_path or str(DB_PATH)
    mode = (inventory_mode or "transaction").strip().lower()
    if mode not in {"transaction", "snapshot"}:
        mode = "transaction"

    try:
        reader = csv.DictReader(io.StringIO(csv_text))
    except Exception as exc:
        return {
            "success": False,
            "message": "CSV parse failed",
            "rows_processed": 0,
            "rows_succeeded": 0,
            "rows_failed": 0,
            "inventory_updated": False,
            "trends_refreshed": False,
            "warnings": [],
            "error": str(exc),
        }

    if not reader.fieldnames:
        return {
            "success": False,
            "message": "CSV header missing",
            "rows_processed": 0,
            "rows_succeeded": 0,
            "rows_failed": 0,
            "inventory_updated": False,
            "trends_refreshed": False,
            "warnings": [],
            "error": "CSV header missing",
        }

    normalized_rows: list[dict] = []
    for raw_row in reader:
        if not any((value or "").strip() for value in raw_row.values()):
            continue
        normalized_rows.append({
            _normalize_csv_header(key): (value or "").strip()
            for key, value in raw_row.items()
            if key
        })

    if not normalized_rows:
        if mode == "snapshot":
            conn = sqlite3.connect(target_db)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
            try:
                cur = conn.execute("UPDATE inventory SET quantity=0 WHERE quantity <> 0")
                conn.commit()
                warnings = []
                if cur.rowcount > 0:
                    warnings.append(
                        f"Snapshot sync: {cur.rowcount} existing item(s) quantity 0 set kiya"
                    )
                return {
                    "success": True,
                    "message": "✅ Empty snapshot CSV imported. Inventory quantities reset.",
                    "rows_processed": 0,
                    "rows_succeeded": 0,
                    "rows_failed": 0,
                    "inventory_updated": True,
                    "trends_refreshed": False,
                    "warnings": warnings,
                    "error": None,
                }
            finally:
                conn.close()

        return {
            "success": False,
            "message": "CSV me data nahi mila",
            "rows_processed": 0,
            "rows_succeeded": 0,
            "rows_failed": 0,
            "inventory_updated": False,
            "trends_refreshed": False,
            "warnings": [],
            "error": "CSV has no data rows",
        }

    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")

    rows_processed = 0
    rows_succeeded = 0
    rows_failed = 0
    warnings: list[str] = []
    snapshot_updates: dict[int, dict] = {}
    snapshot_seen_ids: set[int] = set()

    try:
        conn.execute("BEGIN TRANSACTION")

        if mode == "snapshot":
            tx_count_row = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
            existing_tx_count = int(tx_count_row[0] if tx_count_row else 0)
            if existing_tx_count > 0:
                conn.execute("DELETE FROM transactions")
                warnings.append(
                    f"Snapshot sync: {existing_tx_count} previous transaction row(s) replace kiye gaye"
                )

        for index, row in enumerate(normalized_rows, start=1):
            rows_processed += 1

            item_name = _extract_field(row, ["product_name", "item_name", "name", "product", "item", "sku"])
            quantity_text = _extract_field(row, ["quantity", "qty", "count", "units", "unit_quantity"])
            unit_text = _extract_field(row, ["unit", "units", "uom", "ikai", "measure"])
            price_text = _extract_price_text(row)
            date_text = _extract_field(row, ["date", "order_date", "timestamp", "datetime", "sold_at"])
            time_text = _extract_field(row, ["time", "clock", "time_of_day"])
            transaction_type = _parse_transaction_type(_extract_field(row, ["type", "transaction_type", "mode"]))

            if not item_name:
                rows_failed += 1
                warnings.append(f"Row {index}: product name missing")
                continue
            if not quantity_text:
                rows_failed += 1
                warnings.append(f"Row {index}: quantity missing for {item_name}")
                continue

            try:
                quantity = _clean_number(quantity_text)
            except ValueError:
                rows_failed += 1
                warnings.append(f"Row {index}: invalid quantity for {item_name}")
                continue

            try:
                unit_price = _clean_number(price_text) if price_text else 0.0
            except ValueError:
                unit_price = 0.0

            if unit_price <= 0:
                warnings.append(f"Row {index}: price missing for {item_name}, using 0.0")

            try:
                timestamp = _parse_timestamp(date_text, time_text)
            except ValueError:
                rows_failed += 1
                warnings.append(f"Row {index}: invalid date/time for {item_name}")
                continue

            canonical_name = canonicalize_name(item_name)
            product = conn.execute(
                "SELECT * FROM inventory WHERE LOWER(name)=? ORDER BY id ASC LIMIT 1",
                (canonical_name.lower(),),
            ).fetchone()
            if not product:
                product = conn.execute(
                    "SELECT * FROM inventory WHERE LOWER(name) LIKE ? ORDER BY id ASC LIMIT 1",
                    (f"%{item_name.strip().lower()}%",),
                ).fetchone()

            if not product:
                if transaction_type == "sale":
                    cur = conn.execute(
                        "INSERT INTO inventory (name, quantity, unit, price) VALUES (?, ?, ?, ?)",
                        (canonical_name, 0, (unit_text or "piece"), unit_price),
                    )
                    product = conn.execute(
                        "SELECT * FROM inventory WHERE id=?",
                        (cur.lastrowid,),
                    ).fetchone()
                    warnings.append(f"Row {index}: {item_name} inventory me nahi tha, naya item create kiya")
                else:
                    cur = conn.execute(
                        "INSERT INTO inventory (name, quantity, unit, price) VALUES (?, ?, ?, ?)",
                        (canonical_name, quantity, (unit_text or "piece"), unit_price),
                    )
                    product = conn.execute(
                        "SELECT * FROM inventory WHERE id=?",
                        (cur.lastrowid,),
                    ).fetchone()

            current_stock = float(product["quantity"] or 0)
            item_id = product["id"]
            stored_price = unit_price if unit_price > 0 else float(product["price"] or 0)
            stored_unit = unit_text or product["unit"] or "piece"

            if mode == "snapshot":
                snapshot_seen_ids.add(item_id)
                snapshot_bucket = snapshot_updates.setdefault(item_id, {
                    "quantity": 0.0,
                    "unit": stored_unit,
                    "price": stored_price,
                })
                snapshot_bucket["quantity"] = float(snapshot_bucket["quantity"]) + quantity
                if stored_unit:
                    snapshot_bucket["unit"] = stored_unit
                if stored_price > 0:
                    snapshot_bucket["price"] = stored_price
            elif transaction_type == "sale":
                if current_stock >= quantity:
                    next_stock = current_stock - quantity
                else:
                    next_stock = 0
                    if current_stock > 0:
                        warnings.append(
                            f"Row {index}: {item_name} ke liye stock kam tha ({current_stock}), 0 pe clamp kiya"
                        )
                    else:
                        warnings.append(f"Row {index}: {item_name} ke liye stock available nahi tha")

                conn.execute(
                    "UPDATE inventory SET quantity=?, unit=?, price=COALESCE(NULLIF(?, 0), price) WHERE id=?",
                    (next_stock, stored_unit, stored_price, item_id),
                )
            else:
                next_stock = current_stock + quantity
                conn.execute(
                    "UPDATE inventory SET quantity=?, unit=?, price=COALESCE(NULLIF(?, 0), price) WHERE id=?",
                    (next_stock, stored_unit, stored_price, item_id),
                )

            conn.execute(
                """INSERT INTO transactions (item_id, item_name, type, quantity, price, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item_id, product["name"], transaction_type, quantity, stored_price, timestamp),
            )
            rows_succeeded += 1

        if mode == "snapshot" and snapshot_updates:
            for item_id, update in snapshot_updates.items():
                conn.execute(
                    "UPDATE inventory SET quantity=?, unit=?, price=COALESCE(NULLIF(?, 0), price) WHERE id=?",
                    (float(update["quantity"]), update["unit"], float(update["price"]), item_id),
                )

            placeholders = ",".join("?" for _ in snapshot_seen_ids)
            if placeholders:
                cur = conn.execute(
                    f"UPDATE inventory SET quantity=0 WHERE id NOT IN ({placeholders}) AND quantity <> 0",
                    tuple(snapshot_seen_ids),
                )
                if cur.rowcount > 0:
                    warnings.append(
                        f"Snapshot sync: {cur.rowcount} previous item(s) CSV me nahi the, quantity 0 set kiya"
                    )

        conn.commit()
    except Exception as exc:
        conn.rollback()
        return {
            "success": False,
            "message": "CSV import failed",
            "rows_processed": rows_processed,
            "rows_succeeded": rows_succeeded,
            "rows_failed": rows_failed or (rows_processed - rows_succeeded),
            "inventory_updated": rows_succeeded > 0,
            "trends_refreshed": False,
            "warnings": warnings,
            "error": str(exc),
        }
    finally:
        conn.close()

    trends_refreshed = False
    if rows_succeeded > 0:
        trends_refreshed = refresh_trends_after_bill(target_db)

    return {
        "success": rows_succeeded > 0,
        "message": (
            f"✅ CSV import complete. {rows_succeeded} row(s) processed."
            if rows_succeeded > 0
            else "CSV import failed"
        ),
        "rows_processed": rows_processed,
        "rows_succeeded": rows_succeeded,
        "rows_failed": rows_failed,
        "inventory_updated": rows_succeeded > 0,
        "trends_refreshed": trends_refreshed,
        "warnings": warnings,
        "error": None if rows_succeeded > 0 else "No valid rows found",
    }

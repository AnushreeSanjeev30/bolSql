"""
app/bill_processor.py
Validates and processes shopkeeper-uploaded JSON bills.
Handles inventory updates and sales recording with atomic transactions.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DB_PATH
from logger import get_logger

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

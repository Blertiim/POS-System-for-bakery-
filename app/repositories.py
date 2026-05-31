from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import uuid4
import sqlite3

from .database import get_connection


class AppError(Exception):
    status_code = 400


class ValidationError(AppError):
    status_code = 400


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


def euros_to_cents(value: Any, field_name: str = "amount") -> int:
    if value is None or value == "":
        raise ValidationError(f"{field_name} është e detyrueshme.")
    try:
        amount = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{field_name} nuk është numër i vlefshëm.")
    if amount < 0:
        raise ValidationError(f"{field_name} nuk mund të jetë negative.")
    cents = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def cents_to_euros(cents: int) -> float:
    return cents / 100


def row_to_category(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "sort_order": row["sort_order"],
        "active": bool(row["active"]),
    }


def row_to_product(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "category_id": row["category_id"],
        "category_name": row["category_name"],
        "name": row["name"],
        "price": cents_to_euros(row["price_cents"]),
        "price_cents": row["price_cents"],
        "cost_price": cents_to_euros(row["cost_cents"]),
        "cost_cents": row["cost_cents"],
        "active": bool(row["active"]),
    }


def row_to_sale(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "receipt_no": row["receipt_no"],
        "created_at": row["created_at"],
        "cashier_role": row["cashier_role"],
        "total": cents_to_euros(row["total_cents"]),
        "total_cents": row["total_cents"],
        "amount_received": cents_to_euros(row["amount_received_cents"]),
        "amount_received_cents": row["amount_received_cents"],
        "change_due": cents_to_euros(row["change_due_cents"]),
        "change_due_cents": row["change_due_cents"],
        "profit": cents_to_euros(row["profit_cents"]),
        "profit_cents": row["profit_cents"],
    }


def row_to_sale_item(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "quantity": row["quantity"],
        "unit_price": cents_to_euros(row["unit_price_cents"]),
        "unit_price_cents": row["unit_price_cents"],
        "unit_cost": cents_to_euros(row["unit_cost_cents"]),
        "unit_cost_cents": row["unit_cost_cents"],
        "line_total": cents_to_euros(row["line_total_cents"]),
        "line_total_cents": row["line_total_cents"],
        "line_profit": cents_to_euros(row["line_profit_cents"]),
        "line_profit_cents": row["line_profit_cents"],
    }


def list_categories(include_inactive: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM categories"
    params: list[Any] = []
    if not include_inactive:
        query += " WHERE active = 1"
    query += " ORDER BY sort_order, name"
    with get_connection() as connection:
        return [row_to_category(row) for row in connection.execute(query, params)]


def get_category(category_id: int, include_inactive: bool = False) -> dict[str, Any]:
    query = "SELECT * FROM categories WHERE id = ?"
    params: list[Any] = [category_id]
    if not include_inactive:
        query += " AND active = 1"
    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()
    if row is None:
        raise NotFoundError("Kategoria nuk u gjet.")
    return row_to_category(row)


def create_category(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValidationError("Emri i kategorisë është i detyrueshëm.")
    with get_connection() as connection:
        if payload.get("sort_order") in (None, ""):
            current_max = connection.execute(
                "SELECT COALESCE(MAX(sort_order), 0) FROM categories"
            ).fetchone()[0]
            sort_order = current_max + 10
        else:
            sort_order = int(payload.get("sort_order") or 0)
        try:
            cursor = connection.execute(
                """
                INSERT INTO categories (name, sort_order, active)
                VALUES (?, ?, 1)
                """,
                (name, sort_order),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ConflictError("Kjo kategori ekziston tashmë.")
            raise
        row = connection.execute(
            "SELECT * FROM categories WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return row_to_category(row)


def update_category(category_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValidationError("Emri i kategorisë është i detyrueshëm.")
    active = 1 if payload.get("active", True) else 0
    with get_connection() as connection:
        current = connection.execute(
            "SELECT sort_order FROM categories WHERE id = ?",
            (category_id,),
        ).fetchone()
        if current is None:
            raise NotFoundError("Kategoria nuk u gjet.")
        sort_order = (
            current["sort_order"]
            if payload.get("sort_order") in (None, "")
            else int(payload.get("sort_order") or 0)
        )
        cursor = connection.execute(
            """
            UPDATE categories
            SET name = ?, sort_order = ?, active = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (name, sort_order, active, category_id),
        )
        if cursor.rowcount == 0:
            raise NotFoundError("Kategoria nuk u gjet.")
    return get_category(category_id, include_inactive=True)


def delete_category(category_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        active_products = connection.execute(
            "SELECT COUNT(*) FROM products WHERE category_id = ? AND active = 1",
            (category_id,),
        ).fetchone()[0]
        if active_products:
            raise ConflictError("Kategoria ka produkte aktive. Fshini ose zhvendosni produktet më parë.")
        try:
            cursor = connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            archived = False
        except sqlite3.IntegrityError:
            cursor = connection.execute(
                """
                UPDATE categories
                SET active = 0, updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (category_id,),
            )
            archived = True
        if cursor.rowcount == 0:
            raise NotFoundError("Kategoria nuk u gjet.")
    return {"deleted": True, "archived": archived}


def list_products(
    search: str = "",
    category_id: int | None = None,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    query = """
        SELECT p.*, c.name AS category_name
        FROM products p
        JOIN categories c ON c.id = p.category_id
        WHERE 1 = 1
    """
    params: list[Any] = []
    if not include_inactive:
        query += " AND p.active = 1 AND c.active = 1"
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)
    if search:
        query += " AND lower(p.name) LIKE ?"
        params.append(f"%{search.lower()}%")
    query += " ORDER BY c.sort_order, p.name"
    with get_connection() as connection:
        return [row_to_product(row) for row in connection.execute(query, params)]


def get_product(product_id: int, include_inactive: bool = False) -> dict[str, Any]:
    query = """
        SELECT p.*, c.name AS category_name
        FROM products p
        JOIN categories c ON c.id = p.category_id
        WHERE p.id = ?
    """
    params: list[Any] = [product_id]
    if not include_inactive:
        query += " AND p.active = 1 AND c.active = 1"
    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()
    if row is not None:
        return row_to_product(row)
    raise NotFoundError("Produkti nuk u gjet.")


def ensure_category_exists(category_id: int) -> None:
    get_category(category_id, include_inactive=False)


def normalize_product_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValidationError("Emri i produktit është i detyrueshëm.")
    try:
        category_id = int(payload.get("category_id"))
    except (TypeError, ValueError):
        raise ValidationError("Kategoria është e detyrueshme.")
    ensure_category_exists(category_id)
    price_cents = euros_to_cents(payload.get("price"), "Çmimi")
    cost_value = payload.get("cost_price", 0)
    cost_cents = euros_to_cents(cost_value or 0, "Kosto")
    if cost_cents > price_cents:
        raise ValidationError("Kosto nuk mund të jetë më e lartë se çmimi.")
    active = 1 if payload.get("active", True) else 0
    return {
        "name": name,
        "category_id": category_id,
        "price_cents": price_cents,
        "cost_cents": cost_cents,
        "active": active,
    }


def create_product(payload: dict[str, Any]) -> dict[str, Any]:
    product = normalize_product_payload(payload)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO products
                (category_id, name, price_cents, cost_cents, active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product["category_id"],
                product["name"],
                product["price_cents"],
                product["cost_cents"],
                product["active"],
            ),
        )
        row = connection.execute(
            """
            SELECT p.*, c.name AS category_name
            FROM products p
            JOIN categories c ON c.id = p.category_id
            WHERE p.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return row_to_product(row)


def update_product(product_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    product = normalize_product_payload(payload)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE products
            SET category_id = ?,
                name = ?,
                price_cents = ?,
                cost_cents = ?,
                active = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (
                product["category_id"],
                product["name"],
                product["price_cents"],
                product["cost_cents"],
                product["active"],
                product_id,
            ),
        )
        if cursor.rowcount == 0:
            raise NotFoundError("Produkti nuk u gjet.")
    return get_product(product_id, include_inactive=True)


def delete_product(product_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        try:
            cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
            archived = False
        except sqlite3.IntegrityError:
            cursor = connection.execute(
                """
                UPDATE products
                SET active = 0, updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (product_id,),
            )
            archived = True
        if cursor.rowcount == 0:
            raise NotFoundError("Produkti nuk u gjet.")
    return {"deleted": True, "archived": archived}


def create_sale(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items") or []
    if not items:
        raise ValidationError("Porosia është bosh.")
    amount_received_value = payload.get("amount_received")
    cashier_role = str(payload.get("cashier_role", "cashier")).strip() or "cashier"
    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:
        sale_lines: list[dict[str, Any]] = []
        total_cents = 0
        profit_cents = 0
        for item in items:
            try:
                product_id = int(item.get("product_id"))
                quantity = int(item.get("quantity"))
            except (TypeError, ValueError):
                raise ValidationError("Artikulli në porosi nuk është i vlefshëm.")
            if quantity <= 0:
                raise ValidationError("Sasia duhet të jetë më e madhe se zero.")

            row = connection.execute(
                """
                SELECT p.*, c.name AS category_name
                FROM products p
                JOIN categories c ON c.id = p.category_id
                WHERE p.id = ?
                """,
                (product_id,),
            ).fetchone()
            if row is None:
                raise NotFoundError("Produkti në porosi nuk u gjet.")

            line_total_cents = row["price_cents"] * quantity
            line_profit_cents = (row["price_cents"] - row["cost_cents"]) * quantity
            total_cents += line_total_cents
            profit_cents += line_profit_cents
            sale_lines.append(
                {
                    "product_id": row["id"],
                    "product_name": row["name"],
                    "quantity": quantity,
                    "unit_price_cents": row["price_cents"],
                    "unit_cost_cents": row["cost_cents"],
                    "line_total_cents": line_total_cents,
                    "line_profit_cents": line_profit_cents,
                }
            )

        if amount_received_value in (None, ""):
            amount_received_cents = total_cents
        else:
            amount_received_cents = euros_to_cents(amount_received_value, "Shuma e marrë")

        if amount_received_cents < total_cents:
            raise ValidationError("Insufficient amount received.")

        change_due_cents = amount_received_cents - total_cents
        cursor = connection.execute(
            """
            INSERT INTO sales
                (receipt_no, created_at, cashier_role, total_cents,
                 amount_received_cents, change_due_cents, profit_cents)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"TEMP-{uuid4().hex}",
                created_at,
                cashier_role,
                total_cents,
                amount_received_cents,
                change_due_cents,
                profit_cents,
            ),
        )
        sale_id = cursor.lastrowid
        receipt_no = f"F{datetime.fromisoformat(created_at):%Y%m%d}-{sale_id:05d}"
        connection.execute(
            "UPDATE sales SET receipt_no = ? WHERE id = ?",
            (receipt_no, sale_id),
        )

        for line in sale_lines:
            connection.execute(
                """
                INSERT INTO sale_items
                    (sale_id, product_id, product_name, quantity,
                     unit_price_cents, unit_cost_cents, line_total_cents,
                     line_profit_cents)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    line["product_id"],
                    line["product_name"],
                    line["quantity"],
                    line["unit_price_cents"],
                    line["unit_cost_cents"],
                    line["line_total_cents"],
                    line["line_profit_cents"],
                ),
            )

    return get_sale(sale_id)


def get_sale(sale_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        sale_row = connection.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
        if sale_row is None:
            raise NotFoundError("Shitja nuk u gjet.")
        items = [
            row_to_sale_item(row)
            for row in connection.execute(
                "SELECT * FROM sale_items WHERE sale_id = ? ORDER BY id",
                (sale_id,),
            )
        ]
    sale = row_to_sale(sale_row)
    sale["items"] = items
    return sale


def list_sales(date_text: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = """
        SELECT s.*,
               COALESCE(SUM(si.quantity), 0) AS item_count
        FROM sales s
        LEFT JOIN sale_items si ON si.sale_id = s.id
        WHERE 1 = 1
    """
    params: list[Any] = []
    if date_text:
        query += " AND date(s.created_at) = date(?)"
        params.append(date_text)
    query += " GROUP BY s.id ORDER BY s.created_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as connection:
        sales = []
        for row in connection.execute(query, params):
            sale = row_to_sale(row)
            sale["item_count"] = row["item_count"]
            sales.append(sale)
    return sales


def daily_report(date_text: str) -> dict[str, Any]:
    with get_connection() as connection:
        summary = connection.execute(
            """
            SELECT COUNT(*) AS sale_count,
                   COALESCE(SUM(total_cents), 0) AS revenue_cents,
                   COALESCE(SUM(profit_cents), 0) AS profit_cents
            FROM sales
            WHERE date(created_at) = date(?)
            """,
            (date_text,),
        ).fetchone()
        top_items = [
            {
                "product_name": row["product_name"],
                "quantity": row["quantity"],
                "revenue": cents_to_euros(row["revenue_cents"]),
                "revenue_cents": row["revenue_cents"],
            }
            for row in connection.execute(
                """
                SELECT si.product_name,
                       SUM(si.quantity) AS quantity,
                       SUM(si.line_total_cents) AS revenue_cents
                FROM sale_items si
                JOIN sales s ON s.id = si.sale_id
                WHERE date(s.created_at) = date(?)
                GROUP BY si.product_name
                ORDER BY quantity DESC, revenue_cents DESC
                LIMIT 10
                """,
                (date_text,),
            )
        ]
    return {
        "date": date_text,
        "sale_count": summary["sale_count"],
        "revenue": cents_to_euros(summary["revenue_cents"]),
        "revenue_cents": summary["revenue_cents"],
        "profit": cents_to_euros(summary["profit_cents"]),
        "profit_cents": summary["profit_cents"],
        "top_items": top_items,
    }


def receipt_text(sale_id: int) -> str:
    sale = get_sale(sale_id)
    lines = [
        "FURRA LUMI - POS",
        "FURRA LUMI",
        "-" * 34,
        f"Kuponi: {sale['receipt_no']}",
        f"Data: {sale['created_at']}",
        "-" * 34,
    ]
    for item in sale["items"]:
        lines.append(
            f"{item['product_name'][:18]:18} x{item['quantity']:<3} "
            f"€{item['line_total_cents'] / 100:.2f}"
        )
    lines.extend(
        [
            "-" * 34,
            f"Totali:        €{sale['total_cents'] / 100:.2f}",
            f"Marrë:         €{sale['amount_received_cents'] / 100:.2f}",
            f"Kusuri:        €{sale['change_due_cents'] / 100:.2f}",
            "-" * 34,
            "Faleminderit!",
        ]
    )
    return "\n".join(lines)

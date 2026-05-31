from pathlib import Path
import sqlite3
import os


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = Path(os.environ.get("BAKERY_POS_DB", DATA_DIR / "bakery_pos.db"))


SEED_CATEGORIES = [
    ("Bukë", 10),
    ("Pastiçeri", 20),
    ("Pica", 30),
    ("Pije", 40),
]


SEED_PRODUCTS = [
    ("Bukë", "Bukë e bardhë", 80, 45),
    ("Bukë", "Bukë integrale", 100, 55),
    ("Bukë", "Baguette", 120, 65),
    ("Bukë", "Simite", 50, 25),
    ("Bukë", "Bukë misri", 110, 60),
    ("Bukë", "Focaccia", 150, 80),
    ("Pastiçeri", "Kroasant", 120, 65),
    ("Pastiçeri", "Byrek me djathë", 150, 85),
    ("Pastiçeri", "Byrek me mish", 180, 105),
    ("Pastiçeri", "Donut", 100, 50),
    ("Pastiçeri", "Muffin", 130, 70),
    ("Pastiçeri", "Kek i vogël", 140, 75),
    ("Pica", "Picë Margarita", 250, 135),
    ("Pica", "Picë me proshutë", 300, 165),
    ("Pica", "Picë vegjetariane", 280, 150),
    ("Pica", "Picë ton", 320, 180),
    ("Pica", "Picë pikante", 300, 160),
    ("Pica", "Mini picë", 180, 95),
    ("Pije", "Ujë", 70, 35),
    ("Pije", "Kafe", 100, 35),
    ("Pije", "Kapuçino", 150, 60),
    ("Pije", "Lëng portokalli", 180, 90),
    ("Pije", "Coca-Cola", 150, 80),
    ("Pije", "Çaj", 100, 35),
]


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                cost_cents INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE INDEX IF NOT EXISTS idx_products_category
                ON products(category_id);

            CREATE INDEX IF NOT EXISTS idx_products_name
                ON products(name);

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                cashier_role TEXT NOT NULL,
                total_cents INTEGER NOT NULL,
                amount_received_cents INTEGER NOT NULL,
                change_due_cents INTEGER NOT NULL,
                profit_cents INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_sales_created_at
                ON sales(created_at);

            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price_cents INTEGER NOT NULL,
                unit_cost_cents INTEGER NOT NULL DEFAULT 0,
                line_total_cents INTEGER NOT NULL,
                line_profit_cents INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """
        )

        for name, sort_order in SEED_CATEGORIES:
            connection.execute(
                """
                INSERT INTO categories (name, sort_order, active)
                VALUES (?, ?, 1)
                ON CONFLICT(name) DO UPDATE SET
                    sort_order = excluded.sort_order,
                    active = 1,
                    updated_at = datetime('now', 'localtime')
                """,
                (name, sort_order),
            )

        product_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if product_count == 0:
            category_ids = {
                row["name"]: row["id"]
                for row in connection.execute("SELECT id, name FROM categories")
            }
            for category_name, product_name, price_cents, cost_cents in SEED_PRODUCTS:
                connection.execute(
                    """
                    INSERT INTO products
                        (category_id, name, price_cents, cost_cents, active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (
                        category_ids[category_name],
                        product_name,
                        price_cents,
                        cost_cents,
                    ),
                )

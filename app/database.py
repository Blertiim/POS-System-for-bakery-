from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import os
import sqlite3


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = Path(os.environ.get("BAKERY_POS_DB", DATA_DIR / "bakery_pos.db"))
BACKUP_DIR = Path(os.environ.get("BAKERY_POS_BACKUP_DIR", DB_PATH.parent / "backups"))
SCHEMA_VERSION = 4


SEED_CATEGORIES = [
    ("Bukë", 10),
    ("Kifle", 20),
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
    ("Kifle", "Kroasant", 120, 65),
    ("Kifle", "Byrek me djathë", 150, 85),
    ("Kifle", "Byrek me mish", 180, 105),
    ("Kifle", "Donut", 100, 50),
    ("Kifle", "Muffin", 130, 70),
    ("Kifle", "Kek i vogël", 140, 75),
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


Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]


def ensure_database_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def configure_connection(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA temp_store = MEMORY")


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    ensure_database_directory()
    connection = sqlite3.connect(DB_PATH, timeout=30)
    configure_connection(connection)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_database_backup(reason: str) -> Path | None:
    if not DB_PATH.exists() or os.environ.get("BAKERY_POS_SKIP_DB_BACKUP") == "1":
        return None

    ensure_database_directory()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"bakery_pos-{reason}-{timestamp}.db"

    source = sqlite3.connect(DB_PATH)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    return backup_path


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_schema_version(connection: sqlite3.Connection) -> int:
    if not table_exists(connection, "schema_migrations"):
        return 0
    row = connection.execute("SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations").fetchone()
    return int(row["version"])


def record_migration(connection: sqlite3.Connection, version: int, name: str) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO schema_migrations (version, name)
        VALUES (?, ?)
        """,
        (version, name),
    )
    connection.execute(f"PRAGMA user_version = {version}")


def create_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )


def migration_001_base_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER NOT NULL DEFAULT 0 CHECK (sort_order >= 0),
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
            cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (cost_cents >= 0),
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            cashier_role TEXT NOT NULL,
            total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
            amount_received_cents INTEGER NOT NULL CHECK (amount_received_cents >= 0),
            change_due_cents INTEGER NOT NULL CHECK (change_due_cents >= 0),
            profit_cents INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
            unit_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (unit_cost_cents >= 0),
            line_total_cents INTEGER NOT NULL CHECK (line_total_cents >= 0),
            line_profit_cents INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )


def migration_002_indexes(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_products_category
            ON products(category_id);
        CREATE INDEX IF NOT EXISTS idx_products_name
            ON products(name);
        CREATE INDEX IF NOT EXISTS idx_products_active_category
            ON products(active, category_id);
        CREATE INDEX IF NOT EXISTS idx_sales_created_at
            ON sales(created_at);
        CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id
            ON sale_items(sale_id);
        CREATE INDEX IF NOT EXISTS idx_sale_items_product_id
            ON sale_items(product_id);
        """
    )


def migration_003_seed_catalog(connection: sqlite3.Connection) -> None:
    category_count = connection.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if category_count > 0:
        return

    for name, sort_order in SEED_CATEGORIES:
        connection.execute(
            """
            INSERT INTO categories (name, sort_order, active)
            VALUES (?, ?, 1)
            """,
            (name, sort_order),
        )

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


def migration_004_catalog_cleanup(connection: sqlite3.Connection) -> None:
    repair_known_catalog_issues(connection)


MIGRATIONS: tuple[Migration, ...] = (
    (1, "base_schema", migration_001_base_schema),
    (2, "performance_indexes", migration_002_indexes),
    (3, "seed_default_catalog", migration_003_seed_catalog),
    (4, "catalog_cleanup", migration_004_catalog_cleanup),
)


def normalize_category_name(value: object) -> str:
    name = str(value).strip()
    if name in {"Pastiçeri", "Pasti?eri", "PastiÃ§eri"}:
        return "Kifle"
    return name


def repair_known_catalog_issues(connection: sqlite3.Connection) -> None:
    legacy_names = ("Pastiçeri", "Pasti?eri", "PastiÃ§eri")
    placeholders = ", ".join("?" for _ in legacy_names)
    legacy_rows = list(
        connection.execute(
            f"SELECT id FROM categories WHERE name IN ({placeholders})",
            legacy_names,
        )
    )
    if not legacy_rows:
        return

    target = connection.execute(
        "SELECT id FROM categories WHERE name = ?",
        ("Kifle",),
    ).fetchone()

    if target is None:
        connection.execute(
            """
            UPDATE categories
            SET name = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            ("Kifle", legacy_rows[0]["id"]),
        )
        target_id = legacy_rows[0]["id"]
        duplicate_rows = legacy_rows[1:]
    else:
        target_id = target["id"]
        duplicate_rows = legacy_rows

    for legacy in duplicate_rows:
        connection.execute(
            """
            UPDATE products
            SET category_id = ?, updated_at = datetime('now', 'localtime')
            WHERE category_id = ?
            """,
            (target_id, legacy["id"]),
        )
        try:
            connection.execute("DELETE FROM categories WHERE id = ?", (legacy["id"],))
        except sqlite3.IntegrityError:
            connection.execute(
                """
                UPDATE categories
                SET active = 0, updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (legacy["id"],),
            )

    connection.execute(
        """
        UPDATE categories
        SET active = 1, sort_order = 20, updated_at = datetime('now', 'localtime')
        WHERE id = ?
        """,
        (target_id,),
    )


def assert_database_healthy(connection: sqlite3.Connection) -> None:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")

    foreign_key_issues = list(connection.execute("PRAGMA foreign_key_check"))
    if foreign_key_issues:
        details = ", ".join(
            f"{row['table']} row {row['rowid']}" for row in foreign_key_issues[:5]
        )
        raise RuntimeError(f"SQLite foreign key check failed: {details}")


def apply_migrations(connection: sqlite3.Connection) -> None:
    create_migration_table(connection)
    current_version = get_schema_version(connection)
    if current_version >= SCHEMA_VERSION:
        repair_known_catalog_issues(connection)
        assert_database_healthy(connection)
        connection.commit()
        return

    create_database_backup("before-migration")
    connection.execute("BEGIN IMMEDIATE")
    try:
        for version, name, migration in MIGRATIONS:
            if version <= current_version:
                continue
            migration(connection)
            record_migration(connection, version, name)
        repair_known_catalog_issues(connection)
        assert_database_healthy(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def initialize_database() -> None:
    ensure_database_directory()
    connection = sqlite3.connect(DB_PATH, timeout=30)
    configure_connection(connection)
    try:
        apply_migrations(connection)
    finally:
        connection.close()

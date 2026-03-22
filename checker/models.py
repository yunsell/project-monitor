import aiosqlite

DB_PATH = "monitor.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS check_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                check_label TEXT,
                last_data_at TEXT,
                prev_last_data_at TEXT,
                checked_at TEXT NOT NULL,
                status TEXT DEFAULT 'ok',
                error_message TEXT,
                UNIQUE(service_name, table_name)
            )
        """)
        # Migration: add prev_last_data_at if table already exists without it
        try:
            await db.execute("ALTER TABLE check_results ADD COLUMN prev_last_data_at TEXT")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS check_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                last_data_at TEXT,
                checked_at TEXT NOT NULL,
                status TEXT
            )
        """)
        await db.commit()


async def upsert_result(
    service_name: str,
    table_name: str,
    check_label: str,
    last_data_at: str | None,
    checked_at: str,
    status: str,
    error_message: str | None = None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO check_results
                (service_name, table_name, check_label, last_data_at, checked_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(service_name, table_name) DO UPDATE SET
                check_label = excluded.check_label,
                prev_last_data_at = check_results.last_data_at,
                last_data_at = excluded.last_data_at,
                checked_at = excluded.checked_at,
                status = excluded.status,
                error_message = excluded.error_message
            """,
            (service_name, table_name, check_label, last_data_at, checked_at, status, error_message),
        )
        await db.execute(
            """
            INSERT INTO check_history
                (service_name, table_name, last_data_at, checked_at, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (service_name, table_name, last_data_at, checked_at, status),
        )
        await db.commit()


async def get_all_results() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM check_results ORDER BY service_name, table_name"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_results_by_service(service_name: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM check_results WHERE service_name = ? ORDER BY table_name",
            (service_name,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_chart_data(service_name: str, table_name: str, days: int = 7) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT checked_at, status, last_data_at
            FROM check_history
            WHERE service_name = ? AND table_name = ?
              AND checked_at >= datetime('now', ?)
            ORDER BY checked_at ASC
            """,
            (service_name, table_name, f"-{days} days"),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_history(service_name: str, limit: int = 100) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM check_history
            WHERE service_name = ?
            ORDER BY checked_at DESC
            LIMIT ?
            """,
            (service_name, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

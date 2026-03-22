"""
Demo script: Inserts sample data into monitor.db so the dashboard
can be shown with realistic-looking results for screenshots.

Usage:
    python demo.py
    uvicorn api.main:app --port 8100
    # Open http://localhost:8100 in your browser
"""

import asyncio
from datetime import datetime, timedelta, timezone

from checker.models import init_db, upsert_result

NOW = datetime.now(timezone.utc)


DEMO_DATA = [
    # OK — recent data
    {
        "service_name": "ecommerce-api",
        "table_name": "orders",
        "check_label": "Order Data",
        "last_data_at": (NOW - timedelta(minutes=3)).isoformat(),
        "status": "ok",
    },
    {
        "service_name": "ecommerce-api",
        "table_name": "products",
        "check_label": "Product Catalog",
        "last_data_at": (NOW - timedelta(minutes=45)).isoformat(),
        "status": "ok",
    },
    # Warning — stale data
    {
        "service_name": "ecommerce-api",
        "table_name": "user_sessions",
        "check_label": "User Sessions",
        "last_data_at": (NOW - timedelta(hours=29)).isoformat(),
        "status": "warning",
    },
    # OK
    {
        "service_name": "payment-service",
        "table_name": "transactions",
        "check_label": "Transactions",
        "last_data_at": (NOW - timedelta(minutes=12)).isoformat(),
        "status": "ok",
    },
    {
        "service_name": "payment-service",
        "table_name": "refunds",
        "check_label": "Refund Records",
        "last_data_at": (NOW - timedelta(hours=2, minutes=15)).isoformat(),
        "status": "ok",
    },
    # Critical — very stale data
    {
        "service_name": "log-collector",
        "table_name": "app_logs",
        "check_label": "Application Logs",
        "last_data_at": (NOW - timedelta(days=4)).isoformat(),
        "status": "critical",
    },
    # Error — connection failure
    {
        "service_name": "log-collector",
        "table_name": "audit_logs",
        "check_label": "Audit Logs",
        "last_data_at": None,
        "status": "error",
        "error_message": "Can't connect to MySQL server on '192.168.1.100' (timed out)",
    },
    # OK
    {
        "service_name": "notification-service",
        "table_name": "email_queue",
        "check_label": "Email Queue",
        "last_data_at": (NOW - timedelta(minutes=7)).isoformat(),
        "status": "ok",
    },
    {
        "service_name": "notification-service",
        "table_name": "push_logs",
        "check_label": "Push Notifications",
        "last_data_at": (NOW - timedelta(hours=1, minutes=20)).isoformat(),
        "status": "ok",
    },
]


async def seed():
    await init_db()
    checked_at = NOW.isoformat()

    for d in DEMO_DATA:
        await upsert_result(
            service_name=d["service_name"],
            table_name=d["table_name"],
            check_label=d["check_label"],
            last_data_at=d["last_data_at"],
            checked_at=checked_at,
            status=d["status"],
            error_message=d.get("error_message"),
        )

    print(f"Inserted {len(DEMO_DATA)} demo records.")
    print()
    print("Now run the server:")
    print("  uvicorn api.main:app --port 8100")
    print()
    print("Open http://localhost:8100 in your browser to take a screenshot.")


if __name__ == "__main__":
    asyncio.run(seed())

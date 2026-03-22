import asyncio
from datetime import datetime, timezone

import pymysql

from checker.config_loader import load_config
from checker.models import upsert_result


def _query_last_data(service: dict, check: dict) -> tuple[str | None, str | None]:
    """Connect to MySQL and get MAX(column). Returns (iso_datetime_str, error_message)."""
    try:
        conn = pymysql.connect(
            host=service["host"],
            port=service.get("port", 3306),
            user=service["user"],
            password=service["password"],
            database=service["database"],
            connect_timeout=10,
            read_timeout=10,
        )
        try:
            with conn.cursor() as cursor:
                column = check["column"]
                table = check["table"]
                cursor.execute(f"SELECT MAX(`{column}`) AS last_data_at FROM `{table}`")
                row = cursor.fetchone()
                if row and row[0]:
                    val = row[0]
                    if isinstance(val, datetime):
                        return val.isoformat(), None
                    return str(val), None
                return None, None
        finally:
            conn.close()
    except Exception as e:
        return None, str(e)


def _determine_status(
    last_data_at: str | None,
    error_message: str | None,
    alert_threshold_hours: float,
    critical_threshold_hours: float,
) -> str:
    if error_message:
        return "error"
    if last_data_at is None:
        return "warning"
    try:
        dt = datetime.fromisoformat(last_data_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        hours_ago = (now - dt).total_seconds() / 3600
        if hours_ago >= critical_threshold_hours:
            return "critical"
        if hours_ago >= alert_threshold_hours:
            return "warning"
        return "ok"
    except (ValueError, TypeError):
        return "warning"


async def run_all_checks(config: dict | None = None):
    if config is None:
        config = load_config()

    monitor = config.get("monitor", {})
    alert_threshold = monitor.get("alert_threshold_hours", 24)
    critical_threshold = monitor.get("critical_threshold_hours", 72)

    checked_at = datetime.now(timezone.utc).isoformat()

    for service in config.get("services", []):
        for check in service.get("checks", []):
            last_data_at, error_message = await asyncio.to_thread(
                _query_last_data, service, check
            )
            status = _determine_status(
                last_data_at, error_message, alert_threshold, critical_threshold
            )
            await upsert_result(
                service_name=service["name"],
                table_name=check["table"],
                check_label=check.get("label", check["table"]),
                last_data_at=last_data_at,
                checked_at=checked_at,
                status=status,
                error_message=error_message,
            )

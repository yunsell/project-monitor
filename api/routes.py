import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from checker.config_loader import load_config
from checker.db_connector import run_all_checks
from checker.models import get_all_results, get_results_by_service, get_history, get_chart_data

router = APIRouter(prefix="/api")

_last_manual_check: float = 0.0
RATE_LIMIT_SECONDS = 30


def _calc_hours_ago(iso_str: str | None) -> float | None:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return round((now - dt).total_seconds() / 3600, 2)
    except (ValueError, TypeError):
        return None


def _calc_data_interval(prev: str | None, curr: str | None) -> float | None:
    if not prev or not curr:
        return None
    try:
        dt_prev = datetime.fromisoformat(prev)
        dt_curr = datetime.fromisoformat(curr)
        if dt_prev.tzinfo is None:
            dt_prev = dt_prev.replace(tzinfo=timezone.utc)
        if dt_curr.tzinfo is None:
            dt_curr = dt_curr.replace(tzinfo=timezone.utc)
        diff = (dt_curr - dt_prev).total_seconds() / 3600
        return round(diff, 2) if diff > 0 else None
    except (ValueError, TypeError):
        return None


@router.get("/status")
async def status():
    config = load_config()
    results = await get_all_results()

    service_map: dict[str, dict] = {}
    for svc in config.get("services", []):
        service_map[svc["name"]] = {
            "name": svc["name"],
            "description": svc.get("description", ""),
            "checks": [],
            "overall_status": "ok",
        }

    status_priority = {"critical": 3, "error": 3, "warning": 2, "ok": 1}

    for row in results:
        svc_name = row["service_name"]
        if svc_name not in service_map:
            service_map[svc_name] = {
                "name": svc_name,
                "description": "",
                "checks": [],
                "overall_status": "ok",
            }

        hours_ago = _calc_hours_ago(row["last_data_at"])
        data_interval = _calc_data_interval(row.get("prev_last_data_at"), row["last_data_at"])
        check_item = {
            "table": row["table_name"],
            "label": row["check_label"],
            "last_data_at": row["last_data_at"],
            "hours_ago": hours_ago,
            "data_interval": data_interval,
            "status": row["status"],
            "error_message": row.get("error_message"),
        }
        service_map[svc_name]["checks"].append(check_item)

        cur_priority = status_priority.get(row["status"], 0)
        overall_priority = status_priority.get(service_map[svc_name]["overall_status"], 0)
        if cur_priority > overall_priority:
            service_map[svc_name]["overall_status"] = row["status"]

    services = list(service_map.values())

    summary = {"total": 0, "ok": 0, "warning": 0, "critical": 0, "error": 0}
    for row in results:
        summary["total"] += 1
        s = row["status"]
        if s in summary:
            summary[s] += 1

    checked_at = results[0]["checked_at"] if results else None

    return {
        "checked_at": checked_at,
        "summary": summary,
        "services": services,
    }


@router.get("/status/{service_name}")
async def status_by_service(service_name: str):
    results = await get_results_by_service(service_name)
    if not results:
        return {"service_name": service_name, "checks": [], "message": "No data"}

    checks = []
    for row in results:
        hours_ago = _calc_hours_ago(row["last_data_at"])
        data_interval = _calc_data_interval(row.get("prev_last_data_at"), row["last_data_at"])
        checks.append({
            "table": row["table_name"],
            "label": row["check_label"],
            "last_data_at": row["last_data_at"],
            "hours_ago": hours_ago,
            "data_interval": data_interval,
            "status": row["status"],
            "error_message": row.get("error_message"),
        })

    return {
        "service_name": service_name,
        "checked_at": results[0]["checked_at"],
        "checks": checks,
    }


@router.get("/history/{service_name}")
async def history(service_name: str):
    rows = await get_history(service_name)
    return {"service_name": service_name, "history": rows}


@router.get("/chart/{service_name}/{table_name}")
async def chart(service_name: str, table_name: str, days: int = 7):
    rows = await get_chart_data(service_name, table_name, days)
    return {"service_name": service_name, "table_name": table_name, "data": rows}


@router.post("/check/now")
async def check_now(background_tasks: BackgroundTasks):
    global _last_manual_check
    now = time.time()
    elapsed = now - _last_manual_check
    if elapsed < RATE_LIMIT_SECONDS:
        remaining = int(RATE_LIMIT_SECONDS - elapsed)
        raise HTTPException(
            status_code=429,
            detail=f"{remaining}초 후에 다시 시도해주세요.",
        )
    _last_manual_check = now
    background_tasks.add_task(run_all_checks)
    return {"message": "Check triggered", "status": "running"}

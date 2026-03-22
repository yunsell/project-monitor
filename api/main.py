import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import router
from checker.config_loader import load_config
from checker.db_connector import run_all_checks
from checker.models import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    config = load_config()
    interval = config.get("monitor", {}).get("check_interval_minutes", 10)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_all_checks, "interval", minutes=interval)
    scheduler.start()

    # Run initial check in background (don't block startup)
    asyncio.create_task(run_all_checks(config))

    yield

    scheduler.shutdown()


app = FastAPI(title="Data Freshness Monitor", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

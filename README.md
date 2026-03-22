# Data Freshness Monitor

[한국어](./README.ko.md)

A monitoring tool that tracks the **last data insertion time** of each table across multiple MySQL/MariaDB databases and displays the results on a web dashboard.

> Solves the problem of not being able to tell in real time whether data is flowing into your services normally.

## Features

- **Multi-service monitoring** — manage multiple DB servers and tables with a single `config.yml`
- **Automatic periodic checks** — APScheduler-based, runs at configurable intervals (default: 10 min)
- **Web dashboard** — status summary badges, accordion service cards, 30-second auto-refresh
- **Dark mode** — toggle with localStorage persistence, auto-detects OS preference
- **History chart** — per-table data age trend visualization (last 7 days)
- **Status classification** — OK / Warning / Critical / Error based on data age
- **Environment variable support** — sensitive info like DB passwords managed via `.env`
- **Manual check** — trigger an immediate check from the dashboard
- **Rate limiting** — `/api/check/now` limited to once per 30 seconds

## Status Criteria

| Status | Condition | Default |
|--------|-----------|---------|
| OK | Last data within alert threshold | Within 24 hours |
| Warning | Last data exceeds alert threshold, or NULL | Over 24 hours |
| Critical | Last data exceeds critical threshold | Over 72 hours |
| Error | DB connection failure or query error | - |

Thresholds are configurable in the `monitor` section of `config.yml`.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Checker Engine | Python + APScheduler |
| Backend API | FastAPI (async) |
| Meta Storage | SQLite (aiosqlite) |
| Frontend | HTML + CSS + JS (single file, no build step) |
| DB Connector | PyMySQL |

## Project Structure

```
project-monitor/
├── config.example.yml       # Configuration template
├── .env.example             # Environment variables template
├── requirements.txt
├── checker/
│   ├── config_loader.py     # Load config.yml + ${ENV_VAR} substitution
│   ├── db_connector.py      # MySQL connection + MAX query + status logic
│   └── models.py            # SQLite table creation + CRUD
├── api/
│   ├── main.py              # FastAPI app + APScheduler (single process)
│   └── routes.py            # API endpoints
└── frontend/
    └── index.html           # Dashboard UI
```

## Quick Start

```bash
# 1. Create and activate virtual environment
python3 -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Prepare configuration files
cp config.example.yml config.yml   # Configure monitoring targets
cp .env.example .env               # Enter DB credentials

# 4. Edit config.yml and .env to match your environment

# 5. Start the server
uvicorn api.main:app --reload --port 8100

# 6. Open in browser
open http://localhost:8100
```

## Configuration

### config.yml

```yaml
monitor:
  check_interval_minutes: 10    # Check interval (minutes)
  alert_threshold_hours: 24     # Warning threshold (hours)
  critical_threshold_hours: 72  # Critical threshold (hours)

services:
  - name: "my-service"
    description: "My service description"
    host: "localhost"
    port: 3306
    user: "${DB_USER}"          # Reference .env variable
    password: "${DB_PASS}"
    database: "my_database"
    checks:
      - table: "orders"
        column: "created_at"    # Column for MAX() query
        label: "Order Data"     # Display name on dashboard
```

### .env

```
DB_USER=your_db_user
DB_PASS=your_db_password
```

Use `${VAR_NAME}` syntax in `config.yml` to reference environment variables from `.env`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/status` | All services status (summary + per-service checks) |
| GET | `/api/status/{service_name}` | Single service details |
| GET | `/api/history/{service_name}` | Check history |
| GET | `/api/chart/{service_name}/{table_name}` | Chart data (last 7 days) |
| POST | `/api/check/now` | Trigger immediate check (rate limited: 30s) |

### Response Example — `GET /api/status`

```json
{
  "checked_at": "2026-03-19T14:30:00",
  "summary": {
    "total": 4,
    "ok": 2,
    "warning": 1,
    "critical": 0,
    "error": 1
  },
  "services": [
    {
      "name": "ecommerce-api",
      "description": "E-commerce order service",
      "checks": [
        {
          "table": "orders",
          "label": "Order Data",
          "last_data_at": "2026-03-19T14:25:33",
          "hours_ago": 0.07,
          "status": "ok"
        }
      ],
      "overall_status": "ok"
    }
  ]
}
```

## Deployment (Optional)

### systemd Service

```ini
# /etc/systemd/system/data-monitor.service
[Unit]
Description=Data Freshness Monitor
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/project-monitor
EnvironmentFile=/path/to/project-monitor/.env
ExecStart=/path/to/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8100
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name monitor.yourdomain.com;

    location / {
        root /path/to/project-monitor/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## License

MIT License

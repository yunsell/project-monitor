# Data Freshness Monitor — 구현 계획서

## 프로젝트 개요

여러 서비스의 MySQL/MariaDB 데이터베이스를 모니터링하여, 각 테이블의 마지막 데이터 입력 시각을 웹 대시보드에서 한눈에 확인할 수 있는 오픈소스 관리 도구.

서비스 운영 중 "데이터가 정상적으로 들어오고 있는가?"를 실시간으로 파악하기 어려운 문제를 해결합니다. `config.yml` 하나로 모니터링 대상을 설정하고, 웹 대시보드에서 전체 상태를 한눈에 확인할 수 있습니다.

## 기술 스택

| 영역 | 기술 | 선택 이유 |
|------|------|-----------|
| Checker 엔진 | Python + APScheduler | 가볍고 유연한 스케줄링 |
| Backend API | FastAPI | 고성능 비동기 지원, 자동 문서 생성 |
| Meta Storage | SQLite (기본) → MySQL/PostgreSQL (확장 시) | 별도 DB 서버 불필요, 빠른 시작 |
| Frontend | 순수 HTML + CSS + JavaScript (단일 파일) | 빌드 도구 불필요, Nginx에서 바로 서빙 |
| 배포 | Nginx + systemd | 정적 파일 서빙 + 리버스 프록시 |

---

## Phase 1: 프로젝트 셋업 + Config 설계 (Day 1 전반)

### 목표
프로젝트 디렉토리 구조를 만들고, 모니터링 대상 서비스를 config 파일로 관리할 수 있게 한다.

### 디렉토리 구조

```
data-freshness-monitor/
├── config.example.yml      # 설정 파일 템플릿 (Git 추적)
├── config.yml              # 실제 설정 파일 (.gitignore)
├── .env.example            # 환경변수 템플릿 (Git 추적)
├── .env                    # 실제 환경변수 (.gitignore)
├── .gitignore
├── checker/
│   ├── __init__.py
│   ├── config_loader.py    # config.yml 로드 + 환경변수 치환
│   ├── db_connector.py     # MySQL 접속 + 쿼리 실행
│   └── models.py           # SQLAlchemy 모델 (Meta DB)
├── api/
│   ├── __init__.py
│   ├── main.py             # FastAPI 앱 + APScheduler (단일 프로세스)
│   └── routes.py           # API 엔드포인트
├── frontend/
│   └── index.html          # 대시보드 (HTML + CSS + JS 단일 파일)
├── requirements.txt
└── README.md
```

### config.yml 설계

```yaml
# 모니터링 설정
monitor:
  check_interval_minutes: 10    # 체크 주기
  alert_threshold_hours: 24     # 이 시간 이상 데이터 없으면 경고
  critical_threshold_hours: 72  # 이 시간 이상이면 위험

# 알림 설정
alert:
  enabled: false                         # true로 변경하여 활성화
  type: "slack"                          # slack / discord / custom_webhook
  webhook_url: "${SLACK_WEBHOOK_URL}"    # .env에서 관리

# 모니터링 대상 서비스
services:
  - name: "ecommerce-api"
    description: "이커머스 주문 서비스"
    host: "localhost"
    port: 3306
    user: "${DB_USER}"               # 환경변수 참조
    password: "${DB_PASS}"
    database: "ecommerce_db"
    checks:
      - table: "orders"
        column: "created_at"
        label: "주문 데이터"
      - table: "user_sessions"
        column: "last_active"
        label: "사용자 세션"

  - name: "payment-service"
    description: "결제 처리 서비스"
    host: "db.example.com"
    port: 3306
    user: "${PAYMENT_DB_USER}"
    password: "${PAYMENT_DB_PASS}"
    database: "payment_db"
    checks:
      - table: "transactions"
        column: "processed_at"
        label: "결제 트랜잭션"

  - name: "log-collector"
    description: "로그 수집 서비스"
    host: "192.168.1.100"
    port: 3306
    user: "${LOG_DB_USER}"
    password: "${LOG_DB_PASS}"
    database: "log_db"
    checks:
      - table: "app_logs"
        column: "logged_at"
        label: "애플리케이션 로그"
```

### requirements.txt

```
fastapi
uvicorn[standard]
apscheduler
pymysql
pyyaml
python-dotenv
aiosqlite
sqlalchemy
httpx
```

### 작업 체크리스트

- [ ] 프로젝트 디렉토리 생성
- [ ] `config.example.yml` 작성 (위 템플릿 기반)
- [ ] `.env.example` 파일 작성 (환경변수 템플릿)
- [ ] `.gitignore` 작성 (`config.yml`, `.env`, `*.db`, `__pycache__/`, `venv/` 등)
- [ ] `requirements.txt` 작성
- [ ] Git 저장소 초기화

---

## Phase 2: Checker 엔진 + API 서버 (Day 1 후반 ~ Day 2)

### 목표
실제 DB에 접속하여 마지막 데이터 시각을 가져오고, API로 결과를 제공한다.

### 실행 구조

Checker(APScheduler)와 API(FastAPI)를 **하나의 프로세스**로 실행한다.
FastAPI의 `lifespan` 이벤트에서 APScheduler를 시작하고, uvicorn 하나로 모든 기능이 동작한다.

```python
# api/main.py — 단일 프로세스 구조
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_all_checks, "interval", minutes=config["monitor"]["check_interval_minutes"])
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

### 환경변수 처리

`config.yml`의 `${VAR_NAME}` 패턴은 `os.environ`으로 치환한다. `.env` 파일은 `python-dotenv`로 로드한다.

```python
# checker/config_loader.py
import os, re, yaml
from dotenv import load_dotenv

load_dotenv()

def load_config(path="config.yml"):
    with open(path) as f:
        raw = f.read()
    # ${VAR_NAME} 패턴을 환경변수 값으로 치환
    resolved = re.sub(r'\$\{(\w+)\}', lambda m: os.environ.get(m.group(1), ""), raw)
    return yaml.safe_load(resolved)
```

### 핵심 로직: checker/db_connector.py

```python
# 핵심 쿼리 (서비스별로 실행)
SELECT MAX({column}) as last_data_at FROM {table}
```

각 서비스의 각 테이블에 대해 위 쿼리를 실행하고, 결과를 Meta DB에 저장.

### Meta DB 스키마 (SQLite)

```sql
CREATE TABLE check_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    check_label TEXT,
    last_data_at DATETIME,          -- 해당 테이블의 마지막 데이터 시각
    checked_at DATETIME NOT NULL,   -- 체크를 실행한 시각
    status TEXT DEFAULT 'ok',       -- ok / warning / critical / error
    error_message TEXT,             -- 접속 실패 시 에러 메시지
    UNIQUE(service_name, table_name)
);

CREATE TABLE check_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    last_data_at DATETIME,
    checked_at DATETIME NOT NULL,
    status TEXT
);
```

### API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/status` | 전체 서비스 상태 (최신 체크 결과) |
| GET | `/api/status/{service_name}` | 특정 서비스 상세 |
| GET | `/api/history/{service_name}` | 체크 이력 (최근 7일) |
| POST | `/api/check/now` | 즉시 체크 실행 (수동 트리거) |

### `/api/status` 응답 예시

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
      "description": "이커머스 주문 서비스",
      "checks": [
        {
          "table": "orders",
          "label": "주문 데이터",
          "last_data_at": "2026-03-19T14:25:33",
          "hours_ago": 0.07,
          "status": "ok"
        },
        {
          "table": "user_sessions",
          "label": "사용자 세션",
          "last_data_at": "2026-03-18T09:10:00",
          "hours_ago": 29.3,
          "status": "warning"
        }
      ],
      "overall_status": "warning"
    }
  ]
}
```

### 작업 체크리스트

- [ ] `checker/config_loader.py` — config.yml 로드 + 환경변수 치환 (python-dotenv + os.environ)
- [ ] `checker/db_connector.py` — PyMySQL로 MySQL 접속 + MAX 쿼리 실행
- [ ] `checker/models.py` — SQLite 테이블 생성 + CRUD (aiosqlite)
- [ ] `api/main.py` — FastAPI 앱 + CORS 설정 + lifespan에서 AsyncIOScheduler 시작
- [ ] `api/routes.py` — 4개 엔드포인트 구현
- [ ] 터미널에서 `uvicorn api.main:app --port 8100` 으로 동작 확인
- [ ] `curl localhost:8100/api/status` 로 API 응답 확인

---

## Phase 3: 웹 대시보드 UI (Day 2 ~ Day 3)

### 목표
브라우저에서 전체 서비스 상태를 한눈에 확인할 수 있는 대시보드를 만든다.

### 대시보드 화면 구성

```
┌─────────────────────────────────────────────────┐
│  Data Freshness Monitor          [🔄 새로고침]   │
│  마지막 체크: 2026-03-19 14:30:00               │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ 🟢 2    │ │ 🟡 1    │ │ 🔴 0    │  요약 뱃지│
│  │ 정상    │ │ 경고    │ │ 위험    │           │
│  └─────────┘ └─────────┘ └─────────┘           │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ ecommerce-api                   🟡 경고  │   │
│  │ ┌─ orders         14:25 (5분 전)   🟢  │   │
│  │ └─ user_sessions  어제 09:10 (29h) 🟡  │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ payment-service                  🟢 정상 │   │
│  │ └─ transactions   14:20 (10분 전)  🟢  │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ log-collector                   🔴 에러  │   │
│  │ └─ app_logs       접속 실패        🔴  │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### UI 핵심 요소

1. **요약 뱃지**: 상단에 정상/경고/위험 개수를 한눈에
2. **서비스 카드**: 접고 펼 수 있는 아코디언 형태
3. **상태 색상**: 초록(정상) / 노랑(경고, threshold 초과) / 빨강(위험 또는 에러)
4. **상대 시간 표시**: "5분 전", "2시간 전", "3일 전" 형태
5. **자동 갱신**: 30초마다 API 호출하여 자동 업데이트
6. **수동 체크 버튼**: 즉시 전체 체크 트리거

### 작업 체크리스트

- [ ] `frontend/index.html` 기본 레이아웃
- [ ] API 연동 (fetch → 렌더링)
- [ ] 상태별 색상 코딩
- [ ] 상대 시간 계산 로직
- [ ] 자동 갱신 (setInterval 30초)
- [ ] 수동 체크 버튼 연동
- [ ] Nginx 설정 (정적 파일 서빙)
- [ ] 브라우저에서 전체 흐름 테스트

---

## Phase 4: 배포 + 알림 (Day 3 ~ Day 4, 선택)

### 목표
서버에서 자동 실행되게 하고, 데이터 지연 시 알림을 보낸다.

### 4-1. systemd 서비스 등록

```ini
# /etc/systemd/system/data-monitor.service
[Unit]
Description=Data Freshness Monitor
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/data-freshness-monitor
EnvironmentFile=/path/to/data-freshness-monitor/.env
ExecStart=/path/to/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8100
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4-2. Nginx 리버스 프록시 설정

```nginx
# /etc/nginx/sites-available/data-monitor
server {
    listen 80;
    server_name monitor.yourdomain.com;

    # 대시보드 UI (정적 파일)
    location / {
        root /path/to/data-freshness-monitor/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 리버스 프록시
    location /api/ {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4-3. 알림 — Slack Webhook (기본 구현)

Slack Incoming Webhook을 기본 알림으로 구현한다. `config.yml`에 webhook URL을 설정한다.

```yaml
# config.yml 알림 설정 추가
alert:
  enabled: true
  type: "slack"                          # slack / discord / custom_webhook
  webhook_url: "${SLACK_WEBHOOK_URL}"    # 환경변수로 관리
```

### 알림 트리거 로직

```python
# checker에서 상태 변경 시 알림
if previous_status == "ok" and current_status == "warning":
    send_alert(f"⚠️ {service_name}/{table_name}: {hours_ago}시간 동안 데이터 없음")

if previous_status != "error" and current_status == "error":
    send_alert(f"🔴 {service_name}: DB 접속 실패 - {error_message}")
```

향후 Discord Webhook, 커스텀 Webhook 등으로 확장 가능하도록 `send_alert()` 함수를 `alert_type`에 따라 분기하는 구조로 작성한다.

### 작업 체크리스트

- [ ] systemd 서비스 파일 작성
- [ ] Nginx 설정 파일 작성
- [ ] 알림 방식 선택 + 연동
- [ ] 알림 테스트
- [ ] 최종 동작 확인

---

## 빠른 시작

```bash
# 1. 저장소 클론
git clone https://github.com/your-username/data-freshness-monitor.git
cd data-freshness-monitor

# 2. 가상환경 생성 및 활성화
python3 -m venv venv && source venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 설정 파일 준비
cp config.example.yml config.yml   # 모니터링 대상 서비스 설정
cp .env.example .env               # DB 접속 정보 입력

# 5. 개발 서버 실행
uvicorn api.main:app --reload --port 8100

# 6. 브라우저에서 확인
open http://localhost:8100
```

---

## 확장 아이디어

- 데이터 추이 차트 (최근 7일간 데이터 입력 빈도)
- 서비스 그룹핑 (팀별, 프로젝트별)
- 체크 대상 테이블을 웹 UI에서 동적 추가/삭제
- 여러 DB 종류 지원 (PostgreSQL, MongoDB 커넥터 추가)
- 모바일 반응형 UI
- Prometheus 메트릭 내보내기 (`/metrics` 엔드포인트)
- Grafana 대시보드 연동

---

## 기여하기

이슈와 PR을 환영합니다! 새로운 DB 커넥터 추가, 알림 채널 확장, UI 개선 등 어떤 기여든 좋습니다.

## 라이선스

MIT License

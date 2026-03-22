# Data Freshness Monitor

[English](./README.md)

여러 서비스의 MySQL/MariaDB 데이터베이스를 모니터링하여, 각 테이블의 **마지막 데이터 입력 시각**을 웹 대시보드에서 한눈에 확인할 수 있는 관리 도구입니다.

> "데이터가 정상적으로 들어오고 있는가?"를 실시간으로 파악하기 어려운 문제를 해결합니다.

## 주요 기능

- **다중 서비스 모니터링** — `config.yml` 하나로 여러 DB 서버의 여러 테이블을 관리
- **자동 주기 체크** — APScheduler 기반, 설정한 간격(기본 10분)마다 자동 실행
- **웹 대시보드** — 상태 요약 뱃지, 서비스별 아코디언 카드, 30초 자동 갱신
- **다크 모드** — 토글 전환, localStorage 저장, OS 설정 자동 감지
- **히스토리 차트** — 테이블별 데이터 경과 시간 추이 시각화 (최근 7일)
- **상태 판단** — 데이터 경과 시간 기반 OK / Warning / Critical / Error 분류
- **환경변수 지원** — DB 비밀번호 등 민감 정보를 `.env`로 분리 관리
- **수동 체크** — 대시보드에서 버튼 클릭으로 즉시 전체 체크 실행
- **호출 제한** — `/api/check/now` 30초당 1회 제한

## 상태 판단 기준

| 상태 | 조건 | 기본값 |
|------|------|--------|
| OK | 마지막 데이터가 threshold 이내 | 24시간 이내 |
| Warning | 마지막 데이터가 alert threshold 초과, 또는 데이터 없음(NULL) | 24시간 초과 |
| Critical | 마지막 데이터가 critical threshold 초과 | 72시간 초과 |
| Error | DB 접속 실패 또는 쿼리 에러 | - |

threshold 값은 `config.yml`의 `monitor` 섹션에서 변경할 수 있습니다.

## 기술 스택

| 영역 | 기술 |
|------|------|
| Checker 엔진 | Python + APScheduler |
| Backend API | FastAPI (비동기) |
| Meta Storage | SQLite (aiosqlite) |
| Frontend | HTML + CSS + JS (단일 파일, 빌드 불필요) |
| DB 접속 | PyMySQL |

## 프로젝트 구조

```
project-monitor/
├── config.example.yml       # 설정 파일 템플릿
├── .env.example             # 환경변수 템플릿
├── requirements.txt
├── checker/
│   ├── config_loader.py     # config.yml 로드 + ${ENV_VAR} 치환
│   ├── db_connector.py      # MySQL 접속 + MAX 쿼리 + 상태 판단
│   └── models.py            # SQLite 테이블 생성 + CRUD
├── api/
│   ├── main.py              # FastAPI 앱 + APScheduler (단일 프로세스)
│   └── routes.py            # API 엔드포인트
└── frontend/
    └── index.html           # 대시보드 UI
```

## 빠른 시작

```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv venv && source venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 설정 파일 준비
cp config.example.yml config.yml   # 모니터링 대상 서비스 설정
cp .env.example .env               # DB 접속 정보 입력

# 4. config.yml과 .env를 실제 환경에 맞게 수정

# 5. 서버 실행
uvicorn api.main:app --reload --port 8100

# 6. 브라우저에서 확인
open http://localhost:8100
```

## 설정

### config.yml

```yaml
monitor:
  check_interval_minutes: 10    # 체크 주기 (분)
  alert_threshold_hours: 24     # Warning 기준 (시간)
  critical_threshold_hours: 72  # Critical 기준 (시간)

services:
  - name: "my-service"
    description: "서비스 설명"
    host: "localhost"
    port: 3306
    user: "${DB_USER}"          # .env 환경변수 참조
    password: "${DB_PASS}"
    database: "my_database"
    checks:
      - table: "orders"
        column: "created_at"    # MAX() 쿼리 대상 컬럼
        label: "주문 데이터"     # 대시보드 표시명
```

### .env

```
DB_USER=your_db_user
DB_PASS=your_db_password
```

`config.yml`에서 `${VAR_NAME}` 형태로 환경변수를 참조하면, `.env` 파일의 값으로 자동 치환됩니다.

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/status` | 전체 서비스 상태 (요약 + 서비스별 체크 결과) |
| GET | `/api/status/{service_name}` | 특정 서비스 상세 |
| GET | `/api/history/{service_name}` | 체크 이력 |
| GET | `/api/chart/{service_name}/{table_name}` | 차트 데이터 (최근 7일) |
| POST | `/api/check/now` | 즉시 체크 실행 (30초 제한) |

### 응답 예시 — `GET /api/status`

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
        }
      ],
      "overall_status": "ok"
    }
  ]
}
```

## 배포 (선택)

### systemd 서비스

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

### Nginx 리버스 프록시

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

## 라이선스

MIT License

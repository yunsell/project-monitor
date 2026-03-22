# Data Freshness Monitor — 개선 체크리스트

## 안정성 / 보안

- [ ] SQL Injection 방어 (테이블/컬럼명 검증)
- [ ] 알림 시스템 구현 (Slack / Discord Webhook)
- [ ] 헬스체크 엔드포인트 (`/api/health`)
- [ ] 로깅 시스템 (파일 + 콘솔 로그)
- [ ] config.yml 유효성 검증
- [x] `/api/check/now` 호출 제한 (Rate Limit)

## 기능 개선

- [x] 히스토리 차트 (최근 7일 데이터 추이 시각화)
- [ ] 히스토리 페이지네이션 (날짜 범위 / 페이지 지정)
- [ ] 히스토리 자동 정리 (보존 기간 설정)
- [ ] 서비스 필터 / 검색
- [ ] 상태별 정렬 (Error/Critical 우선)
- [ ] 체크 실행 시간 기록
- [ ] config 핫 리로드
- [ ] 타임존 설정

## 대시보드 UX

- [x] 다크 모드
- [ ] 브라우저 Push 알림
- [ ] CSV / JSON 내보내기
- [ ] 서비스 그룹핑 (팀별, 프로젝트별)
- [ ] 수동 체크 완료 피드백 개선

## 확장성

- [ ] PostgreSQL / MongoDB 지원
- [ ] 인증 / 권한 (로그인)
- [ ] Prometheus `/metrics` 엔드포인트
- [ ] Docker 지원 (Dockerfile + docker-compose)
- [ ] 테스트 코드 (유닛 / 통합)

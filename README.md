# rissmeta-agent

교육학 메타분석 지원 AI 에이전트 저장소다.

현재 저장소에는 연구 문서, 구현 계획, 그리고 실제 구현을 시작할 수 있는 백엔드/프론트엔드 프로토타입이 포함되어 있다.

## 포함 내용

- `research.md`: 제품/연구 문서
- `plan.md`: 구현 계획
- `docs/architecture.md`: 현재 아키텍처 메모
- `backend`: FastAPI 기반 API 및 도메인 로직
- `frontend`: 정적 대시보드 프로토타입

## 현재 구현 범위

- 파일 기반 영속 저장소
- 선택 가능한 `SQLAlchemy/PostgreSQL` 저장소
- 검색 요청 생성/목록/요약
- rerun 시 이전 결과 reset
- KCI live-or-stub 수집 경로
- RISS configurable live-or-stub 수집 경로
- 중복 제거
- 규칙 기반 1차 선별
- 대시보드 기반 수동 선별
- 후보 상세 조회와 검토 큐 API
- PRISMA 집계
- 원문 아티팩트 등록
- TXT/PDF 업로드 기반 원문 저장
- OpenAI Responses API 기반 추출 경로
- 효과크기 계산 가능성 요약과 메타분석 입력 CSV 강화
- OpenAI 미설정 시 휴리스틱 fallback 추출
- 후보/스크리닝/PRISMA/추출/audit report export

## 빠른 시작

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload
```

기본 주소: `http://127.0.0.1:8000`

런타임 데이터는 `backend/data/store.json`에 저장된다.
업로드된 원문 파일은 `backend/uploads`에 저장된다.

### Optional Repository / KCI / RISS / OpenAI config

`backend/.env.example`에 있는 값을 환경변수로 채우면 저장소 모드, KCI live 요청, RISS live 요청, OpenAI 추출을 바꿀 수 있다.

- 기본 저장소는 `REPOSITORY_BACKEND=file` 이다.
- `REPOSITORY_BACKEND=sqlalchemy` 와 `DATABASE_URL=postgresql+psycopg://...` 를 설정하면 데이터베이스 저장소를 사용한다.
- KCI가 설정되지 않았거나 요청이 실패하면 스텁 데이터로 fallback 한다.
- RISS가 설정되지 않았거나 요청이 실패하면 스텁 데이터로 fallback 한다.
- OpenAI가 설정되지 않았거나 요청이 실패하면 휴리스틱 추출 결과를 저장한다.

### Frontend

`frontend/index.html`을 브라우저에서 열면 된다. 백엔드가 먼저 실행 중이어야 한다.

현재 프론트엔드는 검색 실행, 수동 선별, 검토 큐 확인, 후보 상세 조회, TXT/PDF 업로드, 추출 실행, PRISMA/스크리닝/audit export 조회까지 한 화면에서 확인하는 형태다.

## 노출된 API

- `GET /api/search-requests`
- `POST /api/search-requests`
- `GET /api/search-requests/{id}`
- `GET /api/search-requests/{id}/summary`
- `POST /api/search-requests/{id}/run`
- `GET /api/search-requests/{id}/candidates`
- `GET /api/search-requests/{id}/review-queue`
- `GET /api/candidates/{id}`
- `POST /api/candidates/{id}/decision`
- `POST /api/candidates/{id}/full-text`
- `POST /api/candidates/{id}/full-text-file`
- `POST /api/candidates/{id}/extract`
- `GET /api/candidates/{id}/extraction`
- `GET /api/search-requests/{id}/prisma`
- `GET /api/search-requests/{id}/exports/candidates.csv`
- `GET /api/search-requests/{id}/exports/screening-log.json`
- `GET /api/search-requests/{id}/exports/prisma-counts.json`
- `GET /api/search-requests/{id}/exports/extraction-results.json`
- `GET /api/search-requests/{id}/exports/meta-analysis-ready.csv`
- `GET /api/search-requests/{id}/exports/audit-report.md`

## 아직 미구현

- RISS 실운영 엔드포인트별 매핑 검증
- PostgreSQL 마이그레이션 체계
- PDF 파싱 고도화/OCR
- 인증/권한

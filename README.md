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
- 검색 요청 생성/목록/요약
- rerun 시 이전 결과 reset
- KCI live-or-stub 수집 경로
- RISS 스텁 기반 후보 수집
- 중복 제거
- 규칙 기반 1차 선별
- PRISMA 집계
- 후보 목록 조회
- 후보 CSV export
- screening log JSON export
- PRISMA counts JSON export
- 원문 아티팩트 등록 API
- 추출 프리뷰 자리표시자 API

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

### Optional KCI live config

`backend/.env.example`에 있는 값을 환경변수로 채우면 KCI live 요청을 시도한다. 설정이 없거나 요청이 실패하면 스텁 데이터로 자동 fallback 한다.

### Frontend

`frontend/index.html`을 브라우저에서 열면 된다. 백엔드가 먼저 실행 중이어야 한다.

## 노출된 API

- `GET /api/search-requests`
- `POST /api/search-requests`
- `GET /api/search-requests/{id}`
- `GET /api/search-requests/{id}/summary`
- `POST /api/search-requests/{id}/run`
- `GET /api/search-requests/{id}/candidates`
- `POST /api/candidates/{id}/decision`
- `POST /api/candidates/{id}/full-text`
- `GET /api/candidates/{id}/extraction`
- `GET /api/search-requests/{id}/prisma`
- `GET /api/search-requests/{id}/exports/candidates.csv`
- `GET /api/search-requests/{id}/exports/screening-log.json`
- `GET /api/search-requests/{id}/exports/prisma-counts.json`

## 아직 미구현

- 실제 RISS 연동
- OpenAI Responses API 기반 추출
- PostgreSQL / Redis
- PDF 파싱/OCR
- 인증/권한

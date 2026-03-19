# rissmeta-agent

교육학 메타분석 지원 AI 에이전트 초기 골격이다.

현재 포함 내용:

- `research.md`: 제품/연구 문서
- `plan.md`: 구현 계획
- `backend`: FastAPI 기반 API 및 도메인 로직 골격
- `frontend`: 최소 대시보드 프로토타입

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

### Frontend

`frontend/index.html`은 정적 프로토타입이다. 브라우저에서 직접 열거나 정적 서버로 서빙하면 된다.

## 현재 상태

초기 구현 범위:

- 검색 요청 생성
- KCI/RISS 스텁 기반 후보 수집
- 중복 제거
- 규칙 기반 1차 선별
- PRISMA 집계
- API 응답 제공

아직 미구현:

- 실제 KCI/RISS 연동
- OpenAI 추출
- 영속 DB
- PDF 업로드/파싱
- 인증/권한

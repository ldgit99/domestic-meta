# Backend

FastAPI 기반 초기 백엔드 구현이다.

## 포함 기능

- 검색 요청 생성 및 조회
- 파일 기반 영속 저장소
- rerun-safe 수집 실행
- 후보 논문 조회
- PRISMA 집계 조회
- 규칙 기반 1차 선별
- KCI live-or-stub 커넥터
- RISS 스텁 커넥터
- 원문 등록
- OpenAI Responses API 기반 추출 경로
- 휴리스틱 fallback 추출

## KCI 연동

기본값은 스텁이다. 아래 환경변수를 설정하면 live 요청을 시도하고, 실패 시 스텁으로 자동 fallback 한다.

- `KCI_LIVE_ENABLED=true`
- `KCI_API_URL`
- `KCI_API_KEY`
- `KCI_API_KEY_PARAM`
- `KCI_QUERY_PARAM`
- `KCI_COUNT_PARAM`
- `KCI_RESPONSE_FORMAT`

## OpenAI 추출

아래 환경변수를 설정하면 `Responses API`와 `Structured Outputs` 기반 추출을 시도한다.

- `OPENAI_API_KEY`
- `OPENAI_MODEL_EXTRACTION`
- `OPENAI_RESPONSES_URL`

설정이 없거나 요청이 실패하면 휴리스틱 추출 결과를 저장한다.

## 추후 연결 예정

- 실제 RISS Linked Data 수집기
- PostgreSQL 및 Redis
- PDF OCR 및 정교한 파서

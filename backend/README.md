# Backend

FastAPI 기반 초기 백엔드 구현이다.

## 포함 기능

- 검색 요청 생성 및 조회
- 파일 기반 영속 저장소
- 수집 실행
- 후보 논문 조회
- PRISMA 집계 조회
- 규칙 기반 1차 선별
- KCI/RISS 커넥터 인터페이스와 스텁 구현
- KCI live path 준비 완료

## KCI 연동

기본값은 스텁이다. 아래 환경변수를 설정하면 live 요청을 시도하고, 실패 시 스텁으로 자동 fallback 한다.

- `KCI_LIVE_ENABLED=true`
- `KCI_API_URL`
- `KCI_API_KEY`
- `KCI_API_KEY_PARAM`
- `KCI_QUERY_PARAM`
- `KCI_COUNT_PARAM`
- `KCI_RESPONSE_FORMAT`

## 추후 연결 예정

- 실제 RISS Linked Data 수집기
- PostgreSQL 및 Redis
- OpenAI 기반 원문 추출

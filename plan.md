# 교육학 메타분석 지원 AI 에이전트 구현 계획

## 1. 목표와 구현 원칙

이 계획의 목표는 [research.md](d:\OneDrive\Agent\rissmeta-agent\research.md)를 구현 가능한 수준의 아키텍처와 작업 단위로 구체화하는 것이다. 초기 제품은 교육학 논문의 메타분석 준비를 지원하는 반자동 시스템으로 정의한다.

핵심 원칙은 다음과 같다.

- `공식 데이터 접근 경로 우선`
- `PRISMA 2020` 기준의 추적 가능한 선별 로그
- `사람 검토를 전제로 한 AI 보조`
- `MVP 우선, RISS 고도화는 후속 단계`
- `검색-선별-추출` 단계를 독립 서비스와 데이터 모델로 분리

## 2. 제품 범위

### 2.1 MVP 범위

- 웹 대시보드에서 교육학 검색어 입력
- `KCI` 기반 후보 논문 메타데이터 수집
- `RISS`는 보조 경로로 최소 연동
- 후보 논문 정규화와 중복 제거
- 제목/초록 기반 1차 선별
- 원문 업로드 또는 링크 기반 원문 확보
- OpenAI API를 활용한 구조화 데이터 추출
- `PRISMA flow diagram`용 수치 자동 집계
- 검토용 산출물 다운로드

### 2.2 MVP 제외 범위

- 완전 자동 최종 포함 결정
- 비공식 대량 크롤링
- 전 분야 메타분석 일반화
- 자동 효과크기 통합 계산 엔진
- 사용자 계정/권한 고도화

## 3. 제안 아키텍처

### 3.1 상위 구조

시스템은 아래 5개 계층으로 구성한다.

1. `Frontend`
2. `API`
3. `Orchestrator/Workers`
4. `Database/Storage`
5. `External Integrations`

### 3.2 서비스 구성

#### Frontend

- 기술: `Next.js`
- 역할:
  - 검색 조건 입력
  - 작업 실행 상태 확인
  - 후보 논문 리스트와 선별 결과 표시
  - PRISMA 수치와 흐름도 시각화
  - 원문 업로드
  - 추출 결과 검토 및 다운로드

#### API

- 기술: `FastAPI`
- 역할:
  - 프론트엔드 요청 수신
  - 검색 요청 생성
  - 작업 큐 등록
  - 결과 조회 API 제공
  - PRISMA/추출 산출물 export 제공

#### Orchestrator / Workers

- 기술: `Python + Celery`
- 역할:
  - 소스별 수집 작업 실행
  - 중복 제거
  - 선별 작업
  - 원문 파싱
  - OpenAI 추출 요청
  - QA 검증
  - 상태 전이 기록

#### Database / Storage

- `PostgreSQL`
  - 검색 요청, 후보 논문, 선별 로그, PRISMA 집계, 추출 결과 저장
- `Redis`
  - 작업 큐, 캐시, 단기 상태 저장
- 파일 스토리지
  - 원문 PDF, 파싱 결과, export 파일 저장

#### External Integrations

- `KCI Open API / OAI-PMH`
- `RISS Linked Data / SPARQL / 합법적 검색 경로`
- `OpenAI Responses API`

### 3.3 권장 디렉터리 구조

```text
/
  frontend/
  backend/
    app/
      api/
      core/
      models/
      schemas/
      services/
      agents/
      workers/
      repositories/
    tests/
  docs/
```

## 4. 핵심 데이터 흐름

### 4.1 사용자 흐름

1. 사용자가 검색어와 선별 기준을 입력한다.
2. API가 `SearchRequest`를 생성하고 작업을 큐에 넣는다.
3. 수집 워커가 `KCI`와 `RISS`에서 후보를 수집한다.
4. 정규화 후 중복 제거를 수행한다.
5. 1차 선별로 제목/초록 기준 적합성을 판정한다.
6. 원문 확보 가능한 후보에 대해 원문 검토 단계로 넘긴다.
7. OpenAI 기반 추출로 메타분석 입력값을 구조화한다.
8. QA 단계에서 불확실성과 근거 문장을 정리한다.
9. 최종 결과와 PRISMA 집계를 대시보드에 표시한다.

### 4.2 상태 전이

각 후보 논문은 아래 상태를 가진다.

- `collected`
- `normalized`
- `deduplicated`
- `screened_title_abstract`
- `full_text_requested`
- `full_text_available`
- `screened_full_text`
- `extracted`
- `qa_reviewed`
- `exported`

이 상태 전이는 `PRISMA` 수치 집계와 연결되어야 한다.

## 5. 멀티에이전트 상세 설계

### 5.1 Search Planning Agent

입력:

- 검색어
- 연도 범위
- 학위논문 포함 여부
- 교육학 하위 분야
- 포함/제외 규칙

출력:

- `query_id`
- 소스별 검색 파라미터
- 확장 키워드 목록
- 수집 작업 명세

구현 포인트:

- 교육학 관련 동의어 사전 유지
- 사용자 입력을 KCI/RISS별 파라미터로 변환
- 검색 파라미터를 저장해 재현 가능하게 유지

### 5.2 Source Collection Agent

입력:

- 검색 작업 명세

출력:

- 공통 스키마의 `CandidateRecord[]`

구현 포인트:

- KCI 커넥터와 RISS 커넥터 분리
- 각 커넥터는 raw 응답과 normalized 응답을 모두 저장
- 소스별 오류와 제한을 독립적으로 로깅

### 5.3 Deduplication Agent

입력:

- 수집된 `CandidateRecord[]`

출력:

- `canonical_record`
- `duplicate_group`
- 병합 규칙 로그

구현 포인트:

- 1순위 DOI 일치
- 2순위 제목 정규화 + 연도 + 저자 비교
- 3순위 학위논문과 학술지 논문의 파생 관계 표시

### 5.4 Screening Agent

입력:

- 후보 논문 메타데이터
- 사용자 기준

출력:

- `EligibilityDecision`
- `reason_code`
- `reason_text`
- `confidence`

구현 포인트:

- 규칙 기반 필터와 LLM 판정을 혼합
- 명백한 비교육학, 질적연구, 비논문 자료는 규칙 기반 우선
- 애매한 케이스만 LLM 보조 판정

### 5.5 Full-text Review Agent

입력:

- 1차 선별 통과 후보
- PDF 또는 텍스트

출력:

- 원문 확보 상태
- 2차 적격성 결과
- 메타분석 가능성 판정

구현 포인트:

- PDF 텍스트 추출 실패 시 OCR 대체 경로 고려
- 원문 미확보는 `full_text_unavailable` reason code 기록

### 5.6 Extraction Agent

입력:

- 원문 텍스트
- 추출 스키마

출력:

- `ExtractionResult`
- `EvidenceSpan[]`
- `effect_size_inputs`

구현 포인트:

- `Responses API` + `Structured Outputs` 사용
- 1차 추출과 2차 검증 분리
- 필드별 근거 문장과 페이지 위치 저장

### 5.7 QA / Audit Agent

입력:

- 추출 결과
- 검증 결과

출력:

- `qa_status`
- `needs_human_review`
- `audit_report`

구현 포인트:

- 누락 필드 감지
- 값 충돌 감지
- confidence가 낮은 건 검토 큐에 이동

## 6. 데이터 모델 초안

### 6.1 SearchRequest

- `id`
- `query_text`
- `expanded_keywords`
- `year_from`
- `year_to`
- `include_theses`
- `include_journal_articles`
- `inclusion_rules`
- `exclusion_rules`
- `status`
- `created_at`

### 6.2 CandidateRecord

- `id`
- `search_request_id`
- `source`
- `source_record_id`
- `title`
- `authors`
- `year`
- `journal_or_school`
- `abstract`
- `keywords`
- `doi`
- `url`
- `document_type`
- `language`
- `raw_payload`

### 6.3 EligibilityDecision

- `id`
- `candidate_record_id`
- `stage`
- `decision`
- `reason_code`
- `reason_text`
- `confidence`
- `reviewed_by`
- `created_at`

### 6.4 FullTextArtifact

- `id`
- `candidate_record_id`
- `file_path`
- `source_url`
- `mime_type`
- `text_content`
- `text_extraction_status`

### 6.5 ExtractionResult

- `id`
- `candidate_record_id`
- `study_design`
- `participants_json`
- `intervention_or_predictor`
- `comparison`
- `outcomes_json`
- `statistics_json`
- `effect_size_inputs_json`
- `confidence`
- `model_name`
- `created_at`

### 6.6 PrismaCounts

- `id`
- `search_request_id`
- `identified_records`
- `duplicate_records_removed`
- `records_screened`
- `records_excluded`
- `reports_sought_for_retrieval`
- `reports_not_retrieved`
- `reports_assessed_for_eligibility`
- `reports_excluded_with_reasons_json`
- `studies_included_in_review`

## 7. API 설계 초안

### 7.1 검색 및 작업 관리

- `POST /search-requests`
- `GET /search-requests/{id}`
- `GET /search-requests/{id}/status`
- `POST /search-requests/{id}/run`

### 7.2 후보 논문 및 선별

- `GET /search-requests/{id}/candidates`
- `POST /candidates/{id}/decision`
- `POST /candidates/{id}/full-text`
- `GET /candidates/{id}/extraction`

### 7.3 PRISMA 및 export

- `GET /search-requests/{id}/prisma`
- `GET /search-requests/{id}/exports/candidates.csv`
- `GET /search-requests/{id}/exports/meta-analysis-ready.csv`
- `GET /search-requests/{id}/exports/audit-report`

## 8. PRISMA 구현 계획

### 8.1 구현 원칙

- PRISMA는 별도 계산기가 아니라 이벤트 기반 집계로 구현한다.
- 모든 논문 상태 변경 시 `prisma_event` 또는 동등한 로그를 남긴다.
- 제외 사유는 항상 reason code를 강제한다.

### 8.2 구현 항목

- 상태 전이 시 PRISMA 카운트 업데이트
- reason code별 집계
- flow diagram에 필요한 JSON 생성
- 대시보드용 시각화 데이터 API 제공

### 8.3 수용 기준

- 파이프라인 로그와 `prisma_counts` 값이 일치해야 한다.
- `reports excluded with reasons` 합계가 실제 제외 건수와 일치해야 한다.

## 9. OpenAI 통합 계획

### 9.1 모델 사용 전략

- 저비용 분류 모델: 제목/초록 선별 보조
- 고정밀 추출 모델: 원문 기반 구조화 데이터 추출

### 9.2 프롬프트 전략

- 시스템 프롬프트는 교육학 메타분석 컨텍스트를 명시
- 출력은 JSON Schema로 고정
- 근거 문장과 페이지 위치를 필수로 요구
- 불확실하면 추정하지 말고 `needs_human_review`로 표기

### 9.3 장애 대응

- 스키마 불일치 시 재시도
- 추출 실패 시 부분 결과 저장
- 토큰 초과 시 섹션 단위 분할 추출

## 10. 단계별 작업 계획

### Phase 0. 프로젝트 골격

- 저장소 구조 생성
- `frontend` / `backend` 기본 앱 생성
- 환경변수, 설정 파일, 로깅 체계 구성

산출물:

- 실행 가능한 기본 앱
- 환경설정 예시 파일

### Phase 1. 데이터 모델과 기본 API

- `PostgreSQL` 스키마 정의
- ORM 모델 작성
- 검색 요청/후보 조회 API 구현

산출물:

- DB 마이그레이션
- 기본 CRUD API

### Phase 2. KCI 수집기

- KCI 커넥터 구현
- raw/normalized 저장
- 검색 요청 기준 수집 작업 구현

산출물:

- KCI 메타데이터 수집 파이프라인

### Phase 3. RISS 보조 연동

- RISS Linked Data 기반 최소 커넥터 구현
- KCI 누락 보완용 후보 수집

산출물:

- 선택적 RISS 수집 기능

### Phase 4. 중복 제거와 PRISMA 로그

- 정규화 규칙 작성
- 중복 병합 구현
- PRISMA 이벤트/집계 로직 구현

산출물:

- `prisma_counts.json` 생성 가능 상태

### Phase 5. 1차 선별

- 규칙 기반 필터 구현
- LLM 보조 선별 구현
- 결정 로그 UI/API 제공

산출물:

- 제목/초록 기반 선별 기능

### Phase 6. 원문 업로드 및 추출

- PDF 업로드
- 텍스트 추출 파이프라인
- OpenAI Structured Outputs 기반 추출 구현

산출물:

- `meta_analysis_ready.csv` 생성 가능 상태

### Phase 7. QA 및 검토 UI

- 불확실성 표시
- 근거 문장 표시
- 사람 검토 플로우 추가

산출물:

- 검토 가능한 추출 결과 화면
- `audit_report.md`

### Phase 8. 운영 안정화

- 실패 재처리
- 성능 최적화
- 테스트 자동화
- GitHub 배포 파이프라인

산출물:

- CI/CD 초안
- 운영 체크리스트

## 11. 테스트 계획

### 11.1 단위 테스트

- 정규화 함수
- 중복 판정 함수
- reason code 매핑
- PRISMA 카운트 계산

### 11.2 통합 테스트

- 검색 요청부터 후보 수집까지
- 후보 수집부터 PRISMA 집계까지
- PDF 업로드부터 추출 결과 생성까지

### 11.3 평가 테스트

- 교육학 키워드 3개 이상으로 end-to-end 실행
- 사람 판정 대비 1차 선별 재현율 측정
- 추출값과 근거 문장 일치율 측정

## 12. 우선순위와 의사결정

### 12.1 가장 먼저 만들 것

1. `KCI 수집기`
2. `공통 메타데이터 스키마`
3. `PRISMA 집계 모델`
4. `중복 제거`
5. `기본 대시보드`

### 12.2 후속 고도화

- RISS 연동 확대
- OCR 기반 스캔 PDF 처리
- 효과크기 계산 보조 모듈
- 검색식 추천 고도화
- 공동 검토자 워크플로

## 13. 완료 기준

아래 조건을 만족하면 MVP 완료로 본다.

- 사용자가 웹에서 교육학 검색어를 입력할 수 있다.
- KCI에서 후보 논문을 수집해 목록을 볼 수 있다.
- 중복 제거와 1차 선별 결과를 저장할 수 있다.
- PRISMA flow diagram용 수치를 자동 생성할 수 있다.
- 사용자가 업로드한 원문에서 메타분석 입력값을 구조화 추출할 수 있다.
- 추출값마다 근거 문장과 검토 필요 여부를 확인할 수 있다.

## 14. 즉시 실행할 첫 작업

구현 시작 순서는 아래와 같이 고정한다.

1. 백엔드 골격 생성
2. DB 모델과 마이그레이션 설계
3. `SearchRequest`, `CandidateRecord`, `EligibilityDecision`, `PrismaCounts` 모델 구현
4. KCI 수집기 프로토타입 구현
5. PRISMA 이벤트 집계 로직 구현
6. 최소 UI에서 검색 실행과 후보 목록 확인

이 순서로 진행하면, 가장 중요한 `검색 가능성`, `데이터 구조`, `PRISMA 추적성`을 먼저 검증할 수 있다.

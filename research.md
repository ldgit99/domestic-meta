# 교육학 메타분석 지원 AI 에이전트 연구

## 1. 목표

본 문서는 사용자가 교육학 관련 검색어를 입력하면 `RISS`와 `KCI`에서 후보 논문을 수집하고, 메타분석 가능 여부를 선별한 뒤, 최종 포함 논문에서 메타분석용 데이터를 자동 추출하는 웹 기반 AI 에이전트의 구현 가능성과 설계 방향을 정리한다.

핵심 목표는 다음과 같다.

- 국내 교육학 논문을 대상으로 한 메타분석 준비 작업 자동화
- `PRISMA 2020` 기준에 맞는 문헌 검색 및 선별 로그 관리
- 메타분석 가능한 양적연구를 우선 식별
- OpenAI API를 이용한 원문 기반 구조화 데이터 추출
- 사람이 검토 가능한 감사 추적(audit trail) 확보

초기 버전의 범위는 교육학 분야의 양적연구이며, 질적연구와 완전 자동 메타분석 계산은 범위 밖으로 둔다.

## 2. 왜 이 시스템이 필요한가

교육학 메타분석은 일반적으로 다음 작업에 시간이 많이 소요된다.

- 검색식 설계와 데이터베이스별 수집
- 중복 제거
- 제목/초록 기반 1차 선별
- 원문 확보와 2차 적격성 평가
- 표본수, 평균, 표준편차, 상관계수, 회귀계수 등 효과크기 계산용 정보 추출
- 제외 사유 및 PRISMA 보고용 수치 정리

이 중 검색, 중복 제거, 선별 로그 관리, 원문 기반 수치 추출 보조는 자동화 효과가 크다. 다만 최종 포함 여부와 추출값 확정은 여전히 연구자 검토가 필요하므로, 본 시스템은 `완전 자동화`가 아니라 `사람 검토를 전제로 한 반자동화`를 목표로 한다.

## 3. 관련 기준과 연구 동향

### 3.1 PRISMA 2020

문헌 선별과 보고 프레임은 `PRISMA 2020`을 기본으로 삼는다. `PRISMA 2020`은 `PRISMA 2009`를 대체한 최신 보고 지침이며, 검색, 선별, 포함 논문 수, 제외 사유를 더 명확하게 기록하도록 요구한다.

중요한 이유는 다음과 같다.

- 국내 교육학 메타분석에서도 PRISMA 흐름도를 요구하거나 사실상 표준처럼 사용한다.
- 검색에서 포함까지의 수치가 투명하게 관리되어야 재현성이 높아진다.
- AI 시스템이 각 단계의 판단 근거와 제외 사유를 구조적으로 저장하기에 적합하다.

핵심 참고:

- PRISMA 2020 Statement: https://www.bmj.com/content/372/bmj.n71
- PRISMA 2020 Flow Diagram: https://www.prisma-statement.org/PRISMAStatement/FlowDiagram

### 3.2 자동화와 LLM 활용 동향

체계적 문헌고찰 및 메타분석 자동화 연구는 주로 다음 두 영역으로 발전하고 있다.

- 제목/초록 스크리닝 자동화 또는 반자동화
- 원문 기반 데이터 추출 자동화

자동 스크리닝은 검색 결과가 많은 경우 시간을 크게 줄일 수 있지만, 누락 위험 때문에 보통 `재현율 우선`으로 설계한다. 데이터 추출 자동화는 최근 LLM 도입으로 빠르게 발전하고 있으나, 여전히 사람 검증이 필수라는 점이 공통적이다.

참고:

- Cochrane Handbook, Chapter 5 Collecting Data: https://www.cochrane.org/ms/authors/handbooks-and-manuals/handbook/current/chapter-05
- Research Screener (semi-automated abstract screening): https://doi.org/10.1186/s13643-021-01635-3
- Collaborative large language models for automated data extraction in living systematic reviews: https://pubmed.ncbi.nlm.nih.gov/39836495/

이 연구 흐름을 교육학 국내논문 환경에 적용할 때는, 의학 분야처럼 RCT 중심이 아니라 `사전-사후`, `비교집단`, `상관`, `회귀`, `준실험` 연구가 많다는 점을 반영해야 한다.

## 4. 국내 데이터 소스 조사

### 4.1 KCI

`KCI`는 공식 데이터 제공 체계가 비교적 명확하다.

- Open API
- OAI-PMH
- 파일 데이터
- 데이터 신청

따라서 KCI는 시스템의 `1차 공식 수집 경로`로 적합하다. 교육학 논문 검색 시 제목, 저자, 학술지, 발행연도, 초록, 키워드, 식별자 등 메타데이터 수집의 중심 소스로 활용할 수 있다.

참고:

- KCI 데이터 제공 메인: https://www.kci.go.kr/kciportal/po/openapi/openReqDataList.kci
- KCI 파일데이터 안내: https://www.kci.go.kr/kciportal/po/openapi/openFileDataList.kci

### 4.2 RISS

`RISS`는 국내 학위논문과 학술논문 탐색에서 중요하지만, 대량 수집을 위한 공개 API 체계는 KCI보다 보수적이다. 다만 공식적으로 확인 가능한 접근 자원이 있다.

- RISS Linked Open Data
- SPARQL Endpoint
- RDF/JSON 형태의 시범 발행 데이터
- 신청형 데이터 접근 가능성

따라서 RISS는 `웹 페이지 직접 크롤링`보다 `공식 공개 데이터와 합법적 접근 경로 우선`으로 설계하는 것이 안전하다. 특히 교육학 메타분석에서는 학위논문 포함 여부가 결과에 큰 영향을 줄 수 있으므로, RISS는 `학위논문 보강 소스`로 가치가 크다.

참고:

- RISS Linked Data 예시: https://data.riss.kr/resource/Thesis/000012681655
- RISS Linked Data 서비스: https://data.riss.kr/ontoModel.do

### 4.3 수집 전략 결론

초기 제품에서는 다음 우선순위를 권장한다.

1. `KCI Open API / OAI-PMH`로 학술지 논문 메타데이터 수집
2. `RISS Linked Data / 합법적 검색 경로`로 학위논문 및 누락 레코드 보완
3. 원문은 공개 PDF, DOI 링크, 사용자가 업로드한 파일, 기관 접근 가능 링크 중심으로 확보
4. 비공식 대량 크롤링은 기본 경로에서 제외

## 5. 교육학 메타분석 가능 논문의 판정 기준

초기 시스템은 교육학 양적연구를 우선 처리한다. 메타분석 가능 여부는 `효과크기 계산에 필요한 최소 통계량 확보 가능성`을 중심으로 판단한다.

### 5.1 우선 포함 대상

- 실험연구, 준실험연구
- 사전-사후 비교 연구
- 비교집단 연구
- 상관연구
- 회귀분석을 포함한 양적연구
- 동일 개념을 측정한 반복 연구

### 5.2 핵심 추출 항목

- 표본수(`n`)
- 집단 구분
- 사전/사후 평균
- 표준편차
- t, F, chi-square
- p값
- 상관계수 `r`
- 회귀계수
- 신뢰구간 또는 표준오차
- 결과변수와 측정시점
- 중재/처치 또는 예측변인 정보

### 5.3 제외 또는 보류 조건

- 질적연구
- 이론적 논의만 있는 논문
- 통계량이 전혀 없거나 효과크기 환산이 불가능한 논문
- 원문 미확보
- 중복 게재 의심
- 하나의 연구가 여러 보고서로 분산되어 중복 포함 위험이 큰 경우

최종 판정 라벨은 아래 4단계로 두는 것이 적절하다.

- `include`
- `exclude`
- `maybe`
- `needs_human_review`

## 6. PRISMA 2020을 시스템에 반영하는 방식

### 6.1 기본 원칙

PRISMA flow diagram은 보고서용 그림이 아니라 `파이프라인 상태 모델`로 구현해야 한다. 즉, 검색부터 최종 포함까지 모든 단계가 이벤트와 수치로 저장되어야 한다.

최소 집계 항목은 다음과 같다.

- identified records
- duplicate records removed
- records screened
- records excluded
- reports sought for retrieval
- reports not retrieved
- reports assessed for eligibility
- reports excluded with reasons
- studies included in review

### 6.2 시스템 매핑

| PRISMA 단계 | 시스템 이벤트 | 저장 필드 예시 |
| --- | --- | --- |
| identified records | RISS/KCI에서 후보 수집 완료 | `source`, `query_id`, `record_id` |
| duplicate records removed | 중복 병합 완료 | `duplicate_group_id`, `canonical_record_id` |
| records screened | 제목/초록 1차 선별 수행 | `screening_stage=title_abstract` |
| records excluded | 1차 제외 | `decision=exclude`, `reason_code` |
| reports sought for retrieval | 원문 확보 시도 | `full_text_status=requested` |
| reports not retrieved | 원문 미확보 | `full_text_status=not_retrieved` |
| reports assessed for eligibility | 원문 기반 2차 검토 | `screening_stage=full_text` |
| reports excluded with reasons | 2차 제외 | `decision=exclude`, `reason_code`, `reason_text` |
| studies included in review | 최종 포함 | `decision=include`, `included_at` |

### 6.3 PRISMA reason code 권장안

- `not_education`
- `not_quantitative`
- `insufficient_statistics`
- `no_relevant_outcome`
- `wrong_population`
- `wrong_intervention_or_predictor`
- `wrong_comparison`
- `duplicate_publication`
- `full_text_unavailable`
- `conference_or_non_article`
- `outside_date_range`

### 6.4 PRISMA flow diagram 자동 생성을 위한 JSON 예시

```json
{
  "query_id": "edu-2026-001",
  "identified_records": 420,
  "duplicate_records_removed": 57,
  "records_screened": 363,
  "records_excluded": 241,
  "reports_sought_for_retrieval": 122,
  "reports_not_retrieved": 18,
  "reports_assessed_for_eligibility": 104,
  "reports_excluded_with_reasons": {
    "not_quantitative": 24,
    "insufficient_statistics": 31,
    "wrong_population": 9,
    "duplicate_publication": 6,
    "full_text_unavailable": 7
  },
  "studies_included_in_review": 27
}
```

이 구조를 이용하면 웹 대시보드에서 PRISMA flow diagram을 자동 생성할 수 있다.

## 7. 멀티에이전트 아키텍처 제안

### 7.1 전체 구조

시스템은 다음 에이전트로 분리하는 것이 적절하다.

1. `Search Planning Agent`
2. `Source Collection Agent`
3. `Deduplication Agent`
4. `Screening Agent`
5. `Full-text Review Agent`
6. `Extraction Agent`
7. `QA/Audit Agent`

### 7.2 에이전트별 역할

#### Search Planning Agent

- 사용자 검색어를 데이터베이스별 검색식으로 변환
- 동의어, 학문분야 필터, 연도 범위, 논문 유형 필터 생성
- PRISMA용 `query_id` 발급

#### Source Collection Agent

- KCI와 RISS에서 후보 논문 메타데이터 수집
- 수집 결과를 공통 스키마로 정규화
- 추후 중복 제거를 위해 DOI, 제목, 저자, 연도, 학술지, 학교명 저장

#### Deduplication Agent

- DOI 일치, 제목 유사도, 저자/연도 일치 규칙으로 중복 탐지
- 학술지 논문과 학위논문의 중복/파생 관계도 표시

#### Screening Agent

- 제목, 초록, 키워드 기반 1차 선별
- `include/exclude/maybe` 판정
- 제외 시 PRISMA reason code 부여

#### Full-text Review Agent

- 원문 확보 여부 확인
- 원문 기반 2차 적격성 평가
- 효과크기 환산 가능 여부 판정

#### Extraction Agent

- 최종 포함 또는 보류 논문에서 메타분석용 수치 추출
- 구조화된 JSON 생성
- 근거 문장과 표 번호 연결

#### QA/Audit Agent

- 추출값별 신뢰도 표시
- 불일치, 누락, 애매한 추출값을 사람 검토 큐로 이동
- 최종 `audit_report.md` 생성

### 7.3 권장 파이프라인

`Search Planning -> Source Collection -> Deduplication -> Screening -> Full-text Review -> Extraction -> QA/Audit -> Export`

이 구조는 각 단계 산출물을 독립적으로 저장할 수 있어, 실패 복구와 사람 검토에 유리하다.

## 8. OpenAI API 활용 설계

### 8.1 기본 권장

OpenAI 기반 구현은 `Responses API`를 중심으로 설계하는 것이 적절하다. 구조화 추출은 `Structured Outputs`를 사용해 JSON Schema 강제를 적용한다. 멀티에이전트 오케스트레이션은 `OpenAI Agents SDK`를 기본 후보로 둔다.

참고:

- Responses API: https://platform.openai.com/docs/api-reference/responses
- Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/

### 8.2 왜 Structured Outputs가 중요한가

논문 데이터 추출에서 가장 큰 실패 원인은 필드 누락, 형식 불일치, 임의 서술이다. `Structured Outputs`를 사용하면 아래 장점이 있다.

- 필수 필드 강제
- 타입 안정성 확보
- 후처리 단순화
- 검토 UI와 직접 연결 가능

### 8.3 추출 스키마 권장안

```json
{
  "study_design": "quasi_experimental",
  "participants": {
    "population": "중학생",
    "sample_size_total": 120,
    "groups": [
      {
        "name": "experimental",
        "n": 60
      },
      {
        "name": "control",
        "n": 60
      }
    ]
  },
  "intervention_or_predictor": "협동학습 기반 수업",
  "comparison": "전통 강의식 수업",
  "outcomes": [
    {
      "name": "학업성취도",
      "measure": "과학 성취도 검사",
      "timepoints": ["pretest", "posttest"]
    }
  ],
  "timepoints": ["pretest", "posttest"],
  "statistics": [
    {
      "outcome": "학업성취도",
      "group": "experimental",
      "timepoint": "posttest",
      "mean": 82.4,
      "sd": 10.1
    }
  ],
  "effect_size_inputs": {
    "effect_type_candidates": ["standardized_mean_difference"],
    "is_meta_analytic_ready": true
  },
  "evidence_spans": [
    {
      "field": "participants.sample_size_total",
      "evidence_text": "연구대상은 중학교 2학년 120명이었다.",
      "location": "p.5"
    }
  ],
  "confidence": "medium"
}
```

### 8.4 추출 워크플로

권장 흐름은 다음과 같다.

1. 원문 PDF 또는 텍스트 입력
2. 1차 구조화 추출
3. 2차 검증 프롬프트로 값 재검토
4. 불일치 필드 플래그 처리
5. 사람 검토 필요 항목 분리

이 방식은 `단일 응답을 그대로 신뢰하는 구조`보다 안전하다.

## 9. 시스템 인터페이스 설계

### 9.1 웹 대시보드 입력

- 검색어
- 동의어/확장 키워드
- 연도 범위
- 교육학 하위 분야
- 학술지/학위논문 포함 여부
- 포함/제외 기준
- 메타분석용 추출 항목 템플릿

### 9.2 결과 화면

각 후보 논문에 대해 다음 정보를 보여주는 것이 적절하다.

- 제목
- 저자
- 연도
- 소스(`RISS` 또는 `KCI`)
- 중복 여부
- 1차 선별 결과
- 2차 선별 결과
- 제외 사유
- 메타분석 가능 여부
- 추출 완료 여부
- 사람 검토 필요 여부

### 9.3 최종 산출물

- `candidate_studies.csv`
- `screening_log.json`
- `prisma_counts.json`
- `meta_analysis_ready.csv`
- `audit_report.md`

## 10. 권장 기술 스택

초기 구현 기준으로는 아래 조합이 현실적이다.

- 백엔드/에이전트 오케스트레이션: `Python`
- 웹 API: `FastAPI`
- 작업 큐: `Celery` 또는 `RQ`
- DB: `PostgreSQL`
- 검색 인덱스/캐시: 필요 시 `Redis`
- 프론트엔드: `React` 또는 `Next.js`
- 파일 저장: 로컬 스토리지 또는 객체 스토리지

이유는 다음과 같다.

- Python은 논문 파싱, 데이터 처리, 메타분석 보조 계산, AI 오케스트레이션에 강하다.
- 웹 대시보드는 프론트와 백엔드를 분리하는 편이 운영상 유리하다.
- 장시간 작업인 검색/추출 파이프라인은 비동기 큐가 필수다.

## 11. 저장 스키마 초안

내부 타입은 다음 정도로 정리하는 것이 적절하다.

- `SearchRequest`
- `CandidateRecord`
- `EligibilityDecision`
- `FullTextArtifact`
- `ExtractionResult`
- `EvidenceSpan`
- `PrismaCounts`
- `MetaAnalysisRecord`

`CandidateRecord`에는 최소한 다음 필드가 필요하다.

- `record_id`
- `source`
- `title`
- `authors`
- `year`
- `journal_or_school`
- `abstract`
- `keywords`
- `doi`
- `url`
- `document_type`

## 12. 검증 계획

### 12.1 검색 및 중복 제거

- 교육학 키워드 3개 이상으로 RISS/KCI 동시 검색
- 동일 논문이 다른 표기로 수집될 때 병합 정확도 측정
- 학술지 논문과 학위논문의 중복/파생 관계 탐지 검증

### 12.2 선별 성능

- 제목·초록 기준 1차 선별 결과와 사람 판정 비교
- 재현율 우선 평가
- PRISMA reason code 일관성 검증

### 12.3 추출 정확도

- 사전-사후 설계 논문
- 비교집단 논문
- 상관연구
- 회귀연구

각 유형에서 골드셋을 수작업으로 만들고, 추출 필드 정확도와 근거 문장 일치도를 검증해야 한다.

### 12.4 PRISMA 집계 검증

- 파이프라인 로그와 `prisma_counts.json` 일치 여부 확인
- 제외 사유 합계와 최종 포함 수 일관성 확인

## 13. 리스크와 대응

### 13.1 데이터 접근 제약

가장 큰 리스크는 국내 데이터 소스의 접근 정책이다. 대응 원칙은 다음과 같다.

- 공식 API와 공개 데이터 우선
- 신청형 데이터는 별도 운영 절차로 분리
- 비공식 대량 크롤링은 기본안 제외

### 13.2 원문 확보 문제

원문이 없으면 추출 정확도가 크게 떨어진다. 따라서 시스템은 다음 우선순위를 둬야 한다.

1. 공개 PDF 링크
2. DOI 기반 외부 링크
3. 사용자 업로드
4. 기관 인증 환경에서 확보 가능한 파일

### 13.3 LLM 추출 오류

자동 추출은 잘못된 숫자를 그럴듯하게 만들 위험이 있다. 따라서 다음이 필요하다.

- 구조화 출력 강제
- 근거 문장 저장
- 2차 검증 프롬프트
- 사람 검토 큐

## 14. MVP 제안

초기 MVP는 아래 범위로 제한하는 것이 현실적이다.

- 교육학 키워드 입력
- KCI 중심 메타데이터 수집
- RISS는 보조 소스로 제한적 연동
- 제목/초록 1차 선별
- PRISMA 수치 자동 집계
- 사용자가 업로드한 PDF에서 메타분석용 수치 추출

즉, `검색부터 추출까지 전부 자동`보다 `선별 로그 + 추출 보조 + 검토 UI`를 우선 구현하는 편이 성공 가능성이 높다.

## 15. 구현 권고안

구현 우선순위는 다음이 적절하다.

1. `KCI 수집 + 공통 메타데이터 스키마`
2. `PRISMA 로그 모델 + 중복 제거`
3. `제목/초록 기반 1차 선별`
4. `PDF 업로드 기반 추출`
5. `RISS 보강 연동`
6. `원문 확보 자동화 고도화`

이 순서가 좋은 이유는, 검색과 선별 로그가 먼저 안정되어야 이후 추출 결과를 연구자가 신뢰할 수 있기 때문이다.

## 16. 결론

교육학 메타분석 지원 AI 에이전트는 기술적으로 충분히 구현 가능하다. 다만 성공 조건은 `대량 크롤링`이나 `완전 자동 판정`이 아니라, 아래 세 가지를 안정적으로 만족하는 것이다.

- 공식 데이터 접근 경로를 우선 사용하는 수집 구조
- `PRISMA 2020` 기준으로 추적 가능한 문헌 선별 로그
- OpenAI 기반 구조화 추출과 사람 검토가 결합된 반자동 워크플로

따라서 본 프로젝트는 `교육학 메타분석 실무를 위한 검색-선별-추출 운영체계`로 정의하는 것이 적절하다. 제품의 핵심 가치는 검색 결과를 많이 가져오는 것보다, `포함/제외 판단 근거와 메타분석 입력값을 재검토 가능하게 만드는 것`에 있다.

## 17. 참고 링크

- PRISMA 2020 Statement: https://www.bmj.com/content/372/bmj.n71
- PRISMA Flow Diagram: https://www.prisma-statement.org/PRISMAStatement/FlowDiagram
- Cochrane Handbook Chapter 5: https://www.cochrane.org/ms/authors/handbooks-and-manuals/handbook/current/chapter-05
- KCI 데이터 제공: https://www.kci.go.kr/kciportal/po/openapi/openReqDataList.kci
- KCI 파일데이터: https://www.kci.go.kr/kciportal/po/openapi/openFileDataList.kci
- RISS Linked Data 예시: https://data.riss.kr/resource/Thesis/000012681655
- RISS Linked Data 서비스: https://data.riss.kr/ontoModel.do
- OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
- Research Screener paper: https://doi.org/10.1186/s13643-021-01635-3
- LLM data extraction paper (PubMed): https://pubmed.ncbi.nlm.nih.gov/39836495/

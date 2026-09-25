# RISS 기반 교육 메타분석 자동화 — 구현 리서치

작성일: 2026-09-25

## 0. 핵심 결론 (요약)

1. **RISS 이용약관이 자동 수집을 제한한다.** 사전 허락 없이 매크로·봇·스크립트·스크래퍼로 "통상적 이용 범위를 벗어난 대량·반복 요청·다운로드"를 하는 것을 금지하고, 허용 경로로 오픈API, 공개적으로 허용한 자동수집 방법, 별도 계약을 든다 [웹, 약관 스니펫 기준: https://www.riss.kr/etc/clause.html]. 이에 따라 수집 경로를 세 가지로 나눈다.
   - **기본 모드 — 내보내기 파일 가져오기.** 대시보드가 검색어별 RISS 검색 URL을 만들어 준다. 사용자가 RISS에서 직접 "내보내기"(Excel/RIS/BibTeX 등)한 파일을 올리면, Python이 검색어별로 병합한다.
   - **보강 모드 — KCI 공식 경로.** 국내학술논문의 초록·키워드·DOI를 KCI 공식 경로(OAI-PMH는 키 불필요, REST는 개인 키)로 채운다.
   - **옵션 모드 — 저속 자동 수집.** 사용자가 명시적으로 켰을 때만 동작한다. 요청 간격은 10초 이상, robots.txt 준수, 로그인 미사용으로 제한한다. 쓰기 전에 KERIS(1599-3122)에 문의하기를 권한다.
2. **RISS 검색결과 HTML 구조는 캡처로 파악돼 있다.** `Search.do`는 로그인 없이 한 페이지에 100건까지 반환한다. 카드마다 제어번호, 제목, 저자, 소속, 연도, 학위구분, 학술지·권호, KCI 등재 여부, 원문 유형, 일부 초록이 있다 [캡처]. 옵션 모드의 파서와, 내보내기 파일 검증용 정답셋에 이 구조를 쓴다.
3. **RISS 검색 OpenAPI**(`www.riss.kr/openApi`)는 비영리 기관·대학에만 키를 발급하는 것으로 알려져 있다 [웹]. 소속 대학이 키를 받았다면 이것이 가장 좋은 공식 자동 경로다. 이 경로는 선택 기능으로 둔다.
4. **Linked Data/SPARQL(data.riss.kr)은 부적합**하다. 커버리지가 좁고(교육 검색어 기준 약 1/6), 초록이 부족하며, 웹 제어번호와 ID 체계가 다르다. [캡처]
5. **스크리닝과 수치 추출은 외부 LLM API 없이 이 Claude Code 세션 안에서 수행**한다. 수집기가 만든 파일(JSONL/CSV)을 세션이 배치 단위로 읽는다. 판정과 근거는 파일로 기록하고 모든 결정은 사람이 검토할 수 있게 남긴다.
6. 문헌상 LLM 제목·초록 스크리닝은 **민감도는 높지만 실행마다 판정이 흔들린다**. 따라서 "자동 제외" 대신 **독립 2회 판정 + 하나라도 포함이면 포함 + 제외 건 표본 감사**로 설계한다. 한국어 초록은 **번역하지 않고 원문 그대로** 판정한다(번역 후 판정 시 민감도가 크게 떨어진다는 보고가 있다).
7. 수치 추출은 **누락과 SD/SE 혼동이 주 오류**다. 페이지·표 번호·원문 인용을 필수로 남기고, M/SD/n으로 t·p를 재계산해 보고값과 대조하는 **자동 일관성 검사**를 붙인다.
8. **이 클라우드 세션은 현재 네트워크 정책상 `www.riss.kr`, `kci.go.kr` 접속이 차단**되어 있다(프록시 403). 해결 방법은 세 가지다.
   - 내보내기 파일을 저장소에 올린다. 기본 모드는 네트워크가 필요 없다.
   - 환경 설정의 허용 도메인에 해당 호스트를 추가한다.
   - 수집 스크립트를 사용자 PC에서 실행한다.

근거 표기: **[캡처]** 이전 프로토타입이 저장한 실제 riss.kr 페이지(git 커밋 `7097837`의 `tmp_www_riss_*`)에서 직접 확인한 내용. **[웹]** 웹 검색으로 확인한 내용(URL 병기). **[추정]** 근거가 간접적이라 실사용 전에 검증해야 하는 내용.

---

## 1. 목표와 운영 전제

### 1.1 목표 워크플로

```
[대시보드] 검색어 목록 입력 (예: "협동학습 학업성취", "협력학습 성취도", ...)
   │
   ▼
   │  대시보드가 검색어 × 컬렉션(학위논문, 국내학술논문)별 RISS 검색 URL 생성
   ▼
[서지 확보] 검색어별로 다음 중 하나
   │   (기본) 사용자가 RISS에서 내보낸 Excel/RIS/BibTeX 파일 업로드
   │   (옵션) 저속 자동 수집(10초+ 간격) 또는 기관 OpenAPI 키
   │     → data/raw/<검색어>/<컬렉션>_<날짜>.<형식>  (원본 그대로 보존)
   ▼
[Python 정규화] 형식별 파서 → 공통 스키마 JSONL (검색어, 가져온 시각 포함)
   ▼
[Python 보강] 국내학술논문은 KCI(OAI-PMH/REST)로 초록·키워드·DOI 보강
   ▼
[Python 병합] 검색어별 결과 합치기 → 제어번호로 1차 병합 → 제목·저자·연도로 2차 중복 판정
   │     → data/merged/records.csv, data/merged/duplicates.csv
   ▼
[Claude Code 세션] 제목·초록 스크리닝 (API 미사용, 세션 내 판정)
   │     → screening/decisions.jsonl (포함/제외/보류, 사유 코드, 근거 문장)
   ▼
[원문 확보] 포함 후보 PDF 수집(수동/반자동) → fulltext/<id>.pdf
   ▼
[Claude Code 세션] 원문 적격성 판정 + 메타분석 수치 추출
   │     → extraction/<id>.json (값 + 페이지 + 표 번호 + 원문 인용)
   ▼
[Python 검증·계산] 일관성 검사, 효과크기 계산, PRISMA 수치 집계
         → exports/effect_sizes.csv (metafor 입력용), exports/prisma.json
```

### 1.2 역할 분담 원칙

| 단계 | 담당 | 이유 |
|---|---|---|
| 서지 파일 확보(기본 모드) | 연구자 | RISS 약관상 가장 안전한 경로 |
| 파싱·정규화·보강·병합·중복 1차 판정 | Python 코드 | 결정적이어야 하고, 재실행 가능해야 한다 |
| 제목·초록 스크리닝 | Claude Code 세션 | 사용자 요구: API 비용 없이 세션에서 판단 |
| 원문 적격성·수치 추출 | Claude Code 세션 | PDF를 직접 읽을 수 있다(`Read` 도구, 20페이지/회) |
| 효과크기 계산·검증 | Python 코드 | 공식은 코드로 고정해야 재현 가능하다(LLM 계산 금지) |
| 최종 판정 확정 | 연구자 | Cochrane/Campbell 등 공동 입장문(RAISE): 최종 책임과 감독은 사람에게 있다 |

### 1.3 "API 미사용, 세션 내 분석"의 의미와 한계

- 스크리닝·추출은 Claude Code가 저장소의 파일을 읽고 판정 결과를 파일로 쓰는 방식이다. 수집기 코드는 LLM을 호출하지 않는다.
- 수천 건을 한 대화 맥락에 넣으면 맥락이 포화된다. 따라서 **배치(예: 50~100건) 단위로 서브에이전트에 분배**하고, 메인 세션은 결과 파일만 취합한다.
- 이중 판정의 독립성을 확보하려면 두 판정자가 서로의 결과를 보지 않아야 한다. 두 서브에이전트에 **서로 다른 모델**(예: Opus 계열 1회, Sonnet 계열 1회)을 지정하면 문헌이 권고하는 "모델 다양성"도 일부 확보된다.
- 비용 대신 Claude Code **사용량 한도**가 제약이 된다. 레코드 1건(제목+초록)은 대략 300~800 토큰이다. 2,000건 × 2회 판정이면 수백만 토큰 규모이므로, 검색어 설계 단계에서 결과 수를 관리해야 한다(3.8절).
- 판정의 재현성을 위해 매 배치마다 `criteria.md`(포함·제외 기준) 버전, 모델명, 날짜를 결정 레코드에 같이 기록한다(PRISMA 2020 Item 8/9 보고 요구).

---

## 2. 데이터 소스 접근 경로 비교

| 경로 | 상태 | 장점 | 단점 | 판단 |
|---|---|---|---|---|
| **A. 사용자 "내보내기" 파일** (Excel/RIS/BibTeX/EndNote/RefWorks/Tab) | 기능 존재 [캡처 + 웹], 컬럼·건수 미검증 | 공식 UI 기능, 약관 위험 최소, 네트워크 불필요 | 한 번에 한 페이지분(최대 100건) 선택, 수작업 반복 | **기본 경로** |
| **B. KCI OAI-PMH / REST** | 공식 제공 [웹] | 국내학술논문 초록(국/영)·DOI·키워드, OAI는 키 불필요 | 학위논문 없음, REST 키는 개인 신청 | **보강 경로** |
| **C. RISS 검색 OpenAPI** (`www.riss.kr/openApi`) | 기관·대학 한정 발급으로 알려짐 [웹] | 공식 자동 경로, 100건/요청 | 개인 발급 불가, 초록 필드 없을 가능성 | 기관 키가 있으면 **최우선 자동 경로** |
| **D. 웹 검색결과 HTML** (`/search/Search.do`) | 로그인 불필요, 동작 확인 [캡처] | 웹 검색과 동일한 결과·건수, 초록 일부 포함 | **약관상 자동화 제한**, 마크업 변경에 취약 | 옵션 모드(저속, 사용자 명시 동의) |
| **E. 초록 AJAX** (`/search/detail/AbstractSelectAjax.do`) | 엔드포인트 존재 [캡처], 응답 형식 미검증 | 초록 보강 | D와 같은 약관 문제, 건별 요청 | 옵션 모드에서 스크리닝 후보에만 |
| **F. Linked Data / SPARQL** (`data.riss.kr/sparql`) | 동작했으나 데이터 부실 [캡처] | 공식 개방 데이터 | 교육 검색어 80,918건 vs 웹 513,387건, 초록·학술논문 부족, ID 체계 불일치 | 사용 안 함 |
| **G. 국회도서관 Open API** | 개인 즉시 발급으로 알려짐 [웹] | 학위논문 서지 | RISS와 식별자 다름 | 학위논문 누락 점검용 선택지 |

---

## 3. RISS 수집 상세 (Python)

3.1~3.5절은 RISS 검색결과 페이지 구조다. 이 구조는 세 곳에 쓰인다.
- 대시보드가 검색어별 검색 URL을 만들 때
- 옵션 모드(저속 자동 수집)의 파서
- 내보내기 파일 검증용 정답셋

기본 모드의 입력은 3.6절 내보내기 파일이다.

### 3.1 검색 엔드포인트와 파라미터 [캡처]

- 엔드포인트: `GET https://www.riss.kr/search/Search.do`
- 이전 프로토타입에서 실제로 동작한 파라미터 조합:

```
isDetailSearch=N&searchGubun=true&viewYn=OP&query=<검색어>&queryText=&iStartCount=0
&iGroupView=5&icate=all&colName=bib_t&exQuery=&exQueryText=&order=/DESC&onHanja=false
&strSort=RANK&pageScale=100&orderBy=&fsearchMethod=search&isFDetailSearch=N&sflag=1
&searchQuery=<검색어>&resultKeyword=<검색어>&pageNumber=1
```

| 파라미터 | 의미 | 비고 |
|---|---|---|
| `query` | 검색어 | `searchQuery`, `resultKeyword`에도 같은 값 |
| `colName` | 컬렉션 | 3.2절 표 |
| `iStartCount` | **페이지 오프셋**(0, 100, 200, …) | 페이징은 이것으로 한다 |
| `pageNumber` | 페이지 번호 | **단독으로는 무시됨**: p2 캡처가 p1과 제어번호 동일 [캡처 검증] |
| `pageScale` | 페이지 크기 | 10/20/30/50/100, 100 동작 확인 [캡처 검증: 100카드] |
| `strSort` | 정렬 | `RANK`(정확도), `DATE`, `VIEWCOUNT`, `TITLE`, `AUTHOR`, `PUBLISHER` |
| `order` | 정렬 방향 | `/DESC`, `/ASC` |
| `p_year1`, `p_year2` | 연도 범위 | 폼 hidden 필드 존재, 실동작 미검증 [추정] |
| `queryText` | 필드 지정 상세검색 | `znTitle,<값>`, `znCreator,`, `znSubject,`(주제어), `znAbstract,`, `znPublisher,`, `znAll`, `znKtoc`(목차). 여러 조건은 `@`로 연결하고 AND/OR/NOT 연산자 요소를 끼운다 [연산자 요소 문법은 추정] |

**전체 건수 위치** [캡처]
- 단일 컬렉션 페이지: `<span class="num">513,387</span>`(검색결과 N 건)
- 통합(`all`) 페이지: `<h3>학위논문<span class="moreCnt">…</span></h3>`

**수집 순서 권장:** `strSort=DATE`로 고정하면 수집 도중 순위가 흔들려도 누락과 중복이 줄어든다. 페이지 경계 누락은 제어번호 집합으로 검증한다.

### 3.2 컬렉션(`colName`) [캡처]

| colName | 의미 | 교육 메타분석 사용 | "교육" 검색 건수(캡처 시점) |
|---|---|---|---|
| `bib_t` | 학위논문 | **필수** | 513,387 |
| `re_a_kor` | 국내학술논문 | **필수** | 559,822 |
| `re_a_over` | 해외학술논문 | 선택 | 23,631 |
| `re_t` | 연구보고서 | 회색문헌 보강 시 | 59,295 |
| `re_s` | 학술지(저널 단위) | 사용 안 함 | 3,806 |
| `bib_m` | 단행본 | 사용 안 함 | 490,802 |
| `all` | 통합 | **사용 금지**: 통합 페이지 카드에는 `p_control_no`가 없다 | 1,653,067 |

학위논문 패싯 [캡처]: `c_use_mat_subtype_cd`(T1 국내석사, T2 국내박사), `c_use_fulltext_kind`(1 원문 있음), `c_use_l_sub_code`(80 = 교육), `c_use_pyear`(연도), `c_use_univ_cd`(대학). 이 패싯을 URL 파라미터로 바꾸는 규칙은 캡처되지 않은 `searchLeft.js`에 있다. 실측으로 확인해야 한다 [추정].

### 3.3 결과 카드 구조와 추출 필드 [캡처]

목록 컨테이너는 `div.srchResultListW > ul > li`이고, 카드 한 장은 다음과 같다.

```html
<input name="p_control_no" value="89930b52…d419|be54d9b8bc7cdb09" type="checkbox"/>   ← 제어번호|자료유형
<input type="checkbox" class="chkBoxType1" name="control_no" value="89930b52…_be54d9…">
<p class="title"><a href="/search/detail/DetailView.do?p_mat_type=…&control_no=…">제목</a></p>
<p class="etc">
  <span class="writer"><a>저자1</a>, <a>저자2</a></span>
  <span class="assigned"><a>동아대학교</a></span>      ← 학위: 대학 / 학술: 학회(발행처)
  <span>2015</span>                                  ← 연도
  <span>국내석사</span>                               ← 학위: 학위구분 / 학술: 학술지명 링크, 권호 링크
</p>
<div class="markW"><span class="mark"><img alt="KCI등재"></span></div>
<li class="viewOrigin"> … originViewType1/2/3 (무료/기관 내 무료/유료)
<p class="preAbstract">초록 …</p>                      ← 100건 중 39건에만 존재 [캡처 검증]
```

**정규 스키마(수집 원본 레코드)**

```json
{
  "source": "riss",
  "collection": "bib_t",
  "control_no": "89930b52...d419",
  "mat_type": "be54d9b8bc7cdb09",
  "detail_url": "https://www.riss.kr/search/detail/DetailView.do?p_mat_type=...&control_no=...",
  "title": "...",
  "authors": ["공태수"],
  "affiliation": "동아대학교",
  "year": 2015,
  "degree": "국내석사",
  "journal": null,
  "volume_issue": null,
  "kci_status": null,
  "fulltext_access": "free|institution|paid|none",
  "abstract": "...|null",
  "query": "협동학습 학업성취",
  "rank": 27,
  "retrieved_at": "2026-09-25T10:00:00+09:00",
  "raw_html_sha1": "..."
}
```

### 3.4 이전 파서의 교훈 [캡처: 이전 `connectors.py` 분석]

| 문제 | 증상 | 대책 |
|---|---|---|
| 정규식 파싱 | 중첩 `<span class='highlight'>` 때문에 값이 잘림("문화예술교육연구" → "문화예술교육") | `selectolax` 또는 `BeautifulSoup`로 DOM 파싱하고 `get_text()` 사용 |
| 다중 저자 | 쉼표로 이은 하나의 문자열 | `span.writer a` 목록으로 추출 |
| 키워드 | 검색어로 채워 넣음(오류) | 목록엔 키워드가 없다. 상세 페이지에서 수집하거나 비워 둔다 |
| 학술지명·권호 | 위치 기반 추출 | 링크 `href`의 `p_mat_type`/`v_control_no`로 구분 |
| 요청 제어 | 지연·재시도 없음 | 요청 간 10초 이상, 차단 응답 시 중단, 동일 요청 캐시(3.9절) |
| 검증 | 없음 | 페이지 카드 수 = min(pageScale, 잔여건수) 확인, 제어번호 중복·누락 검사, 원본 HTML 보관 |

### 3.5 초록·상세 정보 보강 [캡처, 응답 형식은 추정]

- 목록 초록은 약 39%에만 있다. 스크리닝의 질은 초록에 좌우되므로, **초록이 없는 레코드만** 보강한다.
- `POST /search/detail/AbstractSelectAjax.do` `{control_no, p_mat_type}` → 초록
- `GET /search/detail/DetailView.do?p_mat_type=…&control_no=…` → 주제어, 지도교수, 전공, 페이지 수 등(상세 페이지는 캡처가 없어 필드 미확인)
- 순서: 1차 제목 스크리닝으로 명백한 제외를 먼저 걸러낸다. 이후 남은 레코드만 초록을 보강하면 요청 수가 크게 준다. 이 경우 PRISMA에는 "제목 단계 제외"와 "초록 단계 제외"를 나눠 기록한다.

### 3.6 내보내기 파일 — 기본 입력 경로 [캡처 + 웹]

**확인된 사실**
- 목록 상하단에 `전체선택` 체크박스와 `exportData()`를 호출하는 "내보내기" 버튼이 있다. 선택 대상은 현재 페이지에 렌더링된 카드이므로 **한 번에 최대 100건**이다(`pageScale=100`으로 두고 전체선택) [캡처].
- 형식은 EndNote, RefWorks, RIS, BibTeX, Excel, Tab-delimited를 지원한다 [웹: https://www.welfare24.net/ab-3435-44].
- 레코드 단위 내보내기 페이지 `https://www.riss.kr/Export.do?control_no=…&p_mat_type=…&loginFlag=1`가 검색엔진에 노출되어 있다. `loginFlag`로 보아 로그인 확인이 있을 수 있다 [웹 스니펫, 미검증].
- 도서관 프록시로 접속하면 RefWorks 내보내기가 비활성화된다는 도서관 안내가 있다 [웹: https://kmu-kr.libguides.com/c.php?g=962502&p=7089558].

**확인하지 못한 사항 — 첫 실사용 때 반드시 확인**
1. Excel 컬럼 구성, 초록 포함 여부
2. 1회 최대 건수(여러 페이지 선택 누적 가능 여부)
3. 로그인 필요 여부
4. RIS 태그 매핑: RISS 제어번호가 `ID`/`UR`/`AN` 중 어디에 들어가는지

**사용자 작업량 추정**
- 검색어 1개 × 컬렉션 2개 × 결과 800건이면 페이지 8개 × 2 = **내보내기 16회**다.
- 검색어가 6개면 약 100회다. 부담이 크므로 다음 두 가지를 제공한다.
  - 검색어별 **건수 미리보기**: 대시보드가 사용자에게 검색 결과 첫 페이지를 열게 하고 건수를 입력받거나, 옵션 모드로 1페이지만 조회한다.
  - 여러 검색어를 OR로 합친 검색식을 **한 번에** 내보내는 방법 안내: `queryText`의 OR 연산은 검증이 필요하다. 이 방식을 쓰면 검색어별 출처 추적은 PRISMA 보고용으로 따로 남긴다.

**설계**
- `importers/riss_export.py`에 형식별 파서(RIS, BibTeX, Excel, Tab)를 두고 공통 스키마(3.3절)로 변환한다.
- 파일 이름 규칙: `data/raw/<검색어>/<컬렉션>_p<페이지>_<YYYYMMDD>.<ext>`. 이 규칙으로 검색어 출처가 레코드에 기록된다.
- 제어번호가 파일에 없으면 제목 + 저자 + 연도 해시를 임시 키로 쓴다.

### 3.7 SPARQL / Linked Data [캡처]

- 엔드포인트: `https://data.riss.kr/sparql?query=…&type=Json`
- 학위논문 속성: `dc:title`, `dcterms:abstract`, `bibo:degree`, `keris:degreeOrgnization`, `keris:degreeMajor`, `keris:degreeYear`, `dc:subject` 등
- 문제
  - 동일 검색어 결과가 웹의 약 1/6이다(80,918 vs 513,387).
  - 캡처된 JSON 응답이 문법적으로 깨져 있다(바인딩 사이 쉼표 누락).
  - ID(`000000002155`)가 웹 제어번호(hex)와 달라 병합이 어렵다.
- 결론: 사용하지 않는다.

### 3.8 검색어 설계와 수집량 관리

- "교육"처럼 넓은 검색어는 학위논문만 51만 건이다. 메타분석 검색어는 **개념 조합**(중재 × 결과)으로 좁힌다.
  - 예: `협동학습`, `협력학습`, `모둠학습` × `학업성취`, `성취도`, `학업성적`
- 대시보드에서 검색어를 **목록**으로 받고, 각 검색어를 독립 실행한다. 검색어별 건수를 먼저 조회(1페이지만 요청)하여 사용자에게 보여준 뒤 전량 수집을 확정한다.
  - 페이지 수 = Σ ceil(건수/100) × 컬렉션 수. 예: 검색어 6개 × 평균 800건 × 2컬렉션 ≈ 96페이지.
  - 기본 모드에서는 내보내기 96회다. 옵션 모드에서는 10초 간격 기준 약 16분이다.
- 필드 한정 검색(`znTitle`, `znAbstract`, `znSubject`)은 결과를 크게 줄이지만 누락 위험이 있다. 기본값은 전체 필드, 옵션으로 제공한다.
- 검색어별 원본은 절대 덮어쓰지 않고 `retrieved_at`별로 보존한다. PRISMA-S는 데이터베이스별 검색식, 검색일, 건수 보고를 요구한다.

### 3.9 Python 수집기 구성 권장

| 구성 | 권장 | 이유 |
|---|---|---|
| 내보내기 파일 파싱 | `rispy`(RIS), `bibtexparser`(BibTeX), `pandas` + `openpyxl`(Excel/Tab) | 기본 모드 입력 |
| HTTP(KCI 보강, 옵션 모드) | `httpx`(동기) + `tenacity` 재시도 | 단순, 타임아웃·재시도 명시 |
| 파싱 | `selectolax` 또는 `beautifulsoup4`(+`lxml`) | 정규식 대신 DOM 파싱 |
| 저장 | JSONL(원본), `pandas` → CSV/Parquet(병합본) | 원본 보존 + 분석 편의 |
| 캐시 | 요청 URL 해시별 HTML 파일 캐시 | 재실행 시 재요청 방지, 파서 수정 후 재파싱 가능 |
| 중복 판정 | `rapidfuzz`(Jaro-Winkler, token_set_ratio) | 빠르고 한글 문자열에도 사용 가능 |
| 테스트 | 캡처 HTML fixture로 파서 단위 테스트 | 사이트 변경을 CI에서 탐지 |

**옵션 모드 요청 규칙(강제):**
- 동시 요청 1개, 요청 간 **10초 이상**
- robots.txt를 파싱해 `/search/Search.do` 허용 여부를 확인하고, 불허 시 중단
- User-Agent에 도구명과 연락처 명시
- 로그인 세션·쿠키 미사용, CAPTCHA·차단 응답 시 즉시 중단(우회 금지)
- HTML 캐시 우선, 검색어당 상한 건수 설정

참고로 2026년 공개 프로젝트 중 robots.txt를 검사하고 최소 10초 간격을 강제하는 사례가 있다 [웹: https://github.com/mwobareullae/jungle_namanmoo].

### 3.10 이용약관과 법적 검토

> 이 절은 법률 자문이 아니다. 약관 원문은 이 환경에서 직접 열지 못했고, 검색 스니펫과 판례 기사로 정리했다. 시행일과 정확한 문구는 https://www.riss.kr/etc/clause.html 에서 확인해야 한다.

**RISS 이용약관(스니펫 기준)**
- 교육정보원의 사전 허락 없이 매크로·봇·스크립트·스크래퍼 등 자동화 수단으로 다음을 하는 것을 금지한다.
  - 로그인 후 제한된 정보 수집
  - IP 변경, CAPTCHA 등 접근 통제·이용량 제한 우회
  - **통상적 이용 범위를 벗어난 대량·반복 요청·다운로드**
  - 취약점 스캔
- 허용 경로로 오픈API, 공개적으로 허용한 자동수집 방법, 별도 계약을 든다.
- 위반 시 접속 차단, 세션 종료, API 키 제한이 가능하다. 복제·출판·제3자 제공도 금지한다.

**관련 법리**
- **저작권법 제93조(데이터베이스제작자 권리)**: DB의 "상당한 부분" 복제는 침해다. 개별 소재라도 반복적·체계적 복제로 통상적 이용과 충돌하면 침해가 될 수 있다.
  - 잡코리아 v. 사람인: 크롤링 정보를 영업에 사용해 DB권 침해 인정 [웹: https://lawtimes.co.kr/news/121766]
- **대법원 2022. 5. 12. 선고 2021도1533(야놀자 v. 여기어때)**: 정보통신망 침입·업무방해·DB권 침해 모두 무죄.
  - 공개 서버에 보호조치가 없었다는 점이 무죄 이유였다.
  - 반복적·체계적 복제는 "상당한 부분 복제와 같은 결과"가 있어야 침해로 본다고 했다 [웹: https://www.law.go.kr/precInfoP.do?precSeq=221765].
  - 다만 접근권한 제한 여부는 보호조치와 **이용약관** 등을 종합해 판단한다. RISS처럼 약관에 자동화 금지가 명시된 경우 이 판결보다 수집자에게 불리할 수 있다.
- **부정경쟁방지법** (카)목 데이터 부정사용(2022-04-20 시행)은 "특정인에게 제공되는" 한정 데이터가 대상이다. 공개 서지 정보와는 거리가 있다 [웹: https://www.kimchang.com/ko/insights/detail.kc?sch_section=4&idx=24264].

**이 도구에 대한 결론**

| 행위 | 위험 | 설계 |
|---|---|---|
| 사용자가 RISS에서 직접 내보낸 파일 가공 | 낮음 | **기본 모드** |
| KCI OAI-PMH/REST, 기관 RISS OpenAPI | 낮음(공식 경로) | 보강·선택 |
| 사용자 1인이 자기 연구 목적으로 저속 자동 조회 | 불확실: 약관의 "사전 허락 없는 스크립트" 조항에 걸릴 수 있다 | 옵션 모드. 기본 꺼짐, 사용자 명시 동의, 10초+ 간격. KERIS 사전 문의 권장 |
| 전수 크롤링, 원문 PDF 일괄 자동 다운로드, 수집 DB 공유·재배포 | 높음 | **구현하지 않음** |

### 3.11 KCI 보강 경로 [웹]

RISS의 국내학술논문 상당수는 KCI 등재(후보)지다. KCI 공식 경로로 초록·키워드·DOI를 채우면 스크리닝 품질이 오르고 RISS 자동 요청이 줄어든다.

| 경로 | 엔드포인트 | 인증 | 주요 내용 |
|---|---|---|---|
| OAI-PMH | `https://open.kci.go.kr/oai/request` (`set=ARTI`, `metadataPrefix=oai_kci` 또는 `oai_dc`) | 키 불필요 | 초록(description) 포함, 날짜 범위 하베스팅 |
| REST | `https://open.kci.go.kr/po/openapi/openApiSearch.kci?apiCode=articleSearch&key=…&title=…` | 개인 키(로그인 후 신청) | `title`/`keyword`/`abstract`/`author`/`journal`/`dateFrom`/`dateTo`, `displayCount` 최대 100, 국·영문 초록, DOI. 키워드는 `articleDetail`로 별도 조회 |

**매칭 방식**
- RISS 레코드에 DOI가 있으면 DOI로 KCI와 대조한다.
- DOI가 없으면 정규화 제목 + 연도 + 제1저자로 대조한다.
- 매칭 결과는 `kci_id`, `match_method`, `match_score`로 기록한다.

**출처**
- 공식 안내: https://www.kci.go.kr/kciportal/po/openapi/openApiConnSamp.kci , https://www.kci.go.kr/kciportal/po/openapi/openDataOaiPmhView.kci
- 파라미터 정리: https://github.com/cdsassj00/kca-refresh-harness/blob/main/docs/api_specs.md
- 제약 사례(User-Agent 필터 등): https://github.com/rubatoyd/KCI_openAPI

학위논문은 KCI에 없다. 학위논문 초록은 내보내기 파일 또는 옵션 모드로만 채울 수 있다. 내보내기 파일에 초록이 들어 있는지 확인하는 것이 최우선 검증 과제인 이유다.

---

## 4. 검색어별 결과 병합과 중복 제거

### 4.1 두 가지 "중복"을 구분한다

| 유형 | 예 | 처리 |
|---|---|---|
| **레코드 중복** | 여러 검색어에서 같은 제어번호가 나온 경우. 같은 논문이 두 번 등록된 경우 | 하나로 **병합**. 어떤 검색어들에서 나왔는지(`matched_queries`)는 보존 |
| **동일 연구 다중 보고** | 석사학위논문 → 같은 저자의 학술지 논문 | **삭제하지 않고 `study_id`로 연결**. Cochrane 원칙: 분석 단위는 보고서가 아니라 연구 |

국내 교육 메타분석에서는 학위논문과 학술지판이 모두 있으면 1편으로 세고, 보통 학술지판을 채택하는 관행이 보고된다 [웹, 검색 스니펫: https://www.jkasne.org/upload/pdf/jkasne_21_3_308.pdf]. 반면 국내 메타분석이 학위논문에 편중된다는 비판도 있다 [웹: KCI ART001563377]. 따라서 기본값은 학술지판으로 두되 사용자가 바꿀 수 있게 한다.

### 4.2 판정 규칙

1. **정규화**
   - 유니코드 NFC 정규화(macOS 파일은 NFD일 수 있어 한글 매칭이 깨진다)
   - 공백·구두점 제거, 전각을 반각으로 변환, 소문자화
   - 부제 분리(`:`, `-`, `=`, `―` 뒤). 한자 병기 괄호 제거
   - 국문·영문 병기 제목은 별도 필드로 모두 비교
2. **1차(확정)**: 제어번호 일치 → 자동 병합
3. **2차**: 정규화 제목 Jaro-Winkler ≥ 0.95 + 연도 일치 + 저자 성명 교집합 → 자동 병합
4. **검토 큐**: 0.85 ≤ JW < 0.95 → 사람 확인(대시보드에서 나란히 표시)
5. **다중 보고 후보**: 저자 일치 + 학위 연도 ≤ 학술지 연도 + 제목 유사도 0.6~0.9 → `study_id` 연결 후보로 표시(원문 단계에서 표본 수 일치로 확정)

**근거**
- ASySD는 필드별 Jaro-Winkler와 휴리스틱으로 민감도 0.973, 특이도 0.999를 보였다 [웹: https://link.springer.com/article/10.1186/s12915-023-01686-z].
- 참고문헌관리기(EndNote/Zotero)의 중복 제거 민감도는 42~86%로 낮다 [웹: https://onlinelibrary.wiley.com/doi/10.1002/jrsm.1736]. 전용 규칙을 두는 이유다.
- 임계값 0.95/0.85는 일반 관례이며, 첫 실제 데이터로 보정해야 한다.

### 4.3 PRISMA 기록

PRISMA-S Item 16에 맞춰 다음을 자동 기록한다: 중복 제거 도구와 규칙 버전, 자동 병합 건수, 사람 확인 건수, 최종 제거 건수 [웹: https://link.springer.com/article/10.1186/s13643-020-01542-z].

---

## 5. 스크리닝 (Claude Code 세션 내 수행)

### 5.1 근거: LLM 스크리닝의 성능과 한계

> 이 절의 수치는 웹 검색 결과의 초록·스니펫에서 확인했다. 해당 원문 사이트(PubMed, Springer 등)가 이 환경에서 차단되어 원문 전문은 보지 못했다. 논문 인용 전에 원문으로 재확인이 필요하다.

- 18개 연구 메타분석: 제목·초록 단계 통합 민감도 0.92, 특이도 0.94 [웹: https://www.medrxiv.org/content/10.64898/2026.03.17.26348656v1.full]
- Cochrane 23개 리뷰: 민감도 0.756~1.000, 정밀도 0.004~0.096(포함 대상이 희귀하므로). LLM-사람 또는 LLM-LLM 앙상블은 민감도 100%를 유지하며 작업량을 37.6~99.1% 줄였다 [웹: https://pmc.ncbi.nlm.nih.gov/articles/PMC12012331/]
- **비영어 초록**: 기계번역 후 판정하면 민감도가 0.47~0.54로 떨어졌고, 원문을 직접 판정하면 0.71~1.00을 유지했다 [웹: https://pubmed.ncbi.nlm.nih.gov/42393975/] → **한국어 원문 그대로 판정**
- **개념이 복잡한 사회과학 주제**: 같은 설정으로 두 번 돌렸을 때 94건 판정이 엇갈렸고, 그중 29건이 실제 포함 대상이었다. 저자들은 자동 제외 대신 감사 가능한 사람 감독 워크플로를 권고한다 [웹: https://arxiv.org/abs/2608.26885]
- 다중 모델 다수결의 성능 핵심은 **모델 다양성**이었다 [웹: https://pmc.ncbi.nlm.nih.gov/articles/PMC12934882/]
- 프롬프트: 재현율 중심 단계는 상세한 포함·제외 기준 + 제로샷 판정이 권장된다 [웹: https://arxiv.org/html/2510.16091]

### 5.2 스크리닝 프로토콜(권장)

1. **기준 문서화**: `screening/criteria.md`에 PICOS를 쓴다.
   - 대상(P): 예) 초·중·고 학생
   - 중재·예측변인(I)
   - 비교(C)
   - 결과(O): 예) 학업성취
   - 설계(S): 실험·준실험·상관 등 양적연구, 효과크기 산출 가능성
   - 연도·언어
   - 포함 예시와 제외 예시 3~5건씩(경계 사례 위주)
2. **판정 라벨**: `include` / `exclude` / `uncertain`. 제외는 사유 코드 필수.
3. **이중 독립 판정**: 배치(50~100건)마다 서로 다른 모델의 서브에이전트 2개가 각각 판정한다. 서로의 결과는 보지 않는다.
4. **결합 규칙**: 하나라도 `include`나 `uncertain`이면 다음 단계로 넘긴다. 둘 다 `exclude`인 건만 제외한다.
5. **감사**: 둘 다 제외한 건에서 무작위 10%(최소 50건)를 연구자가 확인한다. 이 표본에서 놓친 포함 대상이 나오면 기준을 고치고 해당 배치를 재판정한다.
6. **사전 지정 핵심 논문**: 연구자가 반드시 포함돼야 할 논문 5~10편을 미리 지정한다. 이 논문들이 포함 판정을 받는지로 재현율을 점검한다(ASReview SAFE 절차의 아이디어) [웹: https://systematicreviewsjournal.biomedcentral.com/articles/10.1186/s13643-024-02502-7].
7. **일관성 측정**: 배치 일부(예: 5%)는 같은 모델로 재판정해 판정 흔들림 비율을 기록한다.

### 5.3 판정 레코드 형식

```json
{
  "record_id": "riss:89930b52...",
  "stage": "title_abstract",
  "reviewer": "claude-subagent-A",
  "model": "<세션이 보고한 모델명>",
  "criteria_version": "criteria.md@<git sha>",
  "decision": "exclude",
  "reason_code": "not_quantitative",
  "evidence": "본 연구는 질적 사례연구로 …",
  "confidence": 85,
  "decided_at": "2026-09-25T11:02:00+09:00"
}
```

사유 코드(예): `not_education`, `wrong_population`, `wrong_intervention`, `no_relevant_outcome`, `not_quantitative`, `review_or_theory`, `duplicate_publication`, `outside_date_range`, `insufficient_statistics`(원문 단계), `full_text_unavailable`(원문 단계)

### 5.4 세션 운영 방식

- 메인 세션은 `data/merged/records.csv`를 배치 파일(`screening/batches/batch_001.jsonl` …)로 나누는 스크립트만 실행한다.
- 각 배치는 서브에이전트가 처리한다.
  - 입력: `criteria.md` + 배치 파일
  - 출력: `screening/decisions/<reviewer>/batch_001.jsonl`
- 결합·감사 표본 추출·PRISMA 집계는 Python 스크립트로 한다(LLM이 수를 세지 않게 한다).
- 모든 산출물은 git에 커밋한다. 판정 이력 자체가 감사 추적이 된다.

---

## 6. 원문 확보와 파싱

### 6.1 원문 확보

- 목록 카드의 `originViewType`로 무료, 기관 내 무료, 유료를 구분할 수 있다 [캡처].
- 원문 다운로드(`/search/download/FullTextDownload.do`)는 로그인·기관 인증과 연결되어 있다 [캡처: `loginFlag` 필드].
- 학위논문은 저자의 원문이용동의 범위에서 dCollection을 거쳐 RISS로 제공되며, 대부분 무료다 [웹: https://www.dcollection.net/]. 국내학술논문 원문은 대부분 DBpia·KISS 등 상용 DB로 연결되어 기관 구독이 필요하다.
- 권장: 원문은 **연구자가 본인 계정으로 받아 `fulltext/<control_no>.pdf`로 저장**한다. 도구는 포함 후보 목록과 상세 페이지 링크, 원문 유형, 진행 상태만 제공한다. RISS 약관이 대량 다운로드를 금지하므로 원문 자동 다운로드는 구현하지 않는다(3.10절).
- 원문 미확보 건은 PRISMA의 "reports not retrieved"로 집계한다.

### 6.2 PDF 파싱 전략

| 상황 | 방법 |
|---|---|
| 텍스트 레이어 정상 | `PyMuPDF`로 페이지별 텍스트 추출 → "연구 결과", "표", "평균", "표준편차", "t", "F" 키워드로 결과 장 페이지 찾기 |
| 텍스트 깨짐(CID 폰트, U+FFFD 다수, 한글 비율 낮음) 또는 스캔본 | 페이지 이미지로 판독(Claude Code `Read`가 PDF 페이지를 이미지로 읽음), 필요 시 OCR(`PaddleOCR` 한국어 모델, `tesseract kor`) |
| 복잡한 표(병합 셀, 여러 페이지) | 텍스트 추출값과 페이지 이미지를 **둘 다** 보고 교차 확인 |
| HWP 원문 | `hwp-hwpx-parser` 등으로 변환하거나 PDF로 받아 처리 |

**근거**
- ToUnicode CMap이 없는 구형 한글 PDF는 텍스트 복구가 불가능해 OCR로 폴백해야 한다 [웹: https://pymupdf.readthedocs.io/en/latest/faq/index.html].
- 한국어 표 파싱을 공정하게 비교한 독립 벤치마크는 찾지 못했다. 첫 20편으로 자체 비교가 필요하다.

**세션 내 처리의 제약:** Claude Code `Read`는 PDF를 한 번에 최대 20페이지 읽는다. 학위논문(100~200쪽)은 전체를 읽지 않는다. PyMuPDF로 결과 장과 연구방법(표본) 페이지를 먼저 찾고 해당 페이지만 읽게 한다.

---

## 7. 메타분석 수치 추출 (Claude Code 세션 내 수행)

### 7.1 근거: LLM 추출의 정확도와 오류 유형

- AI가 먼저 추출하고 사람이 검토하는 방식의 정확도는 91.0%로, 사람 단독(89.0%)과 비슷하거나 높았다(63개 연구, 9,341개 항목) [웹: https://www.acpjournals.org/doi/10.7326/ANNALS-25-00739]
- 수치형 변수 정확도(47~88%)는 범주형(74~96%)보다 낮다 [웹: https://pubmed.ncbi.nlm.nih.gov/42501879/]
- 교육 분야(Visible Learning 메타분석 156편): ICC 0.96~0.97이지만 정확 일치율은 77~81%로 사람(80~86%)보다 약간 낮았다 [웹: https://link.springer.com/article/10.1007/s10648-026-10136-5]
- 주요 오류
  - **누락**
  - **SD를 SE·IQR과 혼동**
  - **표의 행·열 뒤바뀜**(LLM 검증자도 놓침)
  - 조정평균과 원평균 혼동 [웹: https://pmc.ncbi.nlm.nih.gov/articles/PMC12703319/]
- 결론: **추출은 초안, 확정은 사람**. 모든 값에 페이지와 원문 인용을 붙여 검토 시간을 줄이는 것이 핵심이다.

### 7.2 추출 스키마(효과크기 단위 long format)

한 연구에서 결과변수·시점·비교가 여러 개면 행이 여러 개다.

| 필드 | 설명 |
|---|---|
| `study_id`, `report_id`, `es_id` | 연구·보고서·효과크기 식별자(다중 보고 연결용) |
| `design` | `rct` / `quasi_nonequivalent` / `one_group_prepost` / `correlational` |
| `unit_of_assignment`, `n_clusters`, `icc` | 학급 단위 배정 여부 등 군집 보정용 |
| `outcome`, `measure_name`, `outcome_direction` | 결과변수, 측정도구, "높을수록 좋음" 여부 |
| `timepoint` | `pre` / `post` / `followup` |
| `group` | `treatment` / `control` |
| `n`, `mean`, `sd` | 집단별 기술통계 |
| `dispersion_type` | `SD` / `SE` / `CI` / `IQR` — **필수**(혼동 방지) |
| `adjusted` | ANCOVA 조정평균 여부, 공변인 |
| `test_stat_type`, `stat_value`, `df1`, `df2`, `p_value`, `p_is_inequality` | t/F/χ²/r/β와 자유도, p값("p<.05" 여부) |
| `r` | 상관계수(상관연구) |
| `r_prepost` | 사전·사후 상관(대개 미보고 → null) |
| `source_page`, `table_id`, `verbatim_quote` | 근거 위치와 원문 그대로의 인용 |
| `extractor`, `confidence`, `needs_review` | 추출 주체와 검토 필요 여부 |

### 7.3 이중 추출과 대조

- 두 서브에이전트(다른 모델)가 같은 페이지 범위에서 독립 추출한다. Python이 필드 단위로 대조해 불일치만 사람에게 보여준다.
- `verbatim_quote`는 Python이 PDF 텍스트에서 실제로 존재하는지 문자열 검색으로 확인한다. 공백과 정규화 차이는 허용한다. 존재하지 않으면 "인용 불일치"로 표시한다.

### 7.4 자동 일관성 검사(Python)

| 검사 | 규칙 |
|---|---|
| 계산 경로 존재 | `M/SD/n`, `t+n`, `F(df1=1)+n`, `p+방향+n`, `pre/post + r`, `r+n` 중 하나 이상 확보 |
| SD/SE 혼동 | SD가 평균에 비해 과도하게 작거나 SD ≈ SE×√n 관계가 의심되면 경고 |
| 재계산 대조 | M/SD/n으로 t를 다시 계산해 보고된 t·p와 비교(허용오차 초과 시 경고) |
| 표본 합계 | 집단 n의 합 = 전체 N, 탈락 반영 여부 |
| 범위 | 리커트 척도 평균이 척도 범위 안인지, r ∈ [−1, 1], p ∈ [0, 1] |

### 7.5 효과크기 계산 규약(Python에 고정)

| 설계 | 계산 | metafor 대응 |
|---|---|---|
| 두 집단 사후 비교 | S_p = √(((n₁−1)s₁² + (n₂−1)s₂²)/(n₁+n₂−2)), d = (M₁−M₂)/S_p, J = 1 − 3/(4(n₁+n₂)−9), g = J·d, V_d = (n₁+n₂)/(n₁n₂) + d²/(2(n₁+n₂)), V_g = J²·V_d | `escalc("SMD")` |
| t만 보고 | d = t·√(1/n₁ + 1/n₂) | `escalc("SMD", ti=)` |
| F(df₁=1) | t = √F, 방향 부호는 평균 비교로 결정 | 동일 |
| p만 보고 | p → t 역산, 방향 별도 기록 | `escalc("SMD", pi=)` |
| 사전·사후 + 통제집단 | Morris(2008) d_ppc2: [(M_post,T − M_pre,T) − (M_post,C − M_pre,C)] / SD_pre,pooled × 보정계수 | 집단별 `SMCR` 후 차 |
| 상관연구 | z = ½·ln((1+r)/(1−r)), V_z = 1/(n−3) | `escalc("ZCOR")` |
| d ↔ r | r = d/√(d² + a), a = (n₁+n₂)²/(n₁n₂) | — |

**주의점**
- **사전·사후 상관 r 미보고**: 0.5를 대입하고 0.3/0.7로 민감도 분석한다(Cochrane Handbook 6장) [웹: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06].
- **국내 관행 경고**: 국내 메타분석에서 흔히 쓰는 사전·사후 효과크기 계산법은 효과를 평균 2.6~68.7% 과대추정한다는 연구가 있다. 변화량의 집단 간 차(d_ppc2 계열)를 기본으로 한다 [웹: KCI ART002238763].
- **군집 배정(학급 단위)**: Hedges(2007) 보정을 적용한다. ICC 미보고 시 WWC 기본값(학업성취 0.20, 기타 0.10)을 쓰고 플래그를 단다 [웹: https://ies.ed.gov/ncee/wwc/Docs/ReferenceResources/wwc_procedures_handbook_v4_draft.pdf].
- **종속 효과크기**: 한 연구에서 여러 효과크기가 나오면 `study_id`/`es_id` long format으로 내보낸다. 분석은 CHE 모형 + RVE(`metafor::rma.mv` + `clubSandwich`)를 권장한다 [웹: https://cran.r-project.org/web/packages/clubSandwich/vignettes/meta-analysis-with-CRVE.html].
- Python 구현 시 `metafor` 공식과 결과가 같은지 R로 교차 검증하는 테스트를 둔다. Python 메타분석 엔진이 필요하면 `PyMARE`를 쓸 수 있다.

---

## 8. 대시보드

### 8.1 역할

분석을 Claude Code 세션이 맡으므로 대시보드는 **입력과 확인** 도구다. LLM 호출 기능은 없다.

1. 검색어 목록 입력, 컬렉션(학위/학술) 선택, 연도 범위 입력
2. 검색어 × 컬렉션별 **RISS 검색 링크 생성**(`pageScale=100`, `strSort=DATE`). 내보내기 체크리스트(페이지별 완료 표시)를 제공한다.
3. 내보내기 파일 업로드(검색어·컬렉션·페이지에 연결). 옵션 모드를 켜면 저속 자동 수집을 실행한다.
4. 검색어별·컬렉션별 건수, **검색어 간 중첩**(겹치는 레코드 수), RISS 표시 건수 대비 확보 건수(누락 페이지 경고)
5. 중복 검토 큐(유사 레코드 나란히 비교, 병합/분리 선택)
6. 스크리닝 결과 열람: 판정자별 결과, 불일치, 감사 표본 확인 입력
7. 추출 결과 검토: 값 + 원문 인용 + 페이지, 불일치 필드 수정
8. PRISMA 흐름도 수치 자동 집계, CSV·RIS 내보내기

### 8.2 기술 선택

- **Streamlit(권장 초기안)**: Python만으로 표, 입력 폼, 진행 표시가 빠르게 된다. 수집기와 같은 코드베이스를 쓴다. 단점은 복잡한 검토 UI(나란히 비교, 키보드 단축키)를 만들기 어렵다는 점이다.
- **FastAPI + 정적 HTML**: 검토 UI를 세밀하게 만들 수 있다. 대신 코드량이 늘어난다.
- 데이터는 파일(JSONL/CSV) + SQLite 하나로 충분하다. Claude Code 세션이 같은 파일을 읽고 써야 하므로, 사람이 읽을 수 있는 파일 형식을 원본으로 유지한다.

---

## 9. 실행 환경 제약

- **이 클라우드 세션**: `www.riss.kr`, `kci.go.kr`, `open.kci.go.kr`가 네트워크 정책상 차단(프록시 403). `data.riss.kr`도 403이다.
  - 기본 모드(내보내기 파일)는 네트워크가 필요 없다. 파일을 `data/raw/`에 커밋·푸시하면 이 세션에서 병합·스크리닝·추출을 모두 할 수 있다.
  - KCI 보강을 이 세션에서 돌리려면 클라우드 환경 설정(세션 제목 표시줄의 환경 메뉴 → Edit)의 **Network access**에서 `open.kci.go.kr`를 허용 목록에 추가한다. 옵션 모드를 쓸 경우 `www.riss.kr`도 추가한다. 문서: https://code.claude.com/docs/en/claude-code-on-the-web
  - 또는 보강·옵션 수집 스크립트를 연구자 PC에서 실행하고 결과만 커밋한다.
- 원문 PDF는 로그인이 필요하므로 어느 경우든 연구자 PC에서 받아 저장소(또는 비공개 저장소)에 올린다. 원문 PDF의 저작권상 **공개 저장소에 올리지 않는다**.

---

## 10. 검증되지 않은 사항과 다음 단계

**연구자가 먼저 해 줄 일(구현 전 가장 중요한 입력)**
1. RISS에서 검색어 하나로 학위논문 100건, 국내학술논문 100건을 **Excel과 RIS 두 형식으로 각각 내보내** 저장소 `samples/`에 올린다. 이 샘플로 다음을 확인하고 파서 스키마를 확정한다.
   - 컬럼 구성, 초록 포함 여부, 제어번호 포함 여부
2. 내보내기할 때 로그인이 필요했는지, 여러 페이지를 한 번에 선택할 수 있었는지 알려준다.
3. 소속 기관이 RISS OpenAPI 키를 갖고 있는지 확인한다(있으면 자동 경로가 합법적으로 열린다).
4. 첫 메타분석 주제의 PICOS와 반드시 포함돼야 할 핵심 논문 5~10편 목록을 준다.

**실사이트에서 확인할 것(옵션 모드를 쓸 경우)**
1. robots.txt 내용과 `/search/Search.do` 허용 여부
2. `p_year1/p_year2`, `queryText`(필드 한정·불리언) 파라미터의 실제 동작
3. 상세 페이지(`DetailView.do`)의 필드: 주제어, 전공, 지도교수, 페이지 수
4. 2026년 현재 마크업이 캡처(2026-03) 당시와 같은지 → 파서 fixture 갱신

**구현 순서 제안**
1. 내보내기 파일 파서(Excel/RIS/BibTeX) + 공통 스키마 + 샘플 기반 테스트
2. 검색어별 병합·중복 제거 + 검토 큐
3. 스크리닝 배치 분할·결합 스크립트, `criteria.md` 템플릿, 세션 스크리닝 1회 시범(검색어 1개, 200건 내외)
4. 대시보드(Streamlit): 검색 링크 생성, 업로드, 현황, 검토 화면
5. KCI 보강(OAI-PMH/REST)
6. 원문 페이지 탐색 + 추출 스키마 + 일관성 검사 + 효과크기 계산
7. PRISMA 집계와 내보내기
8. (선택) 옵션 모드 저속 수집기 — 캡처 HTML fixture 테스트 포함

---

## 11. 참고 자료

**RISS 사이트 구조 근거**
- 이전 프로토타입 캡처: git 커밋 `7097837`의 `tmp_www_riss_search.html`, `tmp_www_riss_bib_t*.html`, `tmp_www_riss_search.js`, `tmp_riss_sparql*`, `tmp_riss_property.html`, `backend/app/services/connectors.py`
- RISS 내보내기 형식 소개: https://www.welfare24.net/ab-3435-44
- RISS 레코드 내보내기 페이지(검색 스니펫): https://www.riss.kr/Export.do?control_no=1ee62ed6ac1af108&p_mat_type=be54d9b8bc7cdb09&loginFlag=1
- 오픈소스 RISS 수집 사례: https://github.com/jaygil8755/crawl_riss , https://github.com/mwobareullae/jungle_namanmoo , https://github.com/ezcar111/textom_cube
- Zotero 커뮤니티 translator(RISS, 초록 미추출): https://github.com/go00ood/zotero-translators-kr

**접근 경로·약관·법**
- RISS 이용약관: https://www.riss.kr/etc/clause.html
- RISS API 센터: https://www.riss.kr/apicenter/apiMain.do
- RISS 검색 OpenAPI 규격 정리: https://github.com/NomaDamas/k-skill/blob/main/docs/features/keris-academic-search.md
- RISS LOD: https://data.riss.kr/LODintro.do
- KCI OpenAPI: https://www.kci.go.kr/kciportal/po/openapi/openApiConnSamp.kci
- KCI OAI-PMH: https://www.kci.go.kr/kciportal/po/openapi/openDataOaiPmhView.kci
- 국회도서관 OpenAPI: https://www.nanet.go.kr/usermadang/etc/openApiView.do
- 대법원 2021도1533: https://www.law.go.kr/precInfoP.do?precSeq=221765
- 잡코리아 v. 사람인: https://lawtimes.co.kr/news/121766
- 부정경쟁방지법 데이터 조항: https://www.kimchang.com/ko/insights/detail.kc?sch_section=4&idx=24264

**중복 제거**
- ASySD: https://link.springer.com/article/10.1186/s12915-023-01686-z
- 중복 제거 도구 비교: https://www.sciencedirect.com/science/article/abs/pii/S0895435622002566 , https://onlinelibrary.wiley.com/doi/10.1002/jrsm.1736
- PRISMA-S: https://link.springer.com/article/10.1186/s13643-020-01542-z

**스크리닝**
- LLM 스크리닝 메타분석: https://www.medrxiv.org/content/10.64898/2026.03.17.26348656v1.full
- Cochrane 리뷰 기반 LLM 스크리닝: https://pmc.ncbi.nlm.nih.gov/articles/PMC12012331/
- 비영어 초록 스크리닝: https://pubmed.ncbi.nlm.nih.gov/42393975/
- 사회과학 주제 재현성: https://arxiv.org/abs/2608.26885
- 다중 LLM 다수결: https://pmc.ncbi.nlm.nih.gov/articles/PMC12934882/
- ASReview v2: https://www.sciencedirect.com/science/article/pii/S2666389925001667
- SAFE 중단 절차: https://systematicreviewsjournal.biomedcentral.com/articles/10.1186/s13643-024-02502-7
- PRISMA 2020: https://pmc.ncbi.nlm.nih.gov/articles/PMC8005925/
- RAISE 공동 입장문: https://pmc.ncbi.nlm.nih.gov/articles/PMC12603384/

**추출·효과크기**
- AI 보조 추출: https://www.acpjournals.org/doi/10.7326/ANNALS-25-00739
- LLM 추출 체계적 고찰: https://pubmed.ncbi.nlm.nih.gov/42501879/
- 교육 분야 LLM 코딩: https://link.springer.com/article/10.1007/s10648-026-10136-5
- 추출 오류 유형: https://pmc.ncbi.nlm.nih.gov/articles/PMC12703319/
- Borenstein 효과크기(평균 기반): https://meta-analysis.com/download/Meta-analysis%20Effect%20sizes%20based%20on%20means.pdf
- metafor `escalc`: https://wviechtb.github.io/metafor/reference/escalc.html
- Morris(2008) metafor 예시: https://www.metafor-project.org/doku.php/analyses:morris2008
- Cochrane Handbook 5·6장: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-05 , https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
- 군집 보정 Hedges(2007): https://journals.sagepub.com/doi/10.3102/1076998606298043
- WWC 절차 핸드북: https://ies.ed.gov/ncee/wwc/Docs/ReferenceResources/wwc_procedures_handbook_v4_draft.pdf
- CHE + RVE: https://cran.r-project.org/web/packages/clubSandwich/vignettes/meta-analysis-with-CRVE.html

**PDF 파싱**
- PyMuPDF FAQ: https://pymupdf.readthedocs.io/en/latest/faq/index.html
- PaddleOCR 한국어: https://github.com/PaddlePaddle/PaddleOCR/issues/15373
- OmniDocBench: https://github.com/opendatalab/OmniDocBench

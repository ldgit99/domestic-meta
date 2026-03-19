import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Iterable

from app.core.config import settings
from app.core.constants import SOURCE_KCI, SOURCE_RISS
from app.core.utils import generate_id
from app.models.domain import CandidateRecord, SearchRequest


class BaseConnector:
    source_name: str

    def collect(self, request: SearchRequest) -> Iterable[CandidateRecord]:
        raise NotImplementedError

    def _split_values(self, value: object, default: list[str] | None = None) -> list[str]:
        if value is None:
            return default or []
        text = str(value).replace(";", ",")
        values = [item.strip() for item in text.split(",") if item.strip()]
        return values or (default or [])

    def _parse_year(self, value: object, fallback: int = 0) -> int:
        if value is None:
            return fallback
        text = str(value).strip()
        try:
            return int(text[:4])
        except ValueError:
            return fallback

    def _flatten_mapping(self, item: dict) -> dict[str, str]:
        flattened: dict[str, str] = {}
        for key, value in item.items():
            if isinstance(value, dict) and "value" in value:
                flattened[key] = str(value.get("value", "")).strip()
            elif isinstance(value, list):
                parts = []
                for entry in value:
                    if isinstance(entry, dict) and "value" in entry:
                        parts.append(str(entry.get("value", "")).strip())
                    elif entry is not None:
                        parts.append(str(entry).strip())
                flattened[key] = ", ".join(part for part in parts if part)
            elif value is not None:
                flattened[key] = str(value).strip()
        return flattened

    def _parse_json_records(self, payload: str) -> list[dict]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []

        if isinstance(data, dict):
            results = data.get("results")
            if isinstance(results, dict) and isinstance(results.get("bindings"), list):
                return [self._flatten_mapping(item) for item in results["bindings"] if isinstance(item, dict)]

        records = None
        if isinstance(data, dict):
            records = (
                data.get("items")
                or data.get("results")
                or data.get("records")
                or data.get("docs")
                or data.get("data")
            )

        if isinstance(records, dict):
            records = records.get("item") or records.get("records") or records.get("docs") or records.get("items")

        if not isinstance(records, list):
            return []

        return [self._flatten_mapping(item) for item in records if isinstance(item, dict)]

    def _parse_xml_records(self, payload: str) -> list[dict]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return []

        records = root.findall(".//record") or root.findall(".//item") or root.findall(".//result")
        if not records:
            records = [node for node in root.iter() if list(node)]

        output: list[dict] = []
        for node in records[:20]:
            mapping = {
                child.tag.split("}")[-1]: (child.text or "").strip()
                for child in node
                if (child.text or "").strip()
            }
            if mapping:
                output.append(mapping)
        return output


class KCIStubConnector(BaseConnector):
    source_name = SOURCE_KCI

    def collect(self, request: SearchRequest) -> Iterable[CandidateRecord]:
        if not request.include_journal_articles:
            return []

        query = request.query_text
        return [
            CandidateRecord(
                id=generate_id("cand"),
                search_request_id=request.id,
                source=self.source_name,
                source_record_id="kci-001",
                title=f"{query}이 학업성취도에 미치는 효과",
                authors=["김연구", "박분석"],
                year=2022,
                journal_or_school="교육평가연구",
                abstract="중학생 대상 비교집단 연구로 사전-사후 평균과 표준편차를 보고하였다.",
                keywords=[query, "학업성취도", "비교집단"],
                doi="10.0000/example-001",
                url="https://example.org/kci/001",
                document_type="journal_article",
                language="ko",
                raw_payload={"source": "stub", "origin": "kci"},
                status="collected",
            ),
            CandidateRecord(
                id=generate_id("cand"),
                search_request_id=request.id,
                source=self.source_name,
                source_record_id="kci-002",
                title=f"{query} 관련 질적 사례연구",
                authors=["이질적"],
                year=2021,
                journal_or_school="교육방법연구",
                abstract="면담과 참여관찰을 활용한 질적 사례연구이다.",
                keywords=[query, "질적연구"],
                doi=None,
                url="https://example.org/kci/002",
                document_type="journal_article",
                language="ko",
                raw_payload={"source": "stub", "origin": "kci"},
                status="collected",
            ),
        ]


class KCILiveConnector(BaseConnector):
    source_name = SOURCE_KCI

    def collect(self, request: SearchRequest) -> Iterable[CandidateRecord]:
        if not request.include_journal_articles:
            return []
        if not settings.kci_live_enabled or not settings.kci_api_url or not settings.kci_api_key:
            return []

        params = {
            settings.kci_api_key_param: settings.kci_api_key,
            settings.kci_query_param: request.query_text,
            settings.kci_count_param: "20",
        }
        url = f"{settings.kci_api_url}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                payload = response.read().decode("utf-8", errors="replace")
        except Exception:
            return []

        if settings.kci_response_format.lower() == "json":
            records = self._parse_json_records(payload)
        else:
            records = self._parse_xml_records(payload)
        return [self._candidate_from_mapping(item, request) for item in records]

    def _candidate_from_mapping(self, item: dict, request: SearchRequest) -> CandidateRecord:
        title = (
            item.get("title")
            or item.get("articleTitle")
            or item.get("journalTitle")
            or f"{request.query_text} 관련 KCI 논문"
        )
        authors = item.get("authors") or item.get("author") or item.get("creator") or ""
        author_list = self._split_values(authors, default=["미상"])
        year = self._parse_year(item.get("year") or item.get("pubYear") or item.get("publicationYear"))

        keywords = item.get("keywords") or item.get("keyword") or request.query_text
        keyword_list = self._split_values(keywords, default=[request.query_text])
        abstract = item.get("abstract") or item.get("description") or ""
        record_id = item.get("id") or item.get("articleId") or item.get("identifier") or generate_id("kci")
        journal = item.get("journal") or item.get("journalTitle") or item.get("publisher") or "KCI"
        doi = item.get("doi")
        url = item.get("url") or item.get("link")

        return CandidateRecord(
            id=generate_id("cand"),
            search_request_id=request.id,
            source=self.source_name,
            source_record_id=str(record_id),
            title=title,
            authors=author_list,
            year=year,
            journal_or_school=journal,
            abstract=abstract,
            keywords=keyword_list,
            doi=doi,
            url=url,
            document_type="journal_article",
            language="ko",
            raw_payload={"source": "live", "origin": "kci", "item": item},
            status="collected",
        )


class KCIConnector(BaseConnector):
    source_name = SOURCE_KCI

    def __init__(self) -> None:
        self.live = KCILiveConnector()
        self.stub = KCIStubConnector()

    def collect(self, request: SearchRequest) -> Iterable[CandidateRecord]:
        live_items = list(self.live.collect(request))
        if live_items:
            return live_items
        return self.stub.collect(request)


class RISSStubConnector(BaseConnector):
    source_name = SOURCE_RISS

    def collect(self, request: SearchRequest) -> Iterable[CandidateRecord]:
        query = request.query_text
        items: list[CandidateRecord] = []

        if request.include_theses:
            items.append(
                CandidateRecord(
                    id=generate_id("cand"),
                    search_request_id=request.id,
                    source=self.source_name,
                    source_record_id="riss-001",
                    title=f"{query}이 학업성취도에 미치는 효과",
                    authors=["김연구"],
                    year=2022,
                    journal_or_school="A대학교 교육대학원",
                    abstract="실험집단과 통제집단의 사전-사후 검사 결과를 제시한 학위논문이다.",
                    keywords=[query, "실험연구", "학위논문"],
                    doi=None,
                    url="https://example.org/riss/001",
                    document_type="thesis",
                    language="ko",
                    raw_payload={"source": "stub", "origin": "riss"},
                    status="collected",
                )
            )

        if request.include_journal_articles:
            items.append(
                CandidateRecord(
                    id=generate_id("cand"),
                    search_request_id=request.id,
                    source=self.source_name,
                    source_record_id="riss-002",
                    title=f"{query} 프로그램의 교육효과 분석",
                    authors=["최연구"],
                    year=2020,
                    journal_or_school="교육공학연구",
                    abstract="교육 프로그램 적용 후 비교집단의 평균 차이를 보고한 학술논문이다.",
                    keywords=[query, "교육효과", "학술논문"],
                    doi=None,
                    url="https://example.org/riss/002",
                    document_type="journal_article",
                    language="ko",
                    raw_payload={"source": "stub", "origin": "riss"},
                    status="collected",
                )
            )

        return items


class RISSLiveConnector(BaseConnector):
    source_name = SOURCE_RISS

    def collect(self, request: SearchRequest) -> Iterable[CandidateRecord]:
        if not settings.riss_live_enabled or not settings.riss_api_url:
            return []

        params: dict[str, str] = {settings.riss_query_param: request.query_text}
        if settings.riss_api_key and settings.riss_api_key_param:
            params[settings.riss_api_key_param] = settings.riss_api_key
        if settings.riss_count_param:
            params[settings.riss_count_param] = "20"

        if settings.riss_document_type_param:
            if request.include_theses and not request.include_journal_articles:
                params[settings.riss_document_type_param] = settings.riss_thesis_value
            elif request.include_journal_articles and not request.include_theses:
                params[settings.riss_document_type_param] = settings.riss_journal_value

        url = f"{settings.riss_api_url}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                payload = response.read().decode("utf-8", errors="replace")
        except Exception:
            return []

        if settings.riss_response_format.lower() == "xml":
            records = self._parse_xml_records(payload)
        else:
            records = self._parse_json(payload)

        candidates = [self._candidate_from_mapping(item, request) for item in records]
        return [item for item in candidates if self._matches_request(item, request)]

    def _parse_json(self, payload: str) -> list[dict]:
        return self._parse_json_records(payload)

    def _candidate_from_mapping(self, item: dict, request: SearchRequest) -> CandidateRecord:
        title = (
            item.get("title")
            or item.get("riss.title")
            or item.get("dc:title")
            or f"{request.query_text} 관련 RISS 논문"
        )
        authors = (
            item.get("authors")
            or item.get("author")
            or item.get("creator")
            or item.get("dc:creator")
            or ""
        )
        author_list = self._split_values(authors, default=["미상"])
        year = self._parse_year(
            item.get("year")
            or item.get("pubYear")
            or item.get("publicationYear")
            or item.get("issued")
            or item.get("dcterms:issued")
        )

        keywords = item.get("keywords") or item.get("keyword") or item.get("subject") or request.query_text
        keyword_list = self._split_values(keywords, default=[request.query_text])
        abstract = item.get("abstract") or item.get("description") or item.get("dc:description") or ""
        record_id = (
            item.get("id")
            or item.get("identifier")
            or item.get("uri")
            or item.get("link")
            or generate_id("riss")
        )
        location = (
            item.get("school")
            or item.get("degreeGrantor")
            or item.get("publisher")
            or item.get("journal")
            or item.get("journalTitle")
            or item.get("isPartOf")
            or "RISS"
        )
        doi = item.get("doi")
        url = item.get("url") or item.get("link") or item.get("uri")
        document_type = self._infer_document_type(item)
        language = item.get("language") or item.get("dc:language") or "ko"

        return CandidateRecord(
            id=generate_id("cand"),
            search_request_id=request.id,
            source=self.source_name,
            source_record_id=str(record_id),
            title=title,
            authors=author_list,
            year=year,
            journal_or_school=location,
            abstract=abstract,
            keywords=keyword_list,
            doi=doi,
            url=url,
            document_type=document_type,
            language=language,
            raw_payload={"source": "live", "origin": "riss", "item": item},
            status="collected",
        )

    def _infer_document_type(self, item: dict) -> str:
        raw_type = " ".join(
            str(item.get(key, ""))
            for key in [
                "documentType",
                "type",
                "publicationType",
                "genre",
                "degree",
                "collection",
            ]
        ).lower()
        if any(token in raw_type for token in ["thesis", "dissertation", "학위", "석사", "박사"]):
            return "thesis"
        return "journal_article"

    def _matches_request(self, candidate: CandidateRecord, request: SearchRequest) -> bool:
        if candidate.document_type == "thesis" and not request.include_theses:
            return False
        if candidate.document_type == "journal_article" and not request.include_journal_articles:
            return False
        return True


class RISSConnector(BaseConnector):
    source_name = SOURCE_RISS

    def __init__(self) -> None:
        self.live = RISSLiveConnector()
        self.stub = RISSStubConnector()

    def collect(self, request: SearchRequest) -> Iterable[CandidateRecord]:
        live_items = list(self.live.collect(request))
        if live_items:
            return live_items
        return self.stub.collect(request)

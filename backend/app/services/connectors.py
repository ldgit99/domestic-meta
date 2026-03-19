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


class KCIStubConnector(BaseConnector):
    source_name = SOURCE_KCI

    def collect(self, request: SearchRequest) -> Iterable[CandidateRecord]:
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
            return self._parse_json(payload, request)
        return self._parse_xml(payload, request)

    def _parse_json(self, payload: str, request: SearchRequest) -> list[CandidateRecord]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []

        records = data.get("items") or data.get("results") or data.get("records") or []
        if isinstance(records, dict):
            records = records.get("item") or records.get("records") or []
        if not isinstance(records, list):
            return []

        return [self._candidate_from_mapping(item, request) for item in records if isinstance(item, dict)]

    def _parse_xml(self, payload: str, request: SearchRequest) -> list[CandidateRecord]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return []

        records = root.findall(".//record") or root.findall(".//item") or root.findall(".//result")
        if not records:
            records = [node for node in root.iter() if list(node)]
        candidates = []
        for node in records[:20]:
            mapping = {child.tag.split("}")[-1]: (child.text or "").strip() for child in node if (child.text or "").strip()}
            if mapping:
                candidates.append(self._candidate_from_mapping(mapping, request))
        return candidates

    def _candidate_from_mapping(self, item: dict, request: SearchRequest) -> CandidateRecord:
        title = (
            item.get("title")
            or item.get("articleTitle")
            or item.get("journalTitle")
            or f"{request.query_text} 관련 KCI 논문"
        )
        authors = item.get("authors") or item.get("author") or item.get("creator") or ""
        author_list = [part.strip() for part in str(authors).replace(";", ",").split(",") if part.strip()] or ["미상"]
        year_value = item.get("year") or item.get("pubYear") or item.get("publicationYear") or "0"
        try:
            year = int(str(year_value)[:4])
        except ValueError:
            year = 0

        keywords = item.get("keywords") or item.get("keyword") or request.query_text
        keyword_list = [part.strip() for part in str(keywords).replace(";", ",").split(",") if part.strip()]
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
        if not request.include_theses:
            return []
        query = request.query_text
        return [
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
        ]

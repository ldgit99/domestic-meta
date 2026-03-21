import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from app.core.config import settings
from app.core.constants import SOURCE_KCI, SOURCE_RISS
from app.core.utils import generate_id
from app.models.domain import CandidateRecord, SearchRequest, SourceCollectionResult
from app.services.search_plans import SourceSearchPlan, build_kci_search_plan, build_riss_search_plan


class BaseConnector:
    source_name: str

    def collect(self, request: SearchRequest) -> SourceCollectionResult | None:
        raise NotImplementedError

    def build_search_plan(self, request: SearchRequest) -> SourceSearchPlan:
        raise NotImplementedError

    def _build_collection(
        self,
        plan: SourceSearchPlan,
        candidates: list[CandidateRecord],
        *,
        backend: str,
        total_hits: int | None = None,
    ) -> SourceCollectionResult:
        return SourceCollectionResult(
            source=self.source_name,
            backend=backend,
            query_mode=plan.mode,
            query_plan=plan.to_dict(),
            total_hits=total_hits if total_hits is not None else len(candidates),
            candidates=candidates,
        )

    def _plan_metadata(self, plan: SourceSearchPlan) -> dict:
        return plan.to_dict()

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

    def _parse_json_records(self, payload: str) -> tuple[list[dict], int | None]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return [], None

        total_hits = self._extract_total_hits_from_json(data)

        if isinstance(data, dict):
            results = data.get("results")
            if isinstance(results, dict) and isinstance(results.get("bindings"), list):
                return [self._flatten_mapping(item) for item in results["bindings"] if isinstance(item, dict)], total_hits

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
            return [], total_hits

        return [self._flatten_mapping(item) for item in records if isinstance(item, dict)], total_hits

    def _parse_xml_records(self, payload: str) -> tuple[list[dict], int | None]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return [], None

        total_hits = self._extract_total_hits_from_xml(root)
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
        return output, total_hits

    def _extract_total_hits_from_json(self, value: object) -> int | None:
        if isinstance(value, dict):
            for key in [
                "totalCount",
                "total_count",
                "totalHits",
                "total_hits",
                "recordCount",
                "record_count",
                "numFound",
                "totalResults",
                "total_results",
                "resultCount",
            ]:
                if key in value:
                    parsed = self._parse_int(value.get(key))
                    if parsed is not None:
                        return parsed
            for nested_key in ["meta", "summary", "search", "result", "results", "response", "header", "body", "data"]:
                if nested_key in value:
                    parsed = self._extract_total_hits_from_json(value.get(nested_key))
                    if parsed is not None:
                        return parsed
        elif isinstance(value, list):
            for item in value:
                parsed = self._extract_total_hits_from_json(item)
                if parsed is not None:
                    return parsed
        return None

    def _extract_total_hits_from_xml(self, root: ET.Element) -> int | None:
        for xpath in [
            ".//totalCount",
            ".//total_count",
            ".//totalHits",
            ".//recordCount",
            ".//resultCount",
            ".//numFound",
        ]:
            node = root.find(xpath)
            if node is not None and node.text:
                parsed = self._parse_int(node.text)
                if parsed is not None:
                    return parsed
        for attribute in ["totalCount", "total_count", "totalHits", "recordCount", "resultCount"]:
            parsed = self._parse_int(root.attrib.get(attribute))
            if parsed is not None:
                return parsed
        return None

    def _parse_int(self, value: object) -> int | None:
        if value is None:
            return None
        text = str(value).strip().replace(",", "")
        return int(text) if text.isdigit() else None

    def _matches_request(self, candidate: CandidateRecord, request: SearchRequest) -> bool:
        if candidate.year and (candidate.year < request.year_from or candidate.year > request.year_to):
            return False
        if candidate.document_type == "thesis" and not request.include_theses:
            return False
        if candidate.document_type == "journal_article" and not request.include_journal_articles:
            return False
        return True


class KCIStubConnector(BaseConnector):
    source_name = SOURCE_KCI

    def build_search_plan(self, request: SearchRequest) -> SourceSearchPlan:
        return build_kci_search_plan(request)

    def collect(self, request: SearchRequest) -> SourceCollectionResult:
        plan = self.build_search_plan(request)
        if not request.include_journal_articles:
            return self._build_collection(plan, [], backend="stub", total_hits=0)

        query = plan.query_text
        items = [
            CandidateRecord(
                id=generate_id("cand"),
                search_request_id=request.id,
                source=self.source_name,
                source_record_id="kci-001",
                title=f"{query} intervention effects on academic achievement",
                authors=["Kim", "Park"],
                year=2022,
                journal_or_school="Korean Journal of Education",
                abstract=(
                    "A quantitative study comparing intervention and control groups with means "
                    "and standard deviations."
                ),
                keywords=[query, "achievement", "control group"],
                doi="10.0000/example-001",
                url="https://example.org/kci/001",
                document_type="journal_article",
                language="ko",
                raw_payload={"source": "stub", "origin": "kci", "query_plan": self._plan_metadata(plan)},
                status="collected",
            ),
            CandidateRecord(
                id=generate_id("cand"),
                search_request_id=request.id,
                source=self.source_name,
                source_record_id="kci-002",
                title=f"Qualitative reflections on {query}",
                authors=["Lee"],
                year=2021,
                journal_or_school="Educational Methods Review",
                abstract="An interview-based qualitative study of classroom experiences.",
                keywords=[query, "qualitative"],
                doi=None,
                url="https://example.org/kci/002",
                document_type="journal_article",
                language="ko",
                raw_payload={"source": "stub", "origin": "kci", "query_plan": self._plan_metadata(plan)},
                status="collected",
            ),
        ]
        candidates = [item for item in items if self._matches_request(item, request)]
        return self._build_collection(plan, candidates, backend="stub", total_hits=len(candidates))


class KCILiveConnector(BaseConnector):
    source_name = SOURCE_KCI

    def build_search_plan(self, request: SearchRequest) -> SourceSearchPlan:
        return build_kci_search_plan(request)

    def collect(self, request: SearchRequest) -> SourceCollectionResult | None:
        if not request.include_journal_articles:
            return self._build_collection(self.build_search_plan(request), [], backend="live", total_hits=0)
        if not settings.kci_live_enabled or not settings.kci_api_url or not settings.kci_api_key:
            return None

        plan = self.build_search_plan(request)
        params = dict(plan.params)
        params[settings.kci_api_key_param] = settings.kci_api_key
        url = f"{settings.kci_api_url}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                payload = response.read().decode("utf-8", errors="replace")
        except Exception:
            return None

        if settings.kci_response_format.lower() == "json":
            records, total_hits = self._parse_json_records(payload)
        else:
            records, total_hits = self._parse_xml_records(payload)

        candidates = [self._candidate_from_mapping(item, request, plan) for item in records]
        filtered = [item for item in candidates if self._matches_request(item, request)]
        return self._build_collection(plan, filtered, backend="live", total_hits=total_hits or len(filtered))

    def _candidate_from_mapping(self, item: dict, request: SearchRequest, plan: SourceSearchPlan) -> CandidateRecord:
        title = (
            item.get("title")
            or item.get("articleTitle")
            or item.get("journalTitle")
            or f"{request.query_text} related KCI article"
        )
        authors = item.get("authors") or item.get("author") or item.get("creator") or ""
        author_list = self._split_values(authors, default=["unknown"])
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
            raw_payload={"source": "live", "origin": "kci", "item": item, "query_plan": self._plan_metadata(plan)},
            status="collected",
        )


class KCIConnector(BaseConnector):
    source_name = SOURCE_KCI

    def __init__(self) -> None:
        self.live = KCILiveConnector()
        self.stub = KCIStubConnector()

    def build_search_plan(self, request: SearchRequest) -> SourceSearchPlan:
        return self.live.build_search_plan(request)

    def collect(self, request: SearchRequest) -> SourceCollectionResult:
        live_result = self.live.collect(request)
        if live_result is not None:
            return live_result
        return self.stub.collect(request)


class RISSStubConnector(BaseConnector):
    source_name = SOURCE_RISS

    def build_search_plan(self, request: SearchRequest) -> SourceSearchPlan:
        return build_riss_search_plan(request)

    def collect(self, request: SearchRequest) -> SourceCollectionResult:
        plan = self.build_search_plan(request)
        query = plan.query_text
        items: list[CandidateRecord] = []

        if request.include_theses:
            items.append(
                CandidateRecord(
                    id=generate_id("cand"),
                    search_request_id=request.id,
                    source=self.source_name,
                    source_record_id="riss-001",
                    title=f"{query} effects on academic achievement",
                    authors=["Kim"],
                    year=2022,
                    journal_or_school="Graduate School of Education",
                    abstract="A thesis reporting pretest and posttest group comparisons.",
                    keywords=[query, "thesis", "experimental"],
                    doi=None,
                    url="https://example.org/riss/001",
                    document_type="thesis",
                    language="ko",
                    raw_payload={"source": "stub", "origin": "riss", "query_plan": self._plan_metadata(plan)},
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
                    title=f"{query} program evaluation",
                    authors=["Choi"],
                    year=2020,
                    journal_or_school="Journal of Educational Engineering",
                    abstract="A journal article comparing intervention and control group means.",
                    keywords=[query, "journal article", "evaluation"],
                    doi=None,
                    url="https://example.org/riss/002",
                    document_type="journal_article",
                    language="ko",
                    raw_payload={"source": "stub", "origin": "riss", "query_plan": self._plan_metadata(plan)},
                    status="collected",
                )
            )

        candidates = [item for item in items if self._matches_request(item, request)]
        return self._build_collection(plan, candidates, backend="stub", total_hits=len(candidates))


class RISSLiveConnector(BaseConnector):
    source_name = SOURCE_RISS

    def build_search_plan(self, request: SearchRequest) -> SourceSearchPlan:
        return build_riss_search_plan(request)

    def collect(self, request: SearchRequest) -> SourceCollectionResult | None:
        if not settings.riss_live_enabled or not settings.riss_api_url:
            return None

        plan = self.build_search_plan(request)
        params = dict(plan.params)
        if settings.riss_api_key and settings.riss_api_key_param:
            params[settings.riss_api_key_param] = settings.riss_api_key

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
            return None

        if settings.riss_response_format.lower() == "xml":
            records, total_hits = self._parse_xml_records(payload)
        else:
            records, total_hits = self._parse_json(payload)

        candidates = [self._candidate_from_mapping(item, request, plan) for item in records]
        filtered = [item for item in candidates if self._matches_request(item, request)]
        return self._build_collection(plan, filtered, backend="live", total_hits=total_hits or len(filtered))

    def _parse_json(self, payload: str) -> tuple[list[dict], int | None]:
        return self._parse_json_records(payload)

    def _candidate_from_mapping(self, item: dict, request: SearchRequest, plan: SourceSearchPlan) -> CandidateRecord:
        title = (
            item.get("title")
            or item.get("riss.title")
            or item.get("dc:title")
            or f"{request.query_text} related RISS record"
        )
        authors = (
            item.get("authors")
            or item.get("author")
            or item.get("creator")
            or item.get("dc:creator")
            or ""
        )
        author_list = self._split_values(authors, default=["unknown"])
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
            raw_payload={"source": "live", "origin": "riss", "item": item, "query_plan": self._plan_metadata(plan)},
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
        if any(token in raw_type for token in ["thesis", "dissertation", "masters", "doctoral"]):
            return "thesis"
        return "journal_article"


class RISSConnector(BaseConnector):
    source_name = SOURCE_RISS

    def __init__(self) -> None:
        self.live = RISSLiveConnector()
        self.stub = RISSStubConnector()

    def build_search_plan(self, request: SearchRequest) -> SourceSearchPlan:
        return self.live.build_search_plan(request)

    def collect(self, request: SearchRequest) -> SourceCollectionResult:
        live_result = self.live.collect(request)
        if live_result is not None:
            return live_result
        return self.stub.collect(request)

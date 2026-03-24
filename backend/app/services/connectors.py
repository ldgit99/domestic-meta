import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape

from app.core.config import settings
from app.core.constants import SOURCE_KCI, SOURCE_RISS
from app.core.utils import generate_id
from app.models.domain import CandidateRecord, SearchRequest, SourceCollectionResult
from app.services.search_plans import SourceSearchPlan, build_kci_search_plan, build_riss_search_plan


RISS_BASE_URL = "https://www.riss.kr"
RISS_DEFAULT_WEB_URL = f"{RISS_BASE_URL}/search/Search.do"
RISS_DEFAULT_SPARQL_URL = "https://data.riss.kr/sparql"
RISS_WEB_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/134.0.0.0 Safari/537.36"
)
RISS_WEB_TOTAL_HITS_RE = re.compile(
    r"<div class=\"searchBox pd\">.*?<span[^>]*class=[\"']num[\"'][^>]*>\s*([\d,]+)\s*</span>",
    re.IGNORECASE | re.DOTALL,
)
RISS_WEB_SECTION_COUNT_RE = re.compile(
    r"<span[^>]*class=[\"']moreCnt[\"'][^>]*>\s*([\d,]+)\s*</span>",
    re.IGNORECASE | re.DOTALL,
)
RISS_WEB_TITLE_RE = re.compile(r'<p class="title"><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></p>', re.DOTALL)
RISS_WEB_ETC_RE = re.compile(r'<p class="etc">(.*?)</p>', re.DOTALL)
RISS_WEB_SPAN_RE = re.compile(r'<span(?:[^>]*class="([^"]*)")?[^>]*>(.*?)</span>', re.DOTALL)
RISS_WEB_ABSTRACT_RE = re.compile(r'<p class="preAbstract">(.*?)</p>', re.DOTALL)
RISS_WEB_TAG_RE = re.compile(r"<[^>]+>")
SPARQL_RESULTS_NS = {"sr": "http://www.w3.org/2005/sparql-results#"}


def _clean_riss_html_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(RISS_WEB_TAG_RE.sub(" ", value or ""))).strip()


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

        if root.tag.split("}")[-1] == "sparql":
            return self._parse_sparql_xml_records(root), self._extract_total_hits_from_xml(root)

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

    def _parse_sparql_xml_records(self, root: ET.Element) -> list[dict[str, str]]:
        output: list[dict[str, str]] = []
        for node in root.findall(".//sr:result", SPARQL_RESULTS_NS)[:20]:
            mapping: dict[str, str] = {}
            for binding in node.findall("sr:binding", SPARQL_RESULTS_NS):
                name = str(binding.attrib.get("name") or "").strip()
                if not name:
                    continue
                value_node = next(iter(list(binding)), None)
                text = (value_node.text or "").strip() if value_node is not None else ""
                if not text:
                    continue
                mapping[name] = text
                mapping[name.lower()] = text
            if mapping:
                output.append(mapping)
        return output

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
        if not settings.riss_live_enabled:
            return None

        plan = self.build_search_plan(request)
        if plan.mode == "riss_web_full_search":
            return self._collect_web_search(request, plan)

        uses_sparql = plan.mode == "riss_sparql_keyword_search"
        if uses_sparql:
            params = dict(plan.params)
            api_url = settings.riss_api_url or RISS_DEFAULT_SPARQL_URL
        else:
            if not settings.riss_api_url:
                plan.notes.append("RISS live collection is enabled but RISS_API_URL is not configured.")
                return self._build_collection(plan, [], backend="live_misconfigured", total_hits=0)
            params = dict(plan.params)
            api_url = settings.riss_api_url
            if settings.riss_api_key and settings.riss_api_key_param:
                params[settings.riss_api_key_param] = settings.riss_api_key
            if settings.riss_document_type_param:
                if request.include_theses and not request.include_journal_articles:
                    params[settings.riss_document_type_param] = settings.riss_thesis_value
                elif request.include_journal_articles and not request.include_theses:
                    params[settings.riss_document_type_param] = settings.riss_journal_value

        try:
            payload = self._fetch_text(api_url, params)
        except Exception:
            plan.notes.append("RISS live request failed, so no stub fallback was used for this run.")
            return self._build_collection(plan, [], backend="live_failed", total_hits=0)

        if uses_sparql or settings.riss_response_format.lower() == "xml":
            records, total_hits = self._parse_xml_records(payload)
        else:
            records, total_hits = self._parse_json(payload)

        candidates = [self._candidate_from_mapping(item, request, plan) for item in records]
        filtered = [item for item in candidates if self._matches_request(item, request)]
        return self._build_collection(plan, filtered, backend="live", total_hits=total_hits or len(filtered))

    def _collect_web_search(self, request: SearchRequest, plan: SourceSearchPlan) -> SourceCollectionResult:
        api_url = settings.riss_api_url or RISS_DEFAULT_WEB_URL
        if "data.riss.kr/sparql" in api_url:
            api_url = RISS_DEFAULT_WEB_URL

        collections = self._selected_web_collections(request)
        if not collections:
            return self._build_collection(plan, [], backend="live", total_hits=0)

        total_hits = 0
        page_requests = 0
        candidates: list[CandidateRecord] = []
        seen_keys: set[tuple[str, str]] = set()
        collection_summaries: list[str] = []

        try:
            for collection_name in collections:
                page_candidates, collection_total_hits, collection_pages = self._collect_web_collection(
                    request,
                    plan,
                    api_url,
                    collection_name,
                )
                total_hits += collection_total_hits
                page_requests += collection_pages
                collection_summaries.append(
                    f"{collection_name}: {collection_total_hits} hit(s), {collection_pages} page(s)"
                )
                for candidate in page_candidates:
                    key = (collection_name, candidate.source_record_id)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    candidates.append(candidate)
        except Exception:
            plan.notes.append("RISS live request failed, so no stub fallback was used for this run.")
            return self._build_collection(plan, [], backend="live_failed", total_hits=0)

        plan.notes.append("RISS web collections collected: " + ", ".join(collection_summaries))
        plan.notes.append(f"Total RISS web page requests: {page_requests}.")
        filtered = [item for item in candidates if self._matches_request(item, request)]
        return self._build_collection(plan, filtered, backend="live", total_hits=total_hits)

    def _selected_web_collections(self, request: SearchRequest) -> list[str]:
        collections: list[str] = []
        if request.include_theses and settings.riss_thesis_collection:
            collections.append(settings.riss_thesis_collection)
        if request.include_journal_articles and settings.riss_journal_collection:
            collections.append(settings.riss_journal_collection)
        deduped: list[str] = []
        for collection_name in collections:
            if collection_name and collection_name not in deduped:
                deduped.append(collection_name)
        return deduped

    def _collect_web_collection(
        self,
        request: SearchRequest,
        plan: SourceSearchPlan,
        api_url: str,
        collection_name: str,
    ) -> tuple[list[CandidateRecord], int, int]:
        base_params = dict(plan.params)
        base_params["colName"] = collection_name
        page_scale = self._parse_int(base_params.get("pageScale")) or settings.riss_web_page_scale or 100

        total_hits: int | None = None
        page_requests = 0
        offset = 0
        candidates: list[CandidateRecord] = []
        seen_ids: set[str] = set()

        while True:
            params = dict(base_params)
            params["iStartCount"] = str(offset)
            params["pageNumber"] = str((offset // page_scale) + 1)
            payload = self._fetch_text(api_url, params)
            page_requests += 1

            page_total_hits = self._extract_total_hits_from_web_html(payload)
            if page_total_hits is not None:
                total_hits = max(total_hits or 0, page_total_hits)

            page_items = self._parse_web_records(payload)
            if not page_items:
                if total_hits is None:
                    total_hits = 0
                break

            for item in page_items:
                candidate = self._candidate_from_web_item(item, request, plan, collection_name)
                if candidate.source_record_id in seen_ids:
                    continue
                seen_ids.add(candidate.source_record_id)
                candidates.append(candidate)

            if total_hits is not None and len(candidates) >= total_hits:
                break
            if total_hits is not None and offset + page_scale >= total_hits:
                break
            if len(page_items) < page_scale and total_hits is None:
                total_hits = len(candidates)
                break

            offset += page_scale

        return candidates, total_hits or len(candidates), page_requests

    def _fetch_text(self, api_url: str, params: dict[str, str]) -> str:
        query_string = urllib.parse.urlencode(params)
        separator = "&" if "?" in api_url else "?"
        request = urllib.request.Request(
            f"{api_url}{separator}{query_string}",
            headers={
                "User-Agent": RISS_WEB_USER_AGENT,
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")

    def _extract_total_hits_from_web_html(self, payload: str) -> int | None:
        for pattern in [RISS_WEB_TOTAL_HITS_RE, RISS_WEB_SECTION_COUNT_RE]:
            match = pattern.search(payload)
            if match:
                parsed = self._parse_int(match.group(1))
                if parsed is not None:
                    return parsed
        return None

    def _parse_web_records(self, payload: str) -> list[dict]:
        items: list[dict] = []
        for segment in payload.split('name="p_control_no"')[1:]:
            block = 'name="p_control_no"' + segment
            control_match = re.search(r'value="([^"]+)"', block)
            title_match = RISS_WEB_TITLE_RE.search(block)
            etc_match = RISS_WEB_ETC_RE.search(block)
            if not control_match or not title_match or not etc_match:
                continue

            etc_entries: list[dict[str, str]] = []
            for span_match in RISS_WEB_SPAN_RE.finditer(etc_match.group(1)):
                class_name = span_match.group(1) or ""
                role = "value"
                if "writer" in class_name.split():
                    role = "writer"
                elif "assigned" in class_name.split():
                    role = "assigned"
                text = _clean_riss_html_text(span_match.group(2))
                if text:
                    etc_entries.append({"role": role, "text": text})

            title = _clean_riss_html_text(title_match.group(2))
            if not title:
                continue

            abstract_match = RISS_WEB_ABSTRACT_RE.search(block)
            items.append(
                {
                    "p_control_no": control_match.group(1),
                    "detail_href": title_match.group(1),
                    "title": title,
                    "etc_entries": etc_entries,
                    "abstract": _clean_riss_html_text(abstract_match.group(1)) if abstract_match else "",
                }
            )
        return items

    def _candidate_from_web_item(
        self,
        item: dict,
        request: SearchRequest,
        plan: SourceSearchPlan,
        collection_name: str,
    ) -> CandidateRecord:
        etc_entries = item.get("etc_entries") or []
        writer = next((entry["text"] for entry in etc_entries if entry.get("role") == "writer"), "")
        assigned = next((entry["text"] for entry in etc_entries if entry.get("role") == "assigned"), "")
        generic_values = [entry["text"] for entry in etc_entries if entry.get("role") == "value" and entry.get("text")]

        year = 0
        extra_values: list[str] = []
        for value in generic_values:
            if not year and re.match(r"^\d{4}$", value):
                year = self._parse_year(value)
            else:
                extra_values.append(value)

        detail_href = item.get("detail_href") or ""
        detail_url = urllib.parse.urljoin(RISS_BASE_URL, detail_href) if detail_href else None
        detail_params = urllib.parse.parse_qs(urllib.parse.urlparse(detail_url or "").query)

        control_value = str(item.get("p_control_no") or "")
        control_parts = control_value.split("|", 1) if control_value else []
        record_id = (
            control_parts[0]
            if control_parts and control_parts[0]
            else (detail_params.get("control_no") or [generate_id("riss")])[0]
        )
        p_mat_type = (
            control_parts[1]
            if len(control_parts) > 1 and control_parts[1]
            else (detail_params.get("p_mat_type") or [""])[0]
        )

        document_type = self._web_collection_document_type(collection_name)
        journal_title = extra_values[0] if extra_values else ""
        journal_or_school = assigned or "RISS"
        if document_type == "journal_article":
            journal_or_school = journal_title or assigned or "RISS"

        return CandidateRecord(
            id=generate_id("cand"),
            search_request_id=request.id,
            source=self.source_name,
            source_record_id=str(record_id),
            title=item.get("title") or f"{request.query_text} related RISS record",
            authors=self._split_values(writer, default=["unknown"]),
            year=year,
            journal_or_school=journal_or_school,
            abstract=item.get("abstract") or "",
            keywords=plan.terms or [request.query_text],
            doi=None,
            url=detail_url,
            document_type=document_type,
            language="ko",
            raw_payload={
                "source": "live",
                "origin": "riss_web",
                "collection": collection_name,
                "item": item,
                "query_plan": self._plan_metadata(plan),
                "p_mat_type": p_mat_type,
                "publisher": assigned,
                "publication_info": extra_values,
            },
            status="collected",
        )

    def _web_collection_document_type(self, collection_name: str) -> str:
        return "thesis" if collection_name == settings.riss_thesis_collection else "journal_article"

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
            or item.get("authortitle")
            or item.get("authorlabel")
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

        keywords = item.get("keywords") or item.get("keyword") or item.get("subjectlabel") or item.get("subject") or request.query_text
        keyword_list = self._split_values(keywords, default=[request.query_text])
        abstract = item.get("abstract") or item.get("description") or item.get("dcterms:description") or item.get("dc:description") or ""
        record_id = (
            item.get("id")
            or item.get("identifier")
            or item.get("uri")
            or item.get("URI")
            or item.get("link")
            or generate_id("riss")
        )
        location = (
            item.get("school")
            or item.get("degreeGrantor")
            or item.get("publisher")
            or item.get("publishertitle")
            or item.get("publisherlabel")
            or item.get("journal")
            or item.get("journalTitle")
            or item.get("journaltitle")
            or item.get("isPartOf")
            or "RISS"
        )
        doi = item.get("doi")
        url = item.get("url") or item.get("link") or item.get("uri") or item.get("URI")
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
                "recordtype",
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
        if not settings.riss_live_enabled:
            return self.stub.collect(request)

        live_result = self.live.collect(request)
        if live_result is not None:
            return live_result
        return self.stub.collect(request)

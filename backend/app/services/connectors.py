from collections.abc import Iterable

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

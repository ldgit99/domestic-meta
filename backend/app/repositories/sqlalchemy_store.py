from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import TITLE_ABSTRACT_STAGE
from app.core.utils import generate_id, now_iso
from app.models.domain import (
    CandidateRecord,
    EligibilityDecision,
    ExtractionResult,
    FullTextArtifact,
    PipelineEvent,
    PrismaCounts,
    SearchRequest,
)
from app.repositories.db_models import (
    Base,
    CandidateRecordModel,
    EligibilityDecisionModel,
    ExtractionResultModel,
    FullTextArtifactModel,
    PipelineEventModel,
    PrismaCountsModel,
    SearchRequestModel,
)
from app.schemas.candidate import DecisionCreate, FullTextArtifactCreate
from app.schemas.search import SearchRequestCreate


class SQLAlchemyStore:
    def __init__(self, database_url: str, auto_create_tables: bool = True) -> None:
        self.database_url = self._normalize_url(database_url)
        self.engine = self._create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, class_=Session)
        if auto_create_tables:
            Base.metadata.create_all(self.engine)

    def _normalize_url(self, database_url: str) -> str:
        if database_url.startswith("sqlite:///"):
            path = database_url.removeprefix("sqlite:///")
            if path not in {":memory:", ""}:
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        return database_url

    def _create_engine(self, database_url: str):
        kwargs = {"future": True}
        if database_url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            if ":memory:" in database_url:
                kwargs["poolclass"] = StaticPool
        return create_engine(database_url, **kwargs)

    @contextmanager
    def _session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _to_search_request(self, model: SearchRequestModel) -> SearchRequest:
        return SearchRequest(
            id=model.id,
            query_text=model.query_text,
            expanded_keywords=model.expanded_keywords or [],
            year_from=model.year_from,
            year_to=model.year_to,
            include_theses=model.include_theses,
            include_journal_articles=model.include_journal_articles,
            inclusion_rules=model.inclusion_rules or [],
            exclusion_rules=model.exclusion_rules or [],
            status=model.status,
            created_at=model.created_at,
        )

    def _to_candidate(self, model: CandidateRecordModel) -> CandidateRecord:
        return CandidateRecord(
            id=model.id,
            search_request_id=model.search_request_id,
            source=model.source,
            source_record_id=model.source_record_id,
            title=model.title,
            authors=model.authors or [],
            year=model.year,
            journal_or_school=model.journal_or_school,
            abstract=model.abstract,
            keywords=model.keywords or [],
            doi=model.doi,
            url=model.url,
            document_type=model.document_type,
            language=model.language,
            raw_payload=model.raw_payload or {},
            status=model.status,
            duplicate_group_id=model.duplicate_group_id,
            canonical_record_id=model.canonical_record_id,
        )

    def _to_decision(self, model: EligibilityDecisionModel) -> EligibilityDecision:
        return EligibilityDecision(
            id=model.id,
            candidate_record_id=model.candidate_record_id,
            stage=model.stage,
            decision=model.decision,
            reason_code=model.reason_code,
            reason_text=model.reason_text,
            confidence=model.confidence,
            reviewed_by=model.reviewed_by,
            created_at=model.created_at,
        )

    def _to_prisma(self, model: PrismaCountsModel) -> PrismaCounts:
        return PrismaCounts(
            id=model.id,
            search_request_id=model.search_request_id,
            identified_records=model.identified_records,
            duplicate_records_removed=model.duplicate_records_removed,
            records_screened=model.records_screened,
            records_excluded=model.records_excluded,
            reports_sought_for_retrieval=model.reports_sought_for_retrieval,
            reports_not_retrieved=model.reports_not_retrieved,
            reports_assessed_for_eligibility=model.reports_assessed_for_eligibility,
            reports_excluded_with_reasons_json=model.reports_excluded_with_reasons_json or {},
            studies_included_in_review=model.studies_included_in_review,
        )

    def _to_artifact(self, model: FullTextArtifactModel) -> FullTextArtifact:
        return FullTextArtifact(
            id=model.id,
            candidate_record_id=model.candidate_record_id,
            file_name=model.file_name,
            source_url=model.source_url,
            mime_type=model.mime_type,
            text_content=model.text_content,
            text_extraction_status=model.text_extraction_status,
            created_at=model.created_at,
            stored_path=model.stored_path,
        )

    def _to_extraction(self, model: ExtractionResultModel) -> ExtractionResult:
        return ExtractionResult(
            id=model.id,
            candidate_id=model.candidate_id,
            status=model.status,
            message=model.message,
            fields_json=model.fields_json or {},
            model_name=model.model_name,
            raw_response=model.raw_response or {},
            created_at=model.created_at,
        )

    def _to_event(self, model: PipelineEventModel) -> PipelineEvent:
        return PipelineEvent(
            id=model.id,
            search_request_id=model.search_request_id,
            event_type=model.event_type,
            status=model.status,
            message=model.message,
            stage=model.stage,
            candidate_id=model.candidate_id,
            metadata_json=model.metadata_json or {},
            created_at=model.created_at,
        )

    def list_search_requests(self) -> list[SearchRequest]:
        with self._session() as session:
            models = session.scalars(
                select(SearchRequestModel).order_by(SearchRequestModel.created_at.desc())
            ).all()
            return [self._to_search_request(model) for model in models]

    def create_search_request(self, payload: SearchRequestCreate) -> SearchRequest:
        with self._session() as session:
            item = SearchRequestModel(
                id=generate_id("search"),
                query_text=payload.query_text,
                expanded_keywords=payload.expanded_keywords,
                year_from=payload.year_from,
                year_to=payload.year_to,
                include_theses=payload.include_theses,
                include_journal_articles=payload.include_journal_articles,
                inclusion_rules=payload.inclusion_rules,
                exclusion_rules=payload.exclusion_rules,
                status="created",
                created_at=now_iso(),
            )
            session.add(item)
            session.add(
                PrismaCountsModel(
                    id=generate_id("prisma"),
                    search_request_id=item.id,
                )
            )
            session.flush()
            return self._to_search_request(item)

    def reset_search_results(self, search_request_id: str) -> None:
        with self._session() as session:
            candidate_ids = session.scalars(
                select(CandidateRecordModel.id).where(CandidateRecordModel.search_request_id == search_request_id)
            ).all()

            if candidate_ids:
                session.execute(
                    delete(EligibilityDecisionModel).where(
                        EligibilityDecisionModel.candidate_record_id.in_(candidate_ids)
                    )
                )
                session.execute(
                    delete(FullTextArtifactModel).where(
                        FullTextArtifactModel.candidate_record_id.in_(candidate_ids)
                    )
                )
                session.execute(
                    delete(ExtractionResultModel).where(ExtractionResultModel.candidate_id.in_(candidate_ids))
                )
                session.execute(delete(CandidateRecordModel).where(CandidateRecordModel.id.in_(candidate_ids)))

            prisma = session.scalar(
                select(PrismaCountsModel).where(PrismaCountsModel.search_request_id == search_request_id)
            )
            if prisma is None:
                prisma = PrismaCountsModel(
                    id=generate_id("prisma"),
                    search_request_id=search_request_id,
                )
                session.add(prisma)
            else:
                prisma.identified_records = 0
                prisma.duplicate_records_removed = 0
                prisma.records_screened = 0
                prisma.records_excluded = 0
                prisma.reports_sought_for_retrieval = 0
                prisma.reports_not_retrieved = 0
                prisma.reports_assessed_for_eligibility = 0
                prisma.reports_excluded_with_reasons_json = {}
                prisma.studies_included_in_review = 0

    def get_search_request(self, search_request_id: str) -> SearchRequest | None:
        with self._session() as session:
            model = session.get(SearchRequestModel, search_request_id)
            return self._to_search_request(model) if model else None

    def update_search_request_status(self, search_request_id: str, status: str) -> None:
        with self._session() as session:
            model = session.get(SearchRequestModel, search_request_id)
            if model is not None:
                model.status = status

    def add_candidates(self, items: list[CandidateRecord]) -> None:
        with self._session() as session:
            for item in items:
                session.merge(
                    CandidateRecordModel(
                        id=item.id,
                        search_request_id=item.search_request_id,
                        source=item.source,
                        source_record_id=item.source_record_id,
                        title=item.title,
                        authors=item.authors,
                        year=item.year,
                        journal_or_school=item.journal_or_school,
                        abstract=item.abstract,
                        keywords=item.keywords,
                        doi=item.doi,
                        url=item.url,
                        document_type=item.document_type,
                        language=item.language,
                        raw_payload=item.raw_payload,
                        status=item.status,
                        duplicate_group_id=item.duplicate_group_id,
                        canonical_record_id=item.canonical_record_id,
                    )
                )

    def list_candidates(self, search_request_id: str) -> list[CandidateRecord]:
        with self._session() as session:
            models = session.scalars(
                select(CandidateRecordModel).where(CandidateRecordModel.search_request_id == search_request_id)
            ).all()
            return [self._to_candidate(model) for model in models]

    def get_candidate(self, candidate_id: str) -> CandidateRecord | None:
        with self._session() as session:
            model = session.get(CandidateRecordModel, candidate_id)
            return self._to_candidate(model) if model else None

    def update_candidate(self, item: CandidateRecord) -> None:
        with self._session() as session:
            model = session.get(CandidateRecordModel, item.id)
            if model is None:
                return
            model.search_request_id = item.search_request_id
            model.source = item.source
            model.source_record_id = item.source_record_id
            model.title = item.title
            model.authors = item.authors
            model.year = item.year
            model.journal_or_school = item.journal_or_school
            model.abstract = item.abstract
            model.keywords = item.keywords
            model.doi = item.doi
            model.url = item.url
            model.document_type = item.document_type
            model.language = item.language
            model.raw_payload = item.raw_payload
            model.status = item.status
            model.duplicate_group_id = item.duplicate_group_id
            model.canonical_record_id = item.canonical_record_id

    def save_decision(self, item: EligibilityDecision) -> EligibilityDecision:
        with self._session() as session:
            session.merge(
                EligibilityDecisionModel(
                    id=item.id,
                    candidate_record_id=item.candidate_record_id,
                    stage=item.stage,
                    decision=item.decision,
                    reason_code=item.reason_code,
                    reason_text=item.reason_text,
                    confidence=item.confidence,
                    reviewed_by=item.reviewed_by,
                    created_at=item.created_at,
                )
            )
        return item

    def create_decision(self, candidate_id: str, payload: DecisionCreate) -> EligibilityDecision | None:
        with self._session() as session:
            candidate = session.get(CandidateRecordModel, candidate_id)
            if candidate is None:
                return None

            item = EligibilityDecision(
                id=generate_id("decision"),
                candidate_record_id=candidate_id,
                stage=payload.stage,
                decision=payload.decision,
                reason_code=payload.reason_code,
                reason_text=payload.reason_text,
                confidence=payload.confidence,
                reviewed_by=payload.reviewed_by,
                created_at=now_iso(),
            )
            session.add(
                EligibilityDecisionModel(
                    id=item.id,
                    candidate_record_id=item.candidate_record_id,
                    stage=item.stage,
                    decision=item.decision,
                    reason_code=item.reason_code,
                    reason_text=item.reason_text,
                    confidence=item.confidence,
                    reviewed_by=item.reviewed_by,
                    created_at=item.created_at,
                )
            )
            if payload.stage == TITLE_ABSTRACT_STAGE:
                candidate.status = "screened_title_abstract"
            return item

    def list_decisions_for_search(self, search_request_id: str) -> list[EligibilityDecision]:
        with self._session() as session:
            candidate_ids = session.scalars(
                select(CandidateRecordModel.id).where(CandidateRecordModel.search_request_id == search_request_id)
            ).all()
            if not candidate_ids:
                return []
            models = session.scalars(
                select(EligibilityDecisionModel).where(
                    EligibilityDecisionModel.candidate_record_id.in_(candidate_ids)
                )
            ).all()
            return [self._to_decision(model) for model in models]

    def get_prisma_counts(self, search_request_id: str) -> PrismaCounts | None:
        with self._session() as session:
            model = session.scalar(
                select(PrismaCountsModel).where(PrismaCountsModel.search_request_id == search_request_id)
            )
            return self._to_prisma(model) if model else None

    def update_prisma_counts(self, item: PrismaCounts) -> None:
        with self._session() as session:
            model = session.scalar(
                select(PrismaCountsModel).where(PrismaCountsModel.search_request_id == item.search_request_id)
            )
            if model is None:
                session.add(
                    PrismaCountsModel(
                        id=item.id,
                        search_request_id=item.search_request_id,
                        identified_records=item.identified_records,
                        duplicate_records_removed=item.duplicate_records_removed,
                        records_screened=item.records_screened,
                        records_excluded=item.records_excluded,
                        reports_sought_for_retrieval=item.reports_sought_for_retrieval,
                        reports_not_retrieved=item.reports_not_retrieved,
                        reports_assessed_for_eligibility=item.reports_assessed_for_eligibility,
                        reports_excluded_with_reasons_json=item.reports_excluded_with_reasons_json,
                        studies_included_in_review=item.studies_included_in_review,
                    )
                )
                return

            model.identified_records = item.identified_records
            model.duplicate_records_removed = item.duplicate_records_removed
            model.records_screened = item.records_screened
            model.records_excluded = item.records_excluded
            model.reports_sought_for_retrieval = item.reports_sought_for_retrieval
            model.reports_not_retrieved = item.reports_not_retrieved
            model.reports_assessed_for_eligibility = item.reports_assessed_for_eligibility
            model.reports_excluded_with_reasons_json = item.reports_excluded_with_reasons_json
            model.studies_included_in_review = item.studies_included_in_review

    def log_event(
        self,
        search_request_id: str,
        event_type: str,
        message: str,
        *,
        stage: str | None = None,
        status: str = "info",
        candidate_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> PipelineEvent:
        item = PipelineEvent(
            id=generate_id("event"),
            search_request_id=search_request_id,
            event_type=event_type,
            status=status,
            message=message,
            stage=stage,
            candidate_id=candidate_id,
            metadata_json=metadata_json or {},
            created_at=now_iso(),
        )
        with self._session() as session:
            session.add(
                PipelineEventModel(
                    id=item.id,
                    search_request_id=item.search_request_id,
                    event_type=item.event_type,
                    status=item.status,
                    message=item.message,
                    stage=item.stage,
                    candidate_id=item.candidate_id,
                    metadata_json=item.metadata_json,
                    created_at=item.created_at,
                )
            )
        return item

    def list_events(self, search_request_id: str) -> list[PipelineEvent]:
        with self._session() as session:
            models = session.scalars(
                select(PipelineEventModel)
                .where(PipelineEventModel.search_request_id == search_request_id)
                .order_by(PipelineEventModel.created_at.desc(), PipelineEventModel.id.desc())
            ).all()
            return [self._to_event(model) for model in models]

    def create_full_text_artifact(
        self,
        candidate_id: str,
        payload: FullTextArtifactCreate,
    ) -> FullTextArtifact | None:
        with self._session() as session:
            if session.get(CandidateRecordModel, candidate_id) is None:
                return None

            existing = session.scalar(
                select(FullTextArtifactModel).where(FullTextArtifactModel.candidate_record_id == candidate_id)
            )
            item = FullTextArtifact(
                id=existing.id if existing else generate_id("artifact"),
                candidate_record_id=candidate_id,
                file_name=payload.file_name,
                source_url=payload.source_url,
                mime_type=payload.mime_type,
                text_content=payload.text_content,
                text_extraction_status=payload.text_extraction_status
                or ("available" if payload.text_content.strip() else "pending"),
                created_at=existing.created_at if existing else now_iso(),
                stored_path=payload.stored_path,
            )

            if existing is None:
                session.add(
                    FullTextArtifactModel(
                        id=item.id,
                        candidate_record_id=item.candidate_record_id,
                        file_name=item.file_name,
                        source_url=item.source_url,
                        mime_type=item.mime_type,
                        text_content=item.text_content,
                        text_extraction_status=item.text_extraction_status,
                        created_at=item.created_at,
                        stored_path=item.stored_path,
                    )
                )
            else:
                existing.file_name = item.file_name
                existing.source_url = item.source_url
                existing.mime_type = item.mime_type
                existing.text_content = item.text_content
                existing.text_extraction_status = item.text_extraction_status
                existing.stored_path = item.stored_path
            return item

    def get_full_text_artifact(self, candidate_id: str) -> FullTextArtifact | None:
        with self._session() as session:
            model = session.scalar(
                select(FullTextArtifactModel).where(FullTextArtifactModel.candidate_record_id == candidate_id)
            )
            return self._to_artifact(model) if model else None

    def save_extraction_result(self, item: ExtractionResult) -> ExtractionResult:
        with self._session() as session:
            existing = session.scalar(
                select(ExtractionResultModel).where(ExtractionResultModel.candidate_id == item.candidate_id)
            )
            if existing is None:
                session.add(
                    ExtractionResultModel(
                        id=item.id or generate_id("extract"),
                        candidate_id=item.candidate_id,
                        status=item.status,
                        message=item.message,
                        fields_json=item.fields_json,
                        model_name=item.model_name,
                        raw_response=item.raw_response,
                        created_at=item.created_at,
                    )
                )
            else:
                existing.id = item.id or existing.id
                existing.status = item.status
                existing.message = item.message
                existing.fields_json = item.fields_json
                existing.model_name = item.model_name
                existing.raw_response = item.raw_response
                existing.created_at = item.created_at
        return item

    def get_extraction_result(self, candidate_id: str) -> ExtractionResult | None:
        with self._session() as session:
            model = session.scalar(
                select(ExtractionResultModel).where(ExtractionResultModel.candidate_id == candidate_id)
            )
            return self._to_extraction(model) if model else None

    def list_extraction_results_for_search(self, search_request_id: str) -> list[ExtractionResult]:
        with self._session() as session:
            candidate_ids = session.scalars(
                select(CandidateRecordModel.id).where(CandidateRecordModel.search_request_id == search_request_id)
            ).all()
            if not candidate_ids:
                return []
            models = session.scalars(
                select(ExtractionResultModel).where(ExtractionResultModel.candidate_id.in_(candidate_ids))
            ).all()
            return [self._to_extraction(model) for model in models]

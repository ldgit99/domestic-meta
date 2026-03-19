DEFAULT_YEAR_FROM = 2010
DEFAULT_YEAR_TO = 2026

TITLE_ABSTRACT_STAGE = "title_abstract"
FULL_TEXT_STAGE = "full_text"

SOURCE_KCI = "kci"
SOURCE_RISS = "riss"

DECISION_INCLUDE = "include"
DECISION_EXCLUDE = "exclude"
DECISION_MAYBE = "maybe"
DECISION_REVIEW = "needs_human_review"

PRISMA_REASON_CODES = {
    "not_education",
    "not_quantitative",
    "insufficient_statistics",
    "no_relevant_outcome",
    "wrong_population",
    "wrong_intervention_or_predictor",
    "wrong_comparison",
    "duplicate_publication",
    "full_text_unavailable",
    "conference_or_non_article",
    "outside_date_range",
}

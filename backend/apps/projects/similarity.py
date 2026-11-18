import logging
import re
import threading
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    ProjectTopic,
    ProjectTopicRevision,
    ProjectTopicSimilarity,
    SimilarityAnalysisStatus,
)

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
ALGORITHM_VERSION = "hybrid-v1"
EMBEDDING_DIMENSION = 384
SIMILARITY_THRESHOLD = 0.62
MATCHED_SECTION_THRESHOLD = 0.50
SEMANTIC_WEIGHT = 0.70
LEXICAL_WEIGHT = 0.30
BATCH_SIZE = 32

FIELD_WEIGHTS = {
    "title": 0.25,
    "abstract": 0.20,
    "problem_statement": 0.25,
    "research_objectives": 0.20,
    "keywords": 0.10,
}

FIELD_LABELS = {
    "title": "Project title",
    "abstract": "Abstract",
    "problem_statement": "Problem statement",
    "research_objectives": "Research objectives",
    "keywords": "Keywords",
}

STOP_WORDS = frozenset(
    (
        "a an and are as at be by for from in into is it of on or that the their this to was were will with "
        "system design implementation development web based application using study project management"
    ).split()
)
TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)

_model = None
_model_lock = threading.Lock()
_analysis_lock = threading.Lock()


def get_embedding_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from fastembed import TextEmbedding

                cache_dir = Path(settings.BASE_DIR) / ".model_cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                _model = TextEmbedding(
                    model_name=MODEL_NAME,
                    cache_dir=str(cache_dir),
                    threads=1,
                    cuda=False,
                )
    return _model


def tokenize_keywords(text):
    return [
        token
        for token in TOKEN_PATTERN.findall(str(text).casefold())
        if len(token) > 1 and token not in STOP_WORDS
    ]


def _jaccard_similarity(left, right):
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def lexical_similarity(left_text, right_text):
    left_tokens = tokenize_keywords(left_text)
    right_tokens = tokenize_keywords(right_text)
    token_score = _jaccard_similarity(set(left_tokens), set(right_tokens))

    left_bigrams = set(zip(left_tokens, left_tokens[1:]))
    right_bigrams = set(zip(right_tokens, right_tokens[1:]))
    if not left_bigrams or not right_bigrams:
        return token_score

    bigram_score = _jaccard_similarity(left_bigrams, right_bigrams)
    return (0.75 * token_score) + (0.25 * bigram_score)


def cosine_similarity(left_vector, right_vector):
    if not left_vector or not right_vector or len(left_vector) != len(right_vector):
        return 0.0

    dot_product = sum(left * right for left, right in zip(left_vector, right_vector))
    left_norm = sum(value * value for value in left_vector) ** 0.5
    right_norm = sum(value * value for value in right_vector) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return max(0.0, min(1.0, dot_product / (left_norm * right_norm)))


def hybrid_field_similarity(left_text, right_text, left_vector, right_vector):
    semantic_score = cosine_similarity(left_vector, right_vector)
    keyword_score = lexical_similarity(left_text, right_text)
    return (SEMANTIC_WEIGHT * semantic_score) + (LEXICAL_WEIGHT * keyword_score)


def _revision_texts(revision):
    return {
        "title": revision.title,
        "abstract": revision.abstract,
        "problem_statement": revision.problem_statement,
        "research_objectives": revision.research_objectives,
        "keywords": " ".join(revision.keywords or []),
    }


def _valid_embedding_set(embeddings):
    return (
        isinstance(embeddings, dict)
        and all(
            isinstance(embeddings.get(field), list)
            and len(embeddings[field]) == EMBEDDING_DIMENSION
            for field in FIELD_WEIGHTS
        )
    )


def _serialise_vector(vector):
    values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
    if len(values) != EMBEDDING_DIMENSION:
        raise ValueError("The semantic model returned an unexpected embedding size.")
    return [float(value) for value in values]


def _ensure_revision_embeddings(revisions, model):
    missing_revisions = [
        revision
        for revision in revisions
        if revision.similarity_model_name != MODEL_NAME
        or not _valid_embedding_set(revision.similarity_embeddings)
    ]
    if not missing_revisions:
        return

    texts = []
    for revision in missing_revisions:
        texts.extend(_revision_texts(revision)[field] for field in FIELD_WEIGHTS)

    vectors = list(model.embed(texts, batch_size=BATCH_SIZE))
    expected_count = len(missing_revisions) * len(FIELD_WEIGHTS)
    if len(vectors) != expected_count:
        raise ValueError("The semantic model returned an incomplete embedding batch.")

    for index, revision in enumerate(missing_revisions):
        start = index * len(FIELD_WEIGHTS)
        revision.similarity_embeddings = {
            field: _serialise_vector(vectors[start + offset])
            for offset, field in enumerate(FIELD_WEIGHTS)
        }
        revision.similarity_model_name = MODEL_NAME

    with transaction.atomic():
        ProjectTopicRevision.objects.bulk_update(
            missing_revisions,
            ["similarity_embeddings", "similarity_model_name"],
            batch_size=50,
        )


def _latest_historical_revisions(source_revision):
    source_user_id = source_revision.topic.student_enrollment.user_id
    revisions = (
        ProjectTopicRevision.objects.select_related(
            "topic",
            "topic__student_enrollment",
            "topic__student_enrollment__session",
        )
        .exclude(topic__student_enrollment__user_id=source_user_id)
        .order_by("topic_id", "-revision_number")
    )

    latest_by_topic = {}
    for revision in revisions:
        if revision.topic_id not in latest_by_topic:
            latest_by_topic[revision.topic_id] = revision
    return list(latest_by_topic.values())


def _score_revision_pair(source_revision, matched_revision):
    source_texts = _revision_texts(source_revision)
    matched_texts = _revision_texts(matched_revision)
    field_scores = {}

    for field in FIELD_WEIGHTS:
        field_scores[field] = round(
            hybrid_field_similarity(
                source_texts[field],
                matched_texts[field],
                source_revision.similarity_embeddings[field],
                matched_revision.similarity_embeddings[field],
            ),
            6,
        )

    overall_score = sum(
        field_scores[field] * weight
        for field, weight in FIELD_WEIGHTS.items()
    )
    return round(overall_score, 6), field_scores


def _analyse_topic_similarity(topic_id, force=False):
    topic = ProjectTopic.objects.select_related(
        "student_enrollment__user",
        "student_enrollment__session",
    ).get(pk=topic_id)
    source_revision = topic.revisions.order_by("-revision_number").first()
    if source_revision is None:
        return None

    if source_revision.similarity_status == SimilarityAnalysisStatus.COMPLETED and not force:
        return source_revision

    try:
        model = get_embedding_model()
        historical_revisions = _latest_historical_revisions(source_revision)
        revisions_to_embed = [source_revision, *historical_revisions]
        _ensure_revision_embeddings(revisions_to_embed, model)

        matches = []
        for historical_revision in historical_revisions:
            overall_score, field_scores = _score_revision_pair(
                source_revision,
                historical_revision,
            )
            if overall_score >= SIMILARITY_THRESHOLD:
                matches.append(
                    ProjectTopicSimilarity(
                        source_revision=source_revision,
                        matched_revision=historical_revision,
                        overall_score=overall_score,
                        field_scores=field_scores,
                        threshold=SIMILARITY_THRESHOLD,
                        model_name=MODEL_NAME,
                        algorithm_version=ALGORITHM_VERSION,
                    )
                )

        with transaction.atomic():
            ProjectTopicSimilarity.objects.filter(source_revision=source_revision).delete()
            ProjectTopicSimilarity.objects.bulk_create(matches, batch_size=50)
            source_revision.similarity_status = SimilarityAnalysisStatus.COMPLETED
            source_revision.similarity_analyzed_at = timezone.now()
            source_revision.save(
                update_fields=["similarity_status", "similarity_analyzed_at"]
            )
    except Exception:
        logger.exception("Project topic similarity analysis failed for topic %s", topic_id)
        ProjectTopicSimilarity.objects.filter(source_revision=source_revision).delete()
        source_revision.similarity_status = SimilarityAnalysisStatus.UNAVAILABLE
        source_revision.similarity_analyzed_at = None
        source_revision.save(
            update_fields=["similarity_status", "similarity_analyzed_at"]
        )

    return source_revision


def analyse_topic_similarity(topic_id, force=False):
    with _analysis_lock:
        return _analyse_topic_similarity(topic_id, force=force)

"""RAG quality evaluation metrics and utilities."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class GoldenExample:
    """A single golden Q&A example for evaluation."""

    id: str
    question: str
    expected_sources: list[str]
    expected_keywords: list[str]
    category: str


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality."""

    recall_at_k: float  # Fraction of expected sources found in top-k
    precision_at_k: float  # Fraction of retrieved sources that are expected
    source_found: bool  # Whether at least one expected source was found
    retrieved_sources: list[str]  # Sources actually retrieved
    expected_sources: list[str]  # Sources expected


@dataclass
class AnswerMetrics:
    """Metrics for answer quality."""

    keyword_recall: float  # Fraction of expected keywords found in answer
    keywords_found: list[str]  # Keywords that were found
    keywords_missing: list[str]  # Keywords that were not found


@dataclass
class EvaluationResult:
    """Combined evaluation result for a single example."""

    example_id: str
    question: str
    retrieval: RetrievalMetrics
    answer: AnswerMetrics
    passed: bool  # Whether the example passed quality thresholds


@dataclass
class EvaluationSummary:
    """Summary of evaluation across all examples."""

    total_examples: int
    passed_examples: int
    pass_rate: float
    avg_retrieval_recall: float
    avg_keyword_recall: float
    results: list[EvaluationResult] = field(default_factory=list)
    failed_examples: list[str] = field(default_factory=list)


def load_golden_dataset(path: Path) -> list[GoldenExample]:
    """Load golden Q&A examples from JSON file.

    Args:
        path: Path to the golden dataset JSON file.

    Returns:
        List of GoldenExample objects.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with path.open() as f:
        data = json.load(f)

    examples = []
    for item in data.get("examples", []):
        examples.append(
            GoldenExample(
                id=item["id"],
                question=item["question"],
                expected_sources=item["expected_sources"],
                expected_keywords=item["expected_keywords"],
                category=item["category"],
            )
        )

    logger.info(
        "golden_dataset_loaded",
        example_count=len(examples),
        path=str(path),
    )

    return examples


def calculate_retrieval_metrics(
    retrieved_sources: list[str],
    expected_sources: list[str],
) -> RetrievalMetrics:
    """Calculate retrieval quality metrics.

    Args:
        retrieved_sources: Source filenames from retrieved chunks.
        expected_sources: Expected source filenames from golden example.

    Returns:
        RetrievalMetrics with recall and precision scores.
    """
    if not expected_sources:
        return RetrievalMetrics(
            recall_at_k=1.0,
            precision_at_k=1.0 if not retrieved_sources else 0.0,
            source_found=True,
            retrieved_sources=retrieved_sources,
            expected_sources=expected_sources,
        )

    # Calculate recall: what fraction of expected sources were retrieved?
    retrieved_set = set(retrieved_sources)
    expected_set = set(expected_sources)
    found = retrieved_set & expected_set
    recall = len(found) / len(expected_set) if expected_set else 0.0

    # Calculate precision: what fraction of retrieved sources were expected?
    precision = len(found) / len(retrieved_set) if retrieved_set else 0.0

    return RetrievalMetrics(
        recall_at_k=recall,
        precision_at_k=precision,
        source_found=len(found) > 0,
        retrieved_sources=retrieved_sources,
        expected_sources=expected_sources,
    )


def calculate_answer_metrics(
    answer: str,
    expected_keywords: list[str],
) -> AnswerMetrics:
    """Calculate answer quality metrics based on keyword presence.

    Args:
        answer: The generated answer text.
        expected_keywords: Keywords expected to appear in the answer.

    Returns:
        AnswerMetrics with keyword recall score.
    """
    if not expected_keywords:
        return AnswerMetrics(
            keyword_recall=1.0,
            keywords_found=[],
            keywords_missing=[],
        )

    answer_lower = answer.lower()
    found = []
    missing = []

    for keyword in expected_keywords:
        if keyword.lower() in answer_lower:
            found.append(keyword)
        else:
            missing.append(keyword)

    recall = len(found) / len(expected_keywords)

    return AnswerMetrics(
        keyword_recall=recall,
        keywords_found=found,
        keywords_missing=missing,
    )


def assess_example(
    example: GoldenExample,
    retrieved_sources: list[str],
    answer: str,
    *,
    keyword_threshold: float = 0.5,
) -> EvaluationResult:
    """Assess a single golden example.

    Args:
        example: The golden example to evaluate against.
        retrieved_sources: Sources from the retrieved chunks.
        answer: The generated answer.
        keyword_threshold: Minimum keyword recall to pass.

    Returns:
        EvaluationResult with metrics and pass/fail status.
    """
    retrieval = calculate_retrieval_metrics(
        retrieved_sources=retrieved_sources,
        expected_sources=example.expected_sources,
    )

    answer_metrics = calculate_answer_metrics(
        answer=answer,
        expected_keywords=example.expected_keywords,
    )

    # An example passes if:
    # 1. At least one expected source was retrieved, AND
    # 2. Keyword recall meets the threshold
    passed = (
        retrieval.source_found and answer_metrics.keyword_recall >= keyword_threshold
    )

    return EvaluationResult(
        example_id=example.id,
        question=example.question,
        retrieval=retrieval,
        answer=answer_metrics,
        passed=passed,
    )


def summarize_assessment(results: list[EvaluationResult]) -> EvaluationSummary:
    """Summarize assessment results across multiple examples.

    Args:
        results: List of individual evaluation results.

    Returns:
        EvaluationSummary with aggregate metrics.
    """
    if not results:
        return EvaluationSummary(
            total_examples=0,
            passed_examples=0,
            pass_rate=0.0,
            avg_retrieval_recall=0.0,
            avg_keyword_recall=0.0,
            results=[],
            failed_examples=[],
        )

    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    avg_retrieval = sum(r.retrieval.recall_at_k for r in results) / len(results)
    avg_keyword = sum(r.answer.keyword_recall for r in results) / len(results)

    summary = EvaluationSummary(
        total_examples=len(results),
        passed_examples=len(passed),
        pass_rate=len(passed) / len(results),
        avg_retrieval_recall=avg_retrieval,
        avg_keyword_recall=avg_keyword,
        results=results,
        failed_examples=[r.example_id for r in failed],
    )

    logger.info(
        "evaluation_summary",
        total=summary.total_examples,
        passed=summary.passed_examples,
        pass_rate=f"{summary.pass_rate:.1%}",
        avg_retrieval_recall=f"{summary.avg_retrieval_recall:.2f}",
        avg_keyword_recall=f"{summary.avg_keyword_recall:.2f}",
    )

    return summary

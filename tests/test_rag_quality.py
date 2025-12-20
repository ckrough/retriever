"""Tests for RAG quality assessment framework."""

import json
import tempfile
from pathlib import Path

import pytest

from src.modules.rag.quality import (
    AnswerMetrics,
    EvaluationResult,
    GoldenExample,
    RetrievalMetrics,
    assess_example,
    calculate_answer_metrics,
    calculate_retrieval_metrics,
    load_golden_dataset,
    summarize_assessment,
)


class TestLoadGoldenDataset:
    """Tests for loading golden dataset."""

    def test_load_valid_dataset(self) -> None:
        """Should load a valid golden dataset JSON file."""
        dataset = {
            "version": "1.0.0",
            "examples": [
                {
                    "id": "test-001",
                    "question": "What is the policy?",
                    "expected_sources": ["policy.md"],
                    "expected_keywords": ["policy", "rule"],
                    "category": "general",
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(dataset, f)
            temp_path = Path(f.name)

        try:
            examples = load_golden_dataset(temp_path)
            assert len(examples) == 1
            assert examples[0].id == "test-001"
            assert examples[0].question == "What is the policy?"
            assert examples[0].expected_sources == ["policy.md"]
            assert examples[0].expected_keywords == ["policy", "rule"]
        finally:
            temp_path.unlink()

    def test_load_empty_dataset(self) -> None:
        """Should handle empty examples list."""
        dataset = {"version": "1.0.0", "examples": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(dataset, f)
            temp_path = Path(f.name)

        try:
            examples = load_golden_dataset(temp_path)
            assert len(examples) == 0
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file_raises(self) -> None:
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_golden_dataset(Path("/nonexistent/path.json"))


class TestCalculateRetrievalMetrics:
    """Tests for retrieval metrics calculation."""

    def test_perfect_retrieval(self) -> None:
        """Should return 1.0 recall when all sources are found."""
        metrics = calculate_retrieval_metrics(
            retrieved_sources=["doc1.md", "doc2.md"],
            expected_sources=["doc1.md", "doc2.md"],
        )
        assert metrics.recall_at_k == 1.0
        assert metrics.precision_at_k == 1.0
        assert metrics.source_found is True

    def test_partial_retrieval(self) -> None:
        """Should return partial recall when some sources are found."""
        metrics = calculate_retrieval_metrics(
            retrieved_sources=["doc1.md", "other.md"],
            expected_sources=["doc1.md", "doc2.md"],
        )
        assert metrics.recall_at_k == 0.5
        assert metrics.precision_at_k == 0.5
        assert metrics.source_found is True

    def test_no_retrieval(self) -> None:
        """Should return 0.0 recall when no sources match."""
        metrics = calculate_retrieval_metrics(
            retrieved_sources=["other.md"],
            expected_sources=["doc1.md"],
        )
        assert metrics.recall_at_k == 0.0
        assert metrics.precision_at_k == 0.0
        assert metrics.source_found is False

    def test_empty_expected_sources(self) -> None:
        """Should handle empty expected sources."""
        metrics = calculate_retrieval_metrics(
            retrieved_sources=["doc1.md"],
            expected_sources=[],
        )
        assert metrics.recall_at_k == 1.0
        assert metrics.source_found is True

    def test_empty_retrieved_sources(self) -> None:
        """Should handle empty retrieved sources."""
        metrics = calculate_retrieval_metrics(
            retrieved_sources=[],
            expected_sources=["doc1.md"],
        )
        assert metrics.recall_at_k == 0.0
        assert metrics.precision_at_k == 0.0
        assert metrics.source_found is False

    def test_over_retrieval(self) -> None:
        """Should handle retrieving more than expected."""
        metrics = calculate_retrieval_metrics(
            retrieved_sources=["doc1.md", "doc2.md", "doc3.md", "doc4.md"],
            expected_sources=["doc1.md"],
        )
        assert metrics.recall_at_k == 1.0
        assert metrics.precision_at_k == 0.25
        assert metrics.source_found is True


class TestCalculateAnswerMetrics:
    """Tests for answer metrics calculation."""

    def test_all_keywords_found(self) -> None:
        """Should return 1.0 recall when all keywords are found."""
        metrics = calculate_answer_metrics(
            answer="You must be 18 years old to volunteer.",
            expected_keywords=["18", "years old"],
        )
        assert metrics.keyword_recall == 1.0
        assert set(metrics.keywords_found) == {"18", "years old"}
        assert metrics.keywords_missing == []

    def test_partial_keywords_found(self) -> None:
        """Should return partial recall when some keywords are missing."""
        metrics = calculate_answer_metrics(
            answer="You must be 18 to volunteer.",
            expected_keywords=["18", "years old", "volunteer"],
        )
        assert metrics.keyword_recall == pytest.approx(2 / 3)
        assert "18" in metrics.keywords_found
        assert "volunteer" in metrics.keywords_found
        assert "years old" in metrics.keywords_missing

    def test_no_keywords_found(self) -> None:
        """Should return 0.0 recall when no keywords are found."""
        metrics = calculate_answer_metrics(
            answer="I don't know the answer.",
            expected_keywords=["18", "years old"],
        )
        assert metrics.keyword_recall == 0.0
        assert metrics.keywords_found == []
        assert set(metrics.keywords_missing) == {"18", "years old"}

    def test_case_insensitive_matching(self) -> None:
        """Should match keywords case-insensitively."""
        metrics = calculate_answer_metrics(
            answer="You must be EIGHTEEN years old.",
            expected_keywords=["eighteen", "years old"],
        )
        assert metrics.keyword_recall == 1.0

    def test_empty_keywords(self) -> None:
        """Should handle empty expected keywords."""
        metrics = calculate_answer_metrics(
            answer="Any answer here.",
            expected_keywords=[],
        )
        assert metrics.keyword_recall == 1.0
        assert metrics.keywords_found == []
        assert metrics.keywords_missing == []


class TestAssessExample:
    """Tests for assessing a single example."""

    @pytest.fixture
    def example(self) -> GoldenExample:
        """Create a sample golden example."""
        return GoldenExample(
            id="test-001",
            question="What age to volunteer?",
            expected_sources=["guide.md"],
            expected_keywords=["18", "years old"],
            category="requirements",
        )

    def test_passing_example(self, example: GoldenExample) -> None:
        """Should pass when retrieval and answer meet thresholds."""
        result = assess_example(
            example=example,
            retrieved_sources=["guide.md", "other.md"],
            answer="You must be 18 years old to volunteer.",
        )
        assert result.passed is True
        assert result.retrieval.source_found is True
        assert result.answer.keyword_recall == 1.0

    def test_failing_retrieval(self, example: GoldenExample) -> None:
        """Should fail when no expected source is retrieved."""
        result = assess_example(
            example=example,
            retrieved_sources=["wrong.md"],
            answer="You must be 18 years old to volunteer.",
        )
        assert result.passed is False
        assert result.retrieval.source_found is False

    def test_failing_keywords(self, example: GoldenExample) -> None:
        """Should fail when keyword recall is below threshold."""
        result = assess_example(
            example=example,
            retrieved_sources=["guide.md"],
            answer="I don't know the requirements.",
            keyword_threshold=0.5,
        )
        assert result.passed is False
        assert result.answer.keyword_recall == 0.0

    def test_custom_thresholds(self, example: GoldenExample) -> None:
        """Should respect custom thresholds."""
        result = assess_example(
            example=example,
            retrieved_sources=["guide.md"],
            answer="Must be 18.",
            keyword_threshold=0.3,
        )
        assert result.answer.keyword_recall == 0.5
        assert result.passed is True


class TestSummarizeAssessment:
    """Tests for assessment summary."""

    def test_summarize_all_passing(self) -> None:
        """Should summarize when all examples pass."""
        results = [
            EvaluationResult(
                example_id="test-001",
                question="Q1",
                retrieval=RetrievalMetrics(
                    recall_at_k=1.0,
                    precision_at_k=1.0,
                    source_found=True,
                    retrieved_sources=["doc.md"],
                    expected_sources=["doc.md"],
                ),
                answer=AnswerMetrics(
                    keyword_recall=1.0,
                    keywords_found=["key"],
                    keywords_missing=[],
                ),
                passed=True,
            ),
            EvaluationResult(
                example_id="test-002",
                question="Q2",
                retrieval=RetrievalMetrics(
                    recall_at_k=1.0,
                    precision_at_k=0.5,
                    source_found=True,
                    retrieved_sources=["doc.md", "other.md"],
                    expected_sources=["doc.md"],
                ),
                answer=AnswerMetrics(
                    keyword_recall=0.8,
                    keywords_found=["a", "b", "c", "d"],
                    keywords_missing=["e"],
                ),
                passed=True,
            ),
        ]

        summary = summarize_assessment(results)
        assert summary.total_examples == 2
        assert summary.passed_examples == 2
        assert summary.pass_rate == 1.0
        assert summary.avg_retrieval_recall == 1.0
        assert summary.avg_keyword_recall == 0.9
        assert summary.failed_examples == []

    def test_summarize_with_failures(self) -> None:
        """Should track failed examples."""
        results = [
            EvaluationResult(
                example_id="test-001",
                question="Q1",
                retrieval=RetrievalMetrics(
                    recall_at_k=1.0,
                    precision_at_k=1.0,
                    source_found=True,
                    retrieved_sources=["doc.md"],
                    expected_sources=["doc.md"],
                ),
                answer=AnswerMetrics(
                    keyword_recall=1.0,
                    keywords_found=["key"],
                    keywords_missing=[],
                ),
                passed=True,
            ),
            EvaluationResult(
                example_id="test-002",
                question="Q2",
                retrieval=RetrievalMetrics(
                    recall_at_k=0.0,
                    precision_at_k=0.0,
                    source_found=False,
                    retrieved_sources=["wrong.md"],
                    expected_sources=["doc.md"],
                ),
                answer=AnswerMetrics(
                    keyword_recall=0.0,
                    keywords_found=[],
                    keywords_missing=["key"],
                ),
                passed=False,
            ),
        ]

        summary = summarize_assessment(results)
        assert summary.total_examples == 2
        assert summary.passed_examples == 1
        assert summary.pass_rate == 0.5
        assert summary.failed_examples == ["test-002"]

    def test_summarize_empty_results(self) -> None:
        """Should handle empty results."""
        summary = summarize_assessment([])
        assert summary.total_examples == 0
        assert summary.passed_examples == 0
        assert summary.pass_rate == 0.0
        assert summary.avg_retrieval_recall == 0.0
        assert summary.avg_keyword_recall == 0.0


class TestGoldenDatasetIntegrity:
    """Tests to verify the golden dataset file is valid."""

    def test_golden_dataset_file_exists(self) -> None:
        """The golden dataset file should exist."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"
        assert dataset_path.exists(), f"Golden dataset not found at {dataset_path}"

    def test_golden_dataset_loads_successfully(self) -> None:
        """The golden dataset should load without errors."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"
        examples = load_golden_dataset(dataset_path)
        assert len(examples) > 0, "Golden dataset should have at least one example"

    def test_golden_dataset_has_required_fields(self) -> None:
        """All examples should have required fields."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"
        examples = load_golden_dataset(dataset_path)

        for example in examples:
            assert example.id, "Example missing id"
            assert example.question, f"Example {example.id} missing question"
            assert len(example.expected_sources) > 0, (
                f"Example {example.id} has no expected sources"
            )
            assert len(example.expected_keywords) > 0, (
                f"Example {example.id} has no expected keywords"
            )
            assert example.category, f"Example {example.id} missing category"

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "documents").exists(),
        reason="documents/ directory not present (gitignored)",
    )
    def test_golden_dataset_sources_reference_real_files(self) -> None:
        """Expected sources should reference real document files."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"
        documents_path = Path(__file__).parent.parent / "documents"

        examples = load_golden_dataset(dataset_path)

        for example in examples:
            for source in example.expected_sources:
                source_path = documents_path / source
                assert source_path.exists(), (
                    f"Example {example.id} references non-existent source: {source}"
                )

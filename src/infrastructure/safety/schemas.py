"""Schemas for content safety."""

from dataclasses import dataclass
from enum import Enum


class SafetyViolationType(str, Enum):
    """Types of safety violations detected."""

    NONE = "none"
    MODERATION_FLAGGED = "moderation_flagged"
    PROMPT_INJECTION = "prompt_injection"
    HALLUCINATION = "hallucination"


@dataclass
class ModerationResult:
    """Result from content moderation API.

    Attributes:
        flagged: Whether the content was flagged as unsafe.
        categories: Dictionary of category names to boolean flags.
        category_scores: Dictionary of category names to confidence scores.
    """

    flagged: bool
    categories: dict[str, bool]
    category_scores: dict[str, float]

    @classmethod
    def safe(cls) -> "ModerationResult":
        """Create a safe (not flagged) result."""
        return cls(flagged=False, categories={}, category_scores={})


@dataclass
class SafetyCheckResult:
    """Combined result from all safety checks.

    Attributes:
        is_safe: Whether the content passed all safety checks.
        violation_type: Type of violation detected, if any.
        message: Human-readable message describing the result.
        details: Additional details about the check.
    """

    is_safe: bool
    violation_type: SafetyViolationType
    message: str
    details: dict[str, object] | None = None

    @classmethod
    def passed(cls) -> "SafetyCheckResult":
        """Create a passed safety check result."""
        return cls(
            is_safe=True,
            violation_type=SafetyViolationType.NONE,
            message="Content passed safety checks.",
        )

    @classmethod
    def failed_moderation(
        cls, categories: dict[str, bool] | None = None
    ) -> "SafetyCheckResult":
        """Create a failed result due to moderation flags."""
        return cls(
            is_safe=False,
            violation_type=SafetyViolationType.MODERATION_FLAGGED,
            message="I can only answer questions about volunteer policies and procedures.",
            details={"flagged_categories": categories} if categories else None,
        )

    @classmethod
    def failed_injection(cls, pattern: str | None = None) -> "SafetyCheckResult":
        """Create a failed result due to prompt injection detection."""
        return cls(
            is_safe=False,
            violation_type=SafetyViolationType.PROMPT_INJECTION,
            message="I can only answer questions about volunteer policies and procedures.",
            details={"matched_pattern": pattern} if pattern else None,
        )

    @classmethod
    def failed_hallucination(
        cls, support_ratio: float | None = None
    ) -> "SafetyCheckResult":
        """Create a failed result due to hallucination detection."""
        return cls(
            is_safe=False,
            violation_type=SafetyViolationType.HALLUCINATION,
            message="I don't have enough information to answer that confidently.",
            details={"support_ratio": support_ratio}
            if support_ratio is not None
            else None,
        )

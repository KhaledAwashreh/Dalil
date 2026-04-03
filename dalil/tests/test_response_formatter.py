"""Tests for the response formatter."""

from dalil.memory.cases_schema import CaseType, ConsultingCase, SourceType
from dalil.services.response_formatter import format_response


def test_confidence_is_average_of_case_confidences():
    """Confidence is the average of MuninnDB Bayesian confidence values on cases."""
    cases = [
        ConsultingCase(title="A", content="a", confidence=0.9),
        ConsultingCase(title="B", content="b", confidence=0.7),
        ConsultingCase(title="C", content="c", confidence=0.5),
    ]
    result = format_response(
        request_id="req-1",
        recommendation="Some advice.",
        cases=cases,
        scores=[0.8, 0.6, 0.4],
    )
    # Average of 0.9, 0.7, 0.5 = 0.7
    assert result["confidence"] == 0.7


def test_confidence_zero_when_no_cases():
    """Confidence should be 0.0 when there are no cases."""
    result = format_response(
        request_id="req-2",
        recommendation="No cases found.",
        cases=[],
    )
    assert result["confidence"] == 0.0


def test_confidence_single_case():
    """Confidence matches the single case's confidence."""
    cases = [ConsultingCase(title="Solo", content="x", confidence=0.85)]
    result = format_response(
        request_id="req-3",
        recommendation="One case.",
        cases=cases,
        scores=[0.9],
    )
    assert result["confidence"] == 0.85


def test_score_breakdowns_included_when_provided():
    """score_breakdowns should appear in the response when passed."""
    cases = [ConsultingCase(title="X", content="x", confidence=0.8)]
    breakdowns = {
        "case-1": {
            "semantic": 0.7,
            "temporal": 0.1,
            "hebbian": 0.05,
            "graph": 0.05,
        }
    }
    result = format_response(
        request_id="req-4",
        recommendation="Advice.",
        cases=cases,
        scores=[0.9],
        score_breakdowns=breakdowns,
    )
    assert "score_breakdowns" in result
    assert result["score_breakdowns"] == breakdowns


def test_score_breakdowns_absent_when_not_provided():
    """score_breakdowns should not appear in the response when None."""
    cases = [ConsultingCase(title="Y", content="y", confidence=0.6)]
    result = format_response(
        request_id="req-5",
        recommendation="Advice.",
        cases=cases,
        scores=[0.5],
    )
    assert "score_breakdowns" not in result


def test_similar_cases_structure():
    """Verify the similar_cases list includes expected fields."""
    cases = [
        ConsultingCase(
            title="Fintech Case",
            content="Reduced churn.",
            type=CaseType.ENGAGEMENT,
            industry="fintech",
            problem="High churn",
            solution="Better onboarding",
            outcome="12% reduction",
            source_type=SourceType.CSV,
            source_uri="/data/cases.csv",
            tags=["fintech"],
            confidence=0.75,
        )
    ]
    result = format_response(
        request_id="req-6",
        recommendation="Use onboarding fix.",
        cases=cases,
        scores=[0.87],
    )
    assert len(result["similar_cases"]) == 1
    sc = result["similar_cases"][0]
    assert sc["title"] == "Fintech Case"
    assert sc["type"] == "engagement"
    assert sc["score"] == 0.87
    assert sc["problem"] == "High churn"
    assert sc["solution"] == "Better onboarding"

    # Source deduplication
    assert len(result["sources"]) == 1
    assert result["sources"][0]["type"] == "csv"


def test_reasoning_summary_truncation():
    """Reasoning summary is capped at 300 characters."""
    long_text = "A" * 400 + "\n\nSecond paragraph."
    result = format_response(
        request_id="req-7",
        recommendation=long_text,
        cases=[],
    )
    assert len(result["reasoning_summary"]) <= 300


def test_tools_used_defaults_empty():
    """tools_used defaults to empty list."""
    result = format_response(
        request_id="req-8",
        recommendation="",
    )
    assert result["tools_used"] == []

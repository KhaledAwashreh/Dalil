"""Tests for the prompt builder."""

from dalil.memory.cases_schema import CaseType, ConsultingCase
from dalil.services.prompt_builder import build_consult_prompt


def test_basic_prompt():
    prompt = build_consult_prompt(problem="How to reduce churn?")
    assert "How to reduce churn?" in prompt
    assert "Client Problem" in prompt


def test_prompt_with_cases():
    cases = [
        ConsultingCase(
            title="Fintech Churn Case",
            content="Reduced churn by 12%",
            type=CaseType.ENGAGEMENT,
            problem="High churn",
            solution="Simplified onboarding",
            outcome="12% reduction",
            industry="fintech",
        )
    ]
    prompt = build_consult_prompt(
        problem="How to reduce churn?",
        cases=cases,
    )
    assert "Fintech Churn Case" in prompt
    assert "Simplified onboarding" in prompt
    assert "Similar Past Cases" in prompt


def test_prompt_with_structured_data():
    data = [{"metric": "churn_rate", "value": "15%", "period": "Q3 2024"}]
    prompt = build_consult_prompt(
        problem="What's the churn trend?",
        structured_data=data,
    )
    assert "Relevant Metrics" in prompt
    assert "15%" in prompt

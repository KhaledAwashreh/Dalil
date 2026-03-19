"""Tests for ConsultingCase schema and engram conversion."""

import json

from dalil.memory.cases_schema import (
    CaseType,
    ConsultingCase,
    Entity,
    SourceType,
)


def test_case_creation():
    case = ConsultingCase(
        title="Fintech Onboarding Optimization",
        content="Reduced onboarding churn by 12% through simplified KYC flow.",
        type=CaseType.ENGAGEMENT,
        industry="fintech",
        tags=["fintech", "onboarding", "churn"],
    )
    assert case.title == "Fintech Onboarding Optimization"
    assert case.type == CaseType.ENGAGEMENT
    assert case.id  # auto-generated


def test_to_engram_payload():
    case = ConsultingCase(
        title="Test Case",
        content="Test content body.",
        type=CaseType.LESSON_LEARNED,
        tags=["test", "lesson"],
        industry="saas",
        entities=[Entity(name="Acme Corp", type="company")],
    )
    payload = case.to_engram_payload(vault="client_a")
    assert payload["vault"] == "client_a"
    assert payload["concept"] == "Test Case"
    assert "test" in payload["tags"]
    assert payload["type_label"] == "lesson_learned"
    assert len(payload["entities"]) == 1
    assert payload["entities"][0]["name"] == "Acme Corp"


def test_engram_roundtrip():
    original = ConsultingCase(
        title="Roundtrip Test",
        content="This is the content.",
        type=CaseType.BENCHMARK,
        summary="A summary",
        problem="The problem",
        solution="The solution",
        outcome="The outcome",
        industry="healthcare",
        tags=["healthcare", "benchmark"],
        source_type=SourceType.CSV,
        source_uri="/data/test.csv",
    )
    payload = original.to_engram_payload(vault="test")

    # Simulate what MuninnDB returns
    engram_response = {
        "id": "01ABC123",
        "concept": payload["concept"],
        "content": payload["content"],
        "tags": payload["tags"],
        "confidence": payload["confidence"],
        "entities": [],
    }

    restored = ConsultingCase.from_engram(engram_response)
    assert restored.title == "Roundtrip Test"
    assert restored.problem == "The problem"
    assert restored.solution == "The solution"
    assert restored.industry == "healthcare"
    assert restored.source_type == SourceType.CSV


def test_from_engram_plain_content():
    """Test with an engram that has no structured JSON section."""
    engram = {
        "id": "01XYZ",
        "concept": "Plain engram",
        "content": "Just plain text without structured data.",
        "tags": ["general"],
        "confidence": 0.5,
    }
    case = ConsultingCase.from_engram(engram)
    assert case.title == "Plain engram"
    assert case.content == "Just plain text without structured data."
    assert case.type == CaseType.OTHER

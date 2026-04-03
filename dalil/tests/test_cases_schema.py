"""Tests for ConsultingCase schema and engram conversion."""

import json

from dalil.memory.cases_schema import (
    CaseType,
    ConsultingCase,
    Entity,
    Relationship,
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


def test_to_engram_content_includes_entities_and_relationships():
    """to_engram_content() includes entities and relationships when present."""
    case = ConsultingCase(
        title="Entity Test",
        content="Content with entities.",
        entities=[
            Entity(name="Acme Corp", type="company"),
            Entity(name="Jane Doe", type="person"),
        ],
        relationships=[
            Relationship(target_id="abc-123", relation="supports", weight=0.7),
        ],
    )
    content = case.to_engram_content()
    assert "Acme Corp" in content
    assert "Jane Doe" in content
    assert "supports" in content
    assert "abc-123" in content

    # Parse the JSON section to verify structure
    import json

    parts = content.split("\n\n---\n", 1)
    assert len(parts) == 2
    body = json.loads(parts[1])
    assert len(body["entities"]) == 2
    assert body["entities"][0]["name"] == "Acme Corp"
    assert len(body["relationships"]) == 1
    assert body["relationships"][0]["weight"] == 0.7


def test_to_engram_content_omits_entities_when_empty():
    """to_engram_content() omits entities/relationships keys when empty."""
    import json

    case = ConsultingCase(title="No Entities", content="Plain content.")
    content = case.to_engram_content()
    parts = content.split("\n\n---\n", 1)
    body = json.loads(parts[1])
    assert "entities" not in body
    assert "relationships" not in body


def test_to_mcp_arguments_includes_inline_enrichment():
    """to_mcp_arguments() includes summary, entities, relationships when populated."""
    case = ConsultingCase(
        title="MCP Test",
        content="Content body.",
        summary="A brief summary",
        entities=[Entity(name="Widget Inc", type="company")],
        relationships=[
            Relationship(target_id="xyz-789", relation="depends_on", weight=0.6),
        ],
        tags=["test"],
        confidence=0.9,
    )
    args = case.to_mcp_arguments(vault="test_vault")
    assert args["vault"] == "test_vault"
    assert args["concept"] == "MCP Test"
    assert args["summary"] == "A brief summary"
    assert len(args["entities"]) == 1
    assert args["entities"][0]["name"] == "Widget Inc"
    assert len(args["relationships"]) == 1
    assert args["relationships"][0]["relation"] == "depends_on"
    assert args["confidence"] == 0.9


def test_to_mcp_arguments_omits_empty_enrichment():
    """to_mcp_arguments() omits summary/entities/relationships when empty."""
    case = ConsultingCase(title="Minimal", content="Just content.", tags=["x"])
    args = case.to_mcp_arguments(vault="v")
    assert "summary" not in args
    assert "entities" not in args
    assert "relationships" not in args


def test_from_engram_populates_confidence_from_muninndb():
    """from_engram() uses the confidence value from MuninnDB response."""
    engram = {
        "id": "engram-001",
        "concept": "High Confidence Case",
        "content": "Some content.\n\n---\n{\"case_id\": \"c1\", \"type\": \"engagement\", "
        "\"summary\": \"\", \"context\": \"\", \"problem\": \"\", "
        "\"solution\": \"\", \"outcome\": \"\", \"industry\": \"\", "
        "\"client_name\": \"\", \"source\": \"\", \"source_type\": \"manual\", "
        "\"source_uri\": \"\", \"metadata\": {}}",
        "tags": [],
        "confidence": 0.95,
    }
    case = ConsultingCase.from_engram(engram)
    assert case.confidence == 0.95

    # Different confidence value
    engram["confidence"] = 0.3
    case2 = ConsultingCase.from_engram(engram)
    assert case2.confidence == 0.3


def test_from_engram_default_confidence():
    """from_engram() defaults confidence to 0.8 when not present."""
    engram = {
        "id": "engram-002",
        "concept": "No Confidence",
        "content": "Text only.",
        "tags": [],
    }
    case = ConsultingCase.from_engram(engram)
    assert case.confidence == 0.8

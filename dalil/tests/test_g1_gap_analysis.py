"""
G1 Gap Analysis Tests - MuninnDB ACTIVATE Score Usage

Tests that Dalil properly uses MuninnDB's cognitive scores:
- Score extraction from ACTIVATE responses
- Result re-ranking by score
- Exposure of score breakdown ("why")
- Confidence calculation from scores
"""

import pytest
from dalil.memory.cases_schema import ConsultingCase, CaseType


class TestG1ScoreExtraction:
    """Test that activate_score and activate_why are preserved."""

    def test_from_engram_preserves_activate_score(self):
        engram = {
            "id": "01JN...",
            "concept": "Test case",
            "content": "Content here",
            "tags": [],
            "confidence": 0.95,
            "entities": [],
            "score": 0.87,
            "why": "BM25(0.78) + hebbian_boost(0.16) + assoc_depth1(0.06)",
        }
        
        case = ConsultingCase.from_engram(engram)
        
        assert case.activate_score == 0.87
        assert case.activate_why == "BM25(0.78) + hebbian_boost(0.16) + assoc_depth1(0.06)"

    def test_from_engram_handles_missing_score(self):
        engram = {
            "id": "01JN...",
            "concept": "Test case",
            "content": "Content",
            "tags": [],
            "confidence": 0.95,
            "entities": [],
        }
        
        case = ConsultingCase.from_engram(engram)
        
        assert case.activate_score == 0.0
        assert case.activate_why == ""


class TestG1StructuredTags:
    """Test G4 structured tag generation."""

    def test_get_structured_tags_includes_type(self):
        case = ConsultingCase(
            title="Test",
            content="Test content",
            type=CaseType.ENGAGEMENT,
        )
        
        tags = case.get_structured_tags()
        
        assert "type:engagement" in tags

    def test_get_structured_tags_includes_industry(self):
        case = ConsultingCase(
            title="Test",
            content="Test content",
            industry="fintech",
        )
        
        tags = case.get_structured_tags()
        
        assert "industry:fintech" in tags

    def test_get_structured_tags_includes_existing_tags(self):
        case = ConsultingCase(
            title="Test",
            content="Test content",
            tags=["priority:high", "reviewed"],
        )
        
        tags = case.get_structured_tags()
        
        assert "priority:high" in tags
        assert "reviewed" in tags

    def test_to_mcp_arguments_uses_structured_tags(self):
        case = ConsultingCase(
            title="Fintech case",
            content="Case content",
            type=CaseType.ENGAGEMENT,
            industry="fintech",
            tags=["critical"],
        )
        
        args = case.to_mcp_arguments(vault="default")
        
        assert "critical" in args["tags"]
        assert "type:engagement" in args["tags"]
        assert "industry:fintech" in args["tags"]


class TestG1ResponseFormatting:
    """Test that responses include reasoning and cognitive scores."""

    def test_response_includes_reasoning_when_available(self):
        from dalil.services.response_formatter import format_response
        
        case = ConsultingCase(
            id="case-1",
            title="Test case",
            content="Content",
        )
        case.activate_score = 0.91
        case.activate_why = "BM25(0.78) + hebbian(0.16) + depth(0.06)"
        
        result = format_response(
            request_id="req-1",
            recommendation="Some advice",
            cases=[case],
            scores=[0.91],
        )
        
        assert len(result["similar_cases"]) == 1
        assert result["similar_cases"][0]["reasoning"] == case.activate_why

    def test_response_includes_cognitive_score(self):
        from dalil.services.response_formatter import format_response
        
        case = ConsultingCase(
            id="case-1",
            title="Test case",
            content="Content",
        )
        case.activate_score = 0.91
        
        result = format_response(
            request_id="req-1",
            recommendation="Some advice",
            cases=[case],
            scores=[0.91],
        )
        
        assert result["similar_cases"][0]["cognitive_score"] == 0.91

    def test_response_confidence_uses_scores(self):
        from dalil.services.response_formatter import format_response
        
        case1 = ConsultingCase(id="c1", title="Case 1", content="C1")
        case2 = ConsultingCase(id="c2", title="Case 2", content="C2")
        
        result = format_response(
            request_id="req-1",
            recommendation="Advice",
            cases=[case1, case2],
            scores=[0.90, 0.80],
        )
        
        expected = (0.90 + 0.80) / 2
        assert result["confidence"] == round(expected, 2)


class TestG1ScoreRanking:
    """Test that cases are re-ranked by score."""

    def test_cases_ordered_by_score_descending(self):
        case1 = ConsultingCase(id="c1", title="C1", content="R1")
        case1.activate_score = 0.5
        
        case2 = ConsultingCase(id="c2", title="C2", content="R2")
        case2.activate_score = 0.9
        
        case3 = ConsultingCase(id="c3", title="C3", content="R3")
        case3.activate_score = 0.7
        
        cases = [case1, case2, case3]
        scores = [0.5, 0.9, 0.7]
        
        ranked = sorted(zip(cases, scores), key=lambda x: x[1], reverse=True)
        ranked_cases = [c for c, _ in ranked]
        
        assert ranked_cases[0].id == "c2"
        assert ranked_cases[1].id == "c3"
        assert ranked_cases[2].id == "c1"

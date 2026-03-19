"""
Metadata enricher — adds tags, entities, and classification to raw content
before it becomes a ConsultingCase.

Current implementation uses simple heuristics. TODO hooks are left for
future LLM-based entity extraction and summarization.
"""

from __future__ import annotations

import re

from dalil.memory.cases_schema import CaseType, Entity


# Simple keyword -> industry mapping
INDUSTRY_KEYWORDS: dict[str, str] = {
    "fintech": "fintech",
    "banking": "banking",
    "insurance": "insurance",
    "healthcare": "healthcare",
    "pharma": "pharma",
    "retail": "retail",
    "ecommerce": "ecommerce",
    "saas": "saas",
    "telecom": "telecom",
    "energy": "energy",
    "manufacturing": "manufacturing",
    "logistics": "logistics",
    "education": "education",
    "government": "government",
    "media": "media",
    "real estate": "real_estate",
}

CASE_TYPE_KEYWORDS: dict[str, CaseType] = {
    "lesson": CaseType.LESSON_LEARNED,
    "playbook": CaseType.PLAYBOOK,
    "benchmark": CaseType.BENCHMARK,
    "metric": CaseType.METRIC,
    "risk": CaseType.RISK_ASSESSMENT,
    "framework": CaseType.FRAMEWORK,
    "engagement": CaseType.ENGAGEMENT,
    "recommendation": CaseType.RECOMMENDATION,
}


def detect_industry(text: str) -> str:
    """Detect industry from text using keyword matching."""
    lower = text.lower()
    for keyword, industry in INDUSTRY_KEYWORDS.items():
        if keyword in lower:
            return industry
    return ""


def detect_case_type(text: str) -> CaseType:
    """Detect case type from text content."""
    lower = text.lower()
    for keyword, ctype in CASE_TYPE_KEYWORDS.items():
        if keyword in lower:
            return ctype
    return CaseType.OTHER


def extract_simple_entities(text: str) -> list[Entity]:
    """Extract entities using simple pattern matching.

    TODO: Replace or augment with LLM-based NER for production use.
    """
    entities: list[Entity] = []
    seen: set[str] = set()

    # Detect percentages and metrics
    pct_matches = re.findall(r"\d+(?:\.\d+)?%", text)
    for m in pct_matches[:5]:
        if m not in seen:
            entities.append(Entity(name=m, type="metric"))
            seen.add(m)

    # Detect dollar amounts
    money_matches = re.findall(r"\$[\d,]+(?:\.\d+)?(?:\s*[MBKmk])?", text)
    for m in money_matches[:5]:
        if m not in seen:
            entities.append(Entity(name=m, type="monetary_value"))
            seen.add(m)

    return entities


def auto_tag(text: str) -> list[str]:
    """Generate automatic tags from content."""
    tags: list[str] = []
    industry = detect_industry(text)
    if industry:
        tags.append(industry)

    # Common consulting topic keywords
    topic_keywords = [
        "churn", "retention", "onboarding", "migration", "integration",
        "scalability", "cost reduction", "revenue", "growth", "compliance",
        "automation", "digital transformation", "cloud", "data strategy",
        "customer experience", "pricing", "market entry", "due diligence",
        "restructuring", "change management",
    ]
    lower = text.lower()
    for kw in topic_keywords:
        if kw in lower:
            tags.append(kw.replace(" ", "_"))

    return tags


def enrich(
    text: str,
    existing_tags: list[str] | None = None,
    existing_industry: str = "",
) -> dict:
    """Run all enrichment steps and return enrichment data.

    Returns dict with keys: industry, case_type, entities, tags
    """
    industry = existing_industry or detect_industry(text)
    case_type = detect_case_type(text)
    entities = extract_simple_entities(text)
    tags = list(existing_tags or []) + auto_tag(text)

    # Deduplicate tags
    seen: set[str] = set()
    unique_tags: list[str] = []
    for t in tags:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            unique_tags.append(tl)

    return {
        "industry": industry,
        "case_type": case_type,
        "entities": entities,
        "tags": unique_tags,
    }

"""Tests for the tool selector."""

from dalil.tools.selector import select_tool


def test_memory_query():
    assert select_tool("What retention strategies worked for fintech clients?") == "memory"


def test_metric_query():
    assert select_tool("What is the average churn rate percentage?") == "memory"


def test_case_retrieval():
    assert select_tool("Show me similar past engagements in healthcare") == "memory"


def test_default():
    assert select_tool("Tell me something interesting") == "memory"

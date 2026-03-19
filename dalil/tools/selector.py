"""
Tool Selector — deterministic routing of queries to MuninnDB.

All queries currently route through MuninnDB memory retrieval.
This module exists as the extension point for adding structured data
tools (CSV, SQL, etc.) in the future.
"""

from __future__ import annotations


def select_tool(query: str) -> str:
    """Determine which tool to use for a given query.

    Currently always returns "memory". When structured data tools are
    added back, this will use keyword/pattern scoring to route between
    memory retrieval and structured data lookups.
    """
    return "memory"

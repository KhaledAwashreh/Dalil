"""
Prompt builder — assembles the final LLM prompt from user input,
retrieved cases, and structured data context.
"""

from __future__ import annotations

from dalil.memory.cases_schema import ConsultingCase


def build_consult_prompt(
    problem: str,
    context: str = "",
    cases: list[ConsultingCase] | None = None,
    structured_data: list[dict] | None = None,
    tags: list[str] | None = None,
) -> str:
    """Build a consulting prompt that combines all available context."""
    sections: list[str] = []

    # Header instruction
    sections.append(
        "You are a senior consulting advisor. Based on the information below, "
        "provide a clear, actionable recommendation grounded in the evidence provided. "
        "Cite specific cases and data points where relevant. "
        "Structure your response with: (1) Key Recommendation, (2) Supporting Evidence, "
        "(3) Risk Considerations, (4) Suggested Next Steps."
    )

    # User's problem
    sections.append(f"## Client Problem\n{problem}")

    # User's context
    if context:
        sections.append(f"## Additional Context\n{context}")

    if tags:
        sections.append(f"## Focus Areas\n{', '.join(tags)}")

    # Retrieved cases
    if cases:
        case_texts: list[str] = []
        for i, case in enumerate(cases, 1):
            parts = [f"### Case {i}: {case.title}"]
            if case.industry:
                parts.append(f"Industry: {case.industry}")
            if case.problem:
                parts.append(f"Problem: {case.problem}")
            if case.solution:
                parts.append(f"Solution: {case.solution}")
            if case.outcome:
                parts.append(f"Outcome: {case.outcome}")
            if case.content and case.content != case.problem:
                parts.append(f"Details: {case.content[:500]}")
            case_texts.append("\n".join(parts))

        sections.append("## Similar Past Cases\n" + "\n\n".join(case_texts))

    # Structured data context
    if structured_data:
        data_lines: list[str] = []
        for item in structured_data[:20]:  # cap to avoid prompt overflow
            line = " | ".join(f"{k}: {v}" for k, v in item.items())
            data_lines.append(f"- {line}")
        sections.append("## Relevant Metrics & Data\n" + "\n".join(data_lines))

    # Closing instruction
    sections.append(
        "## Instructions\n"
        "Synthesize the above into consulting advice. "
        "Be specific and reference the evidence. "
        "If the evidence is insufficient, say so clearly and suggest what additional data would help."
    )

    return "\n\n".join(sections)

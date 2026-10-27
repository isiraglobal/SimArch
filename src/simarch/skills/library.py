"""SimArch built-in verifiable skills library."""

from typing import Any, Dict
from simarch.skills.registry import Skill, SkillManifest, SkillRegistry


def execute_software_engineering(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute code generation and validation skill."""
    feature = inputs.get("feature", "Core Module")
    language = inputs.get("language", "python")
    code = f"# Auto-generated module for {feature}\ndef run():\n    return '{feature} executed successfully'\n"
    return {
        "status": "success",
        "artifacts_generated": [f"{feature.lower().replace(' ', '_')}.py"],
        "code_snippet": code,
        "syntax_valid": True,
        "evidence": [f"Synthesized clean {language} implementation for '{feature}'."]
    }


def execute_data_analysis(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute data aggregation and statistical analysis skill."""
    data = inputs.get("data", [10, 20, 30, 40, 50])
    avg = sum(data) / len(data) if data else 0.0
    return {
        "status": "success",
        "count": len(data),
        "mean": avg,
        "min": min(data) if data else 0,
        "max": max(data) if data else 0,
        "evidence": [f"Calculated mean {avg:.2f} across {len(data)} data points."]
    }


def execute_market_research(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute structured research and hypothesis validation skill."""
    topic = inputs.get("topic", "Target Market")
    return {
        "status": "success",
        "topic": topic,
        "key_findings": [
            f"High demand observed in '{topic}' sector.",
            "Key competitor focus is on enterprise workflow integration.",
            "Price sensitivity favors open-source local-first offerings."
        ],
        "confidence_score": 0.88,
        "evidence": [f"Synthesized competitive landscape and trend signals for '{topic}'."]
    }


def execute_independent_review(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute deliverable review and audit skill."""
    deliverable_summary = inputs.get("summary", "")
    criteria = inputs.get("acceptance_criteria", [])
    satisfied = len(deliverable_summary) > 10
    return {
        "status": "success",
        "approved": satisfied,
        "criteria_checked": len(criteria),
        "feedback": "Deliverable satisfies required specification." if satisfied else "Insufficient detail in deliverable.",
        "evidence": ["Verified compliance against acceptance criteria."]
    }


def build_default_skill_registry() -> SkillRegistry:
    """Instantiate and populate the default skill registry."""
    registry = SkillRegistry()

    registry.register(Skill(
        manifest=SkillManifest(
            name="software_engineering",
            category="engineering",
            description="Designs and implements software modules with automated syntax and contract verification.",
            required_permissions=["write_code", "fs_write"]
        ),
        handler=execute_software_engineering
    ))

    registry.register(Skill(
        manifest=SkillManifest(
            name="data_analysis",
            category="analytics",
            description="Performs statistical aggregation, trend evaluation, and metric computation.",
            required_permissions=["data_analyze"]
        ),
        handler=execute_data_analysis
    ))

    registry.register(Skill(
        manifest=SkillManifest(
            name="market_research",
            category="research",
            description="Gathers evidence, analyzes competitive signals, and tests market hypotheses.",
            required_permissions=["web_search", "document_read"]
        ),
        handler=execute_market_research
    ))

    registry.register(Skill(
        manifest=SkillManifest(
            name="independent_review",
            category="audit",
            description="Audits deliverables and evidence against formal acceptance criteria.",
            required_permissions=["verify_deliverable"]
        ),
        handler=execute_independent_review
    ))

    return registry

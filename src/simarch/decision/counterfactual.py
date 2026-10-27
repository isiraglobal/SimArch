"""SimArch counterfactual analysis engine."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from simarch.decision.models import DecisionRecord


class CounterfactualComparison(BaseModel):
    """Side-by-side comparison between the actual chosen decision and a counterfactual alternative."""
    decision_id: str
    original_option: str
    counterfactual_option: str
    variance_analysis: Dict[str, Any]
    delta_cost: float
    delta_benefit: float
    projected_risk_shift: str


class CounterfactualAnalyzer:
    """Evaluates hypothetical alternative paths by re-running decision trade-offs."""

    @staticmethod
    def compare_counterfactual(decision: DecisionRecord, alternate_option_name: str) -> CounterfactualComparison:
        """Compare actual outcome of winning option against hypothetical choice of alternate option."""
        chosen = next((a for a in decision.alternatives if a.name == decision.chosen_option), None)
        alt = next((a for a in decision.alternatives if a.name == alternate_option_name), None)

        if not chosen or not alt:
            raise ValueError(f"Could not locate options '{decision.chosen_option}' and '{alternate_option_name}'.")

        delta_cost = alt.estimated_cost - chosen.estimated_cost
        delta_benefit = alt.expected_benefit - chosen.expected_benefit

        variance = {
            "score_gap": round(chosen.weighted_total_score - alt.weighted_total_score, 2),
            "cost_difference": f"{'+' if delta_cost > 0 else ''}${delta_cost:,.2f}",
            "benefit_difference": f"{'+' if delta_benefit > 0 else ''}${delta_benefit:,.2f}",
            "original_risk": chosen.risk_level,
            "counterfactual_risk": alt.risk_level
        }

        risk_shift = f"Risk changes from {chosen.risk_level} to {alt.risk_level}."

        return CounterfactualComparison(
            decision_id=decision.id,
            original_option=chosen.name,
            counterfactual_option=alt.name,
            variance_analysis=variance,
            delta_cost=delta_cost,
            delta_benefit=delta_benefit,
            projected_risk_shift=risk_shift
        )

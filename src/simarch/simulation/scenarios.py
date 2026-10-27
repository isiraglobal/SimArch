"""SimArch Monte Carlo evaluation and scenario comparison."""

import statistics
from typing import Any, Dict, List
from simarch.db.database import DatabaseManager
from simarch.simulation.engine import SimulationEngine
from simarch.simulation.models import SimulationConfig, WorldState


class ScenarioAnalyzer:
    """Runs Monte Carlo evaluations and comparative scenario projections."""

    def __init__(self, db: DatabaseManager, sim_engine: SimulationEngine) -> None:
        self.db = db
        self.sim_engine = sim_engine

    def run_monte_carlo(
        self,
        project_id: str,
        base_config: SimulationConfig,
        iterations: int = 25
    ) -> Dict[str, Any]:
        """Perform Monte Carlo simulation over varied random seeds and report confidence intervals."""
        runs_outcomes = []
        survived_count = 0

        for i in range(iterations):
            run_cfg = base_config.model_copy(update={
                "random_seed": base_config.random_seed + i * 17,
                "name": f"{base_config.name} (Iter {i+1})"
            })
            result = self.sim_engine.run_simulation(project_id, run_cfg)
            outcomes = result["outcomes"]
            runs_outcomes.append(outcomes)
            if outcomes["survived"]:
                survived_count += 1

        final_cashes = [o["final_cash"] for o in runs_outcomes]
        final_revs = [o["final_monthly_revenue"] for o in runs_outcomes]
        final_custs = [o["final_customers"] for o in runs_outcomes]

        final_cashes.sort()
        final_revs.sort()

        p10_idx = max(0, int(0.10 * iterations))
        p50_idx = int(0.50 * iterations)
        p90_idx = min(iterations - 1, int(0.90 * iterations))

        return {
            "iterations": iterations,
            "survival_probability_pct": round((survived_count / iterations) * 100.0, 1),
            "cash_distribution": {
                "p10": round(final_cashes[p10_idx], 2),
                "median_p50": round(final_cashes[p50_idx], 2),
                "p90": round(final_cashes[p90_idx], 2),
                "mean": round(statistics.mean(final_cashes), 2)
            },
            "monthly_revenue_distribution": {
                "p10": round(final_revs[p10_idx], 2),
                "median_p50": round(final_revs[p50_idx], 2),
                "p90": round(final_revs[p90_idx], 2),
                "mean": round(statistics.mean(final_revs), 2)
            },
            "average_customers": int(statistics.mean(final_custs))
        }

    def compare_scenarios(
        self,
        project_id: str,
        scenarios: List[SimulationConfig]
    ) -> List[Dict[str, Any]]:
        """Run and compare multiple distinct strategic scenarios side-by-side."""
        comparisons = []
        for cfg in scenarios:
            res = self.sim_engine.run_simulation(project_id, cfg)
            comparisons.append({
                "scenario_name": cfg.name,
                "duration_days": cfg.duration_days,
                "marketing_budget": cfg.marketing_budget_monthly,
                "outcomes": res["outcomes"]
            })
        return comparisons

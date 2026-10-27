"""SimArch discrete-event simulation engine with reproducible seeds and causal feedback."""

import json
import random
from typing import Any, Dict, List, Optional
from simarch.core.types import generate_id, utc_now_iso
from simarch.db.database import DatabaseManager
from simarch.simulation.models import SimulationConfig, SimulationEvent, WorldState


class SimulationEngine:
    """Simulates business, operational, and organizational dynamics over time."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def run_simulation(
        self,
        project_id: str,
        config: SimulationConfig,
        initial_state: Optional[WorldState] = None,
        scheduled_events: Optional[List[SimulationEvent]] = None
    ) -> Dict[str, Any]:
        """Execute a reproducible discrete-event simulation over the configured timeline."""
        rng = random.Random(config.random_seed)
        state = initial_state or WorldState()
        events = sorted(scheduled_events or [], key=lambda e: e.event_time_days)

        history: List[Dict[str, Any]] = []
        current_time = 0.0
        step_days = 30.0  # Monthly simulation steps

        while current_time <= config.duration_days and state.cash > 0:
            # 1. Process any discrete events scheduled up to current_time
            for evt in events:
                if not evt.is_processed and evt.event_time_days <= current_time:
                    for metric, delta in evt.impact.items():
                        if hasattr(state, metric):
                            setattr(state, metric, getattr(state, metric) + delta)
                    evt.is_processed = True

            # 2. Causal Dynamics Feedback Loop
            # Burn rate calculation: Team salaries + marketing spend + overhead
            monthly_burn = (state.team_size * config.headcount_cost_monthly) + config.marketing_budget_monthly
            state.monthly_burn = monthly_burn

            # Customer acquisition: Marketing budget / CAC + organic multiplier based on product readiness
            organic_factor = 1.0 + (state.product_readiness_pct / 100.0)
            new_customers = int((config.marketing_budget_monthly / max(config.cac, 1.0)) * organic_factor * (1.0 + rng.uniform(-0.15, 0.15)))

            # Churn calculation
            churn_pct = max(0.5, config.base_churn_pct * (1.0 - (state.product_readiness_pct / 200.0)))
            state.churn_rate_pct = round(churn_pct, 2)
            churned = int(state.customers * (churn_pct / 100.0))

            state.customers = max(0, state.customers + new_customers - churned)
            state.monthly_revenue = state.customers * config.arpu

            # Net cash flow this step (30 days)
            net_flow = state.monthly_revenue - state.monthly_burn
            state.cash += net_flow

            # Runway in months
            net_burn = state.monthly_burn - state.monthly_revenue
            state.runway_months = round(state.cash / net_burn, 1) if net_burn > 0 else 999.0

            # Product progress
            state.product_readiness_pct = min(100.0, state.product_readiness_pct + (state.team_size * 1.5))
            state.market_share_pct = min(100.0, state.market_share_pct + (new_customers * 0.005))
            state.sim_time_days = current_time

            # Record state snapshot
            history.append({
                "day": current_time,
                "month": round(current_time / 30.0, 1),
                "cash": round(state.cash, 2),
                "monthly_revenue": round(state.monthly_revenue, 2),
                "monthly_burn": round(state.monthly_burn, 2),
                "customers": state.customers,
                "runway_months": state.runway_months,
                "product_readiness": round(state.product_readiness_pct, 1)
            })

            current_time += step_days

        outcomes = {
            "final_cash": round(state.cash, 2),
            "final_monthly_revenue": round(state.monthly_revenue, 2),
            "final_customers": state.customers,
            "final_product_readiness": round(state.product_readiness_pct, 1),
            "survived": state.cash > 0,
            "months_simulated": round(current_time / 30.0, 1)
        }

        # Persist simulation results
        sim_id = generate_id("sim")
        sql = """
        INSERT INTO simulations (id, project_id, name, starting_conditions_json, parameters_json, current_sim_time, max_sim_time, state_history_json, outcome_metrics_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (
            sim_id, project_id, config.name,
            json.dumps((initial_state or WorldState()).model_dump()),
            json.dumps(config.model_dump()),
            current_time, config.duration_days,
            json.dumps(history),
            json.dumps(outcomes),
            utc_now_iso()
        ))

        return {
            "simulation_id": sim_id,
            "config": config.model_dump(),
            "outcomes": outcomes,
            "history": history
        }

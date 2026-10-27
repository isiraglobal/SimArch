"""SimArch discrete-event world simulation models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.types import generate_id, utc_now_iso


class WorldState(BaseModel):
    """Simulated organizational and environmental state at a given point in time."""
    sim_time_days: float = 0.0
    cash: float = 100000.0
    monthly_revenue: float = 5000.0
    monthly_burn: float = 15000.0
    customers: int = 50
    team_size: int = 5
    product_readiness_pct: float = 30.0
    market_share_pct: float = 0.5
    churn_rate_pct: float = 4.0
    runway_months: float = 10.0
    custom_metrics: Dict[str, float] = Field(default_factory=dict)


class SimulationEvent(BaseModel):
    """Scheduled or triggered discrete event in the simulation timeline."""
    id: str = Field(default_factory=lambda: generate_id("sim_evt"))
    event_time_days: float
    name: str
    description: str
    impact: Dict[str, float] = Field(default_factory=dict)  # metric_name -> delta
    is_processed: bool = False


class SimulationConfig(BaseModel):
    """Configuration and initial parameters for a simulation run."""
    id: str = Field(default_factory=lambda: generate_id("sim_cfg"))
    name: str
    duration_days: float = 365.0
    random_seed: int = 42
    cac: float = 200.0  # Customer Acquisition Cost
    arpu: float = 100.0  # Average Revenue Per User/Month
    headcount_cost_monthly: float = 8000.0  # per person
    marketing_budget_monthly: float = 5000.0
    base_churn_pct: float = 3.5

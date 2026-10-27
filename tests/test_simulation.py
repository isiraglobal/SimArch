"""Tests for Simulation Architecture, Reproducibility, and Monte Carlo (Item 12)."""

import pytest
from simarch.db.database import DatabaseManager
from simarch.simulation.engine import SimulationEngine
from simarch.simulation.models import SimulationConfig, WorldState
from simarch.simulation.scenarios import ScenarioAnalyzer


def test_simulation_reproducibility(temp_db: DatabaseManager, sim_engine: SimulationEngine):
    """Verify discrete-event simulations with identical random seeds yield byte-identical outcomes."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO projects (id, org_id, name, objective, created_at, updated_at) VALUES ('p1', 'org1', 'P1', 'O1', '', '')")

    cfg1 = SimulationConfig(name="Sim 1", duration_days=180.0, random_seed=12345, marketing_budget_monthly=4000.0)
    cfg2 = SimulationConfig(name="Sim 2", duration_days=180.0, random_seed=12345, marketing_budget_monthly=4000.0)

    res1 = sim_engine.run_simulation("p1", cfg1)
    res2 = sim_engine.run_simulation("p1", cfg2)

    assert res1["outcomes"]["final_cash"] == res2["outcomes"]["final_cash"]
    assert res1["outcomes"]["final_customers"] == res2["outcomes"]["final_customers"]
    assert res1["outcomes"]["final_monthly_revenue"] == res2["outcomes"]["final_monthly_revenue"]
    assert len(res1["history"]) == len(res2["history"])


def test_simulation_causal_feedback(temp_db: DatabaseManager, sim_engine: SimulationEngine):
    """Verify higher marketing investment causally increases customer count and revenue."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO projects (id, org_id, name, objective, created_at, updated_at) VALUES ('p1', 'org1', 'P1', 'O1', '', '')")

    low_growth = SimulationConfig(name="Low Growth", duration_days=90.0, random_seed=42, marketing_budget_monthly=1000.0)
    high_growth = SimulationConfig(name="High Growth", duration_days=90.0, random_seed=42, marketing_budget_monthly=8000.0)

    res_low = sim_engine.run_simulation("p1", low_growth)
    res_high = sim_engine.run_simulation("p1", high_growth)

    assert res_high["outcomes"]["final_customers"] > res_low["outcomes"]["final_customers"]
    assert res_high["outcomes"]["final_monthly_revenue"] > res_low["outcomes"]["final_monthly_revenue"]


def test_monte_carlo_evaluation(temp_db: DatabaseManager, sim_engine: SimulationEngine):
    """Verify Monte Carlo runner computes distribution percentiles (p10, p50, p90)."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO projects (id, org_id, name, objective, created_at, updated_at) VALUES ('p1', 'org1', 'P1', 'O1', '', '')")

    analyzer = ScenarioAnalyzer(temp_db, sim_engine)
    base_cfg = SimulationConfig(name="Base", duration_days=60.0, random_seed=100)
    mc_results = analyzer.run_monte_carlo("p1", base_cfg, iterations=10)

    assert mc_results["iterations"] == 10
    assert "cash_distribution" in mc_results
    assert mc_results["cash_distribution"]["p10"] <= mc_results["cash_distribution"]["median_p50"]
    assert mc_results["cash_distribution"]["median_p50"] <= mc_results["cash_distribution"]["p90"]

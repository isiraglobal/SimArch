"""Tests for Decision Intelligence, Graph, and Counterfactuals (Items 10 & 18)."""

import pytest
from simarch.core.types import DecisionStatus
from simarch.db.database import DatabaseManager
from simarch.decision.counterfactual import CounterfactualAnalyzer
from simarch.decision.graph import DecisionGraphEngine
from simarch.decision.intelligence import DecisionIntelligence
from simarch.decision.models import DecisionAlternative, DecisionRecord, EvaluationCriterion


def test_decision_evaluation_and_rationale(temp_db: DatabaseManager, decision_intel: DecisionIntelligence):
    """Verify decision scoring ranks alternatives by weighted criteria and generates rationale."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO roles (id, org_id, title, role_type, mission, created_at) VALUES ('r1', 'org1', 'Lead', 'specialist', 'M', '')")
    temp_db.execute("INSERT INTO projects (id, org_id, name, objective, created_at, updated_at) VALUES ('p1', 'org1', 'P1', 'O1', '', '')")

    dec = DecisionRecord(
        project_id="p1",
        org_id="org1",
        owner_role_id="r1",
        objective="Choose cloud provider",
        criteria=[
            EvaluationCriterion(name="Cost", weight=0.6, description="Monthly expense"),
            EvaluationCriterion(name="Reliability", weight=0.4, description="SLA uptime")
        ],
        alternatives=[
            DecisionAlternative(
                name="Provider A",
                description="Low cost, standard reliability",
                estimated_cost=100.0,
                expected_benefit=1000.0,
                risk_level="low",
                scores={"Cost": 9.0, "Reliability": 8.0}
            ),
            DecisionAlternative(
                name="Provider B",
                description="High cost, maximum reliability",
                estimated_cost=500.0,
                expected_benefit=1100.0,
                risk_level="medium",
                scores={"Cost": 4.0, "Reliability": 9.5}
            )
        ]
    )

    evaluated = decision_intel.evaluate_and_select(dec)
    assert evaluated.chosen_option == "Provider A"
    assert evaluated.status == DecisionStatus.SELECTED
    assert "Provider A" in evaluated.reasons_for_selection
    assert evaluated.alternatives[1].rejected_reason is not None


def test_decision_graph_and_binary_tree(temp_db: DatabaseManager, decision_intel: DecisionIntelligence, decision_graph: DecisionGraphEngine):
    """Verify decision graph linking and binary alternative tree representation."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO roles (id, org_id, title, role_type, mission, created_at) VALUES ('r1', 'org1', 'Lead', 'specialist', 'M', '')")
    temp_db.execute("INSERT INTO projects (id, org_id, name, objective, created_at, updated_at) VALUES ('p1', 'org1', 'P1', 'O1', '', '')")

    d1 = DecisionRecord(
        id="d1",
        project_id="p1",
        org_id="org1",
        owner_role_id="r1",
        objective="Root Strategic Decision",
        criteria=[EvaluationCriterion(name="Value", weight=1.0, description="V")],
        alternatives=[
            DecisionAlternative(name="Option 1", description="Opt 1", scores={"Value": 9.0}),
            DecisionAlternative(name="Option 2", description="Opt 2", scores={"Value": 6.0})
        ]
    )
    decision_intel.evaluate_and_select(d1)

    # Binary tree view
    branch = decision_graph.get_binary_tree_view(d1)
    assert branch is not None
    assert branch.selected_option == "Option 1"
    assert branch.rejected_option == "Option 2"
    assert "Option 2" in branch.flip_condition


def test_counterfactual_analysis():
    """Verify counterfactual analysis compares winning option against runner-up."""
    dec = DecisionRecord(
        id="d1",
        project_id="p1",
        org_id="org1",
        owner_role_id="r1",
        objective="Strategy Selection",
        chosen_option="Alpha",
        alternatives=[
            DecisionAlternative(name="Alpha", description="A", estimated_cost=100.0, expected_benefit=500.0, risk_level="low", weighted_total_score=8.5),
            DecisionAlternative(name="Beta", description="B", estimated_cost=300.0, expected_benefit=600.0, risk_level="high", weighted_total_score=6.0)
        ]
    )

    comparison = CounterfactualAnalyzer.compare_counterfactual(dec, "Beta")
    assert comparison.delta_cost == 200.0
    assert comparison.delta_benefit == 100.0
    assert "Risk changes from low to high" in comparison.projected_risk_shift

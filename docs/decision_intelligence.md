# SimArch Decision Intelligence Engine

## 1. Overview
Material corporate decisions require auditable, inspectable records. SimArch records the full evaluation graph for every strategic decision, answering:
- What alternatives were evaluated?
- What criteria and weights were applied?
- Why did the winning choice win?
- What trade-offs were accepted?
- What conditions would flip the decision?
- What is the counterfactual delta if an alternate option were selected?

---

## 2. Decision Record Structure

Each decision record (`DecisionRecord`) captures:
- `id`: Unique identifier (e.g., `dec_2c7db4625edd`).
- `owner_role_id`: Role responsible for making the decision.
- `objective`: Problem statement or strategic goal.
- `criteria`: List of weighted evaluation criteria ($\sum w_i = 1.0$).
- `alternatives`: Evaluated options with score breakdowns ($s_i \in [0, 10]$), cost, expected benefit, and risk tier.
- `chosen_option`: Winning alternative name.
- `reasons_for_selection`: Explicit, grounded explanation of utility score superiority.
- `status`: Lifecycle state (`PROPOSED`, `EVALUATING`, `SELECTED`, `RECONSIDERED`, `OVERRULED`).

---

## 3. Binary Decision Tree View

When comparing two primary alternatives, SimArch renders a binary branch:

```text
[ Root: Strategic Architecture Selection ]
   │
   ├── [ SELECTED ] Option A: SQLite WAL & Thread-Safe Leases (Score: 9.33)
   │     • High simplicity, zero cluster operations, ACID compliant.
   │
   └── [ REJECTED ] Option B: Distributed Multi-Node Cluster (Score: 5.50)
         • Trade-off: High operational overhead and cost ($15,000/yr).
         • Flip Condition: If Option B cost drops by >$15,000 or risk drops to low.
```

---

## 4. Counterfactual Analysis

The counterfactual analyzer compares the chosen option against any rejected option without needing to rerun history:
- **Cost Delta**: $\Delta \text{Cost} = \text{Cost}_{\text{alt}} - \text{Cost}_{\text{chosen}}$
- **Benefit Delta**: $\Delta \text{Benefit} = \text{Benefit}_{\text{alt}} - \text{Benefit}_{\text{chosen}}$
- **Risk Shift**: Reports qualitative movement (e.g. "Risk changes from low to high").

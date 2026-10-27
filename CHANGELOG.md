# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-27

### Added
- **Organization Engine**: Dynamic workforce formation synthesizing proportionate corporate roles (CEO, Coordinator, Lead Engineer, Research Specialist, Quality Auditor) with enforceable contracts and permissions.
- **Workforce Execution Engine**: Strict 10-state task lifecycle (`PROPOSED -> READY -> ASSIGNED -> RUNNING -> REVIEW -> COMPLETED`), DAG dependency resolution, topological unblocking, and circular dependency detection.
- **Persistent Job Scheduler**: SQLite WAL storage with atomic worker leases (30s duration), heartbeats, and automatic crash recovery.
- **Independent Review Engine**: Rigorous audit of deliverables and evidence against formal acceptance criteria with actionable revision tracking.
- **Scoped Memory System**: Domain isolation across Organization, Department, Project, Employee, and Task scopes with contradiction detection and token-budget context assembly.
- **Decision Intelligence Engine**: Directed decision graphs, multi-criteria scoring, grounded winning rationales, binary decision tree comparison, and counterfactual delta analysis.
- **Discrete-Event Simulation**: Time-compressed business dynamics simulator with causal feedback loops (burn, revenue, churn, CAC, product progress) and Monte Carlo confidence intervals ($P_{10}, P_{50}, P_{90}$).
- **Model Router & Deterministic Local Provider**: 100% offline zero-cost execution engine with graceful fallback for external model keys.
- **Operational Web Dashboard**: Dark-mode operational console served via FastAPI with live polling, role tables, task graphs, decision inspections, and simulation triggers.
- **Typer CLI**: Headless command-line interface with `init`, `org`, `project`, `decision`, `sim`, `smoke-test`, and `serve` commands.
- **First Organization Demo**: Comprehensive reproducible end-to-end smoke test validating all core platform subsystems.

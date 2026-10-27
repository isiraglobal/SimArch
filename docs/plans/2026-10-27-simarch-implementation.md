# SimArch Implementation Plan

> **For SimArch Build:** End-to-end autonomous implementation of SimArch platform.

**Goal:** Build SimArch: an open-source platform for autonomous AI organizations, persistent digital workforces, decision intelligence, and time-compressed world simulation.

**Architecture:** Modular monolith in Python 3.13 with SQLite persistent store, durable background scheduler, state machine execution engine, scoped memory system, decision intelligence with DAG/binary alternative trees, discrete-event simulation engine with Monte Carlo evaluation, pluggable model router with deterministic zero-cost default, and an integrated FastAPI dashboard and CLI.

**Tech Stack:** Python 3.13, Pydantic v2, SQLite (WAL mode, foreign keys, ACID leases), Typer/Rich for CLI, FastAPI/Uvicorn for API & Dashboard, PyYAML, Pytest & Pytest-Asyncio.

---

## Phase 1: Foundation & Core Repositories
- Git setup, `.gitignore`, `.editorconfig`, `pyproject.toml`, package configuration.
- `src/simarch/core`: Configuration, domain models, UUIDs, timestamps, event bus, base contracts.
- `src/simarch/db`: SQLite database manager with WAL mode, transactions, schema initialization, migrations, and atomic lease operations.

## Phase 2: Organization Engine & Dynamic Workforce
- `src/simarch/org`: Role definitions, Role contracts (identity, permissions, budget limits, escalation, reporting relationships), Organization hierarchy, Department structure.
- Workforce formation planner: objective interpretation -> capability decomposition -> organization graph construction -> role instantiation -> budget allocation.
- Runtime permission validator preventing privilege escalation.

## Phase 3: Workforce Execution & Long-Running Engine
- `src/simarch/execution`: Task domain model (10+ states: PROPOSED, READY, ASSIGNED, RUNNING, REVIEW, COMPLETED, BLOCKED, FAILED, CANCELLED, RETRYING).
- Dependency resolver (DAG execution, topological sort, unblocking).
- Persistent scheduler, worker heartbeats, lease management, idempotency keys, crash recovery.
- Manager delegation, deliverable inspection, independent review / revision cycle with actionable feedback.
- Cross-functional messaging (structured inter-agent communications, bounded recursion/depth).

## Phase 4: Company Memory & Context Management
- `src/simarch/memory`: Scoped memory hierarchy (Organization, Department, Project, Employee, Task, Decision, Evidence).
- Relevance retrieval, token-budget context assembly, provenance tracking, contradiction detection, retention policies.

## Phase 5: Decision Intelligence Engine
- `src/simarch/decision`: Decision records (objective, alternatives, criteria, weights, scores, risks, chosen option, rejected options, audit evidence).
- Directed decision graphs and binary alternative trees.
- "Why a decision won" evaluator.
- Counterfactual scenario comparison against checkpoints.

## Phase 6: Simulation Architecture & Discrete-Event Engine
- `src/simarch/simulation`: Discrete-event simulation runner, simulated clock (time compression: minutes, months, years), versioned world state, event queues.
- Causal models: connected variables (demand, conversion, retention, staffing, burn, runway).
- Monte Carlo evaluations, reproducible random seeds, sensitivity analysis, scenario comparison.

## Phase 7: Model Router, Skills, Workspaces & Self-Learning
- `src/simarch/models`: Registry, latency/cost/capability routing, fallback logic, deterministic local provider (100% operational offline without keys) + external provider connectors (OpenAI/Anthropic/Gemini).
- `src/simarch/skills`: Skill registry with manifests, validation, permissions, and tool dispatch.
- `src/simarch/workspace`: Temporary workspace manager, lifecycle (`CREATED -> ACTIVE -> CHECKPOINTED -> CLEANUP_ELIGIBLE -> DELETED`), artifact preservation.
- `src/simarch/learning`: 5 adaptation mechanisms (company adaptation, performance-based staffing, workflow capture, trend awareness, controlled self-improvement loop: `OBSERVE -> PROPOSE -> EVALUATE -> APPROVE -> VERSION -> DEPLOY -> MONITOR -> ROLLBACK`).

## Phase 8: CLI, API & Operational Dashboard
- `src/simarch/cli.py`: Complete CLI with `simarch init`, `org`, `project`, `task`, `decision`, `sim`, `serve`.
- `src/simarch/api`: REST API endpoints with full OpenAPI documentation.
- `src/simarch/ui`: Dense, dark-themed operational dashboard (Overview, Organization, Projects, Live Ops, Decision Intelligence, Simulation, Learning, Governance).

## Phase 9: Verification & Testing Suite
- Comprehensive tests for all 20 required verification domains: unit, integration, and recovery tests.
- `examples/first_organization`: End-to-end reproducible demonstration.

## Phase 10: Clean GitHub Release & Documentation
- `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`, `CITATION.cff`, `.env.example`, `.github/workflows/ci.yml`.
- Verify cleanliness, zero stray caches, working installation and packaging.

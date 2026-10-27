# SimArch CLI Command Reference

The `simarch` command-line utility provides complete headless control over all platform subsystems.

---

## Global Commands

### `simarch version`
Display the installed SimArch version.
```bash
simarch version
```

### `simarch init [--path PATH]`
Initialize a fresh local SimArch database, schema, and workspaces.
```bash
simarch init
simarch init --path ./my_workspace
```

### `simarch smoke-test`
Run the complete, reproducible `first_organization` end-to-end smoke test verifying organization formation, task DAG unblocking, deliverable auditing, decision intelligence, and process restart recovery.
```bash
simarch smoke-test
```

### `simarch serve [--host HOST] [--port PORT]`
Launch the operational web dashboard and REST API service.
```bash
simarch serve --port 8400
```

---

## Organization Commands (`simarch org`)

### `simarch org create`
Synthesize an autonomous organization from a high-level mission statement.
```bash
simarch org create --name "Apex Labs" --objective "Research autonomous AI systems" --scale standard
```

### `simarch org list`
List all persisted organizations and executive leadership.
```bash
simarch org list
```

---

## Project Commands (`simarch project`)

### `simarch project start`
Launch a new strategic initiative within an organization.
```bash
simarch project start --org org_12345 --name "MVP Sprint" --objective "Release v0.1.0" --budget 5000.0
```

### `simarch project status <project-id>`
Display real-time task states, dependencies, worker leases, and budget spent.
```bash
simarch project status proj_abcde
```

### `simarch project pause <project-id>`
Pause task scheduling and worker leases for a project.
```bash
simarch project pause proj_abcde
```

### `simarch project resume <project-id>`
Resume execution for a paused project.
```bash
simarch project resume proj_abcde
```

---

## Decision Commands (`simarch decision`)

### `simarch decision inspect <decision-id>`
Display multi-criteria utility scores, winning rationale, and binary tree view for a decision.
```bash
simarch decision inspect dec_98765
```

---

## Simulation Commands (`simarch sim`)

### `simarch sim run`
Execute a discrete-event business simulation over a specified number of days.
```bash
simarch sim run --name "Year 1 Model" --duration 365 --marketing 6000
```

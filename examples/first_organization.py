#!/usr/bin/env python3
"""SimArch - First Organization Executable Example.

Demonstrates:
1. Dynamic workforce formation based on a business objective.
2. Generation of proportionate role contracts with enforced decision and tool boundaries.
3. Task dependency DAG creation and topological unblocking.
4. Bounded execution with concrete deliverables and evidence.
5. Independent review and approval protocol.
6. Multi-criteria decision intelligence with winning rationale and binary alternative tree.
7. Discrete-event world simulation with causal feedback loops.
8. Persistence to SQLite WAL database and crash recovery validation across process restarts.
"""

import sys
from pathlib import Path

# Add src to sys.path so it runs directly without installation
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from simarch.execution.smoke_test import run_first_organization_smoke_test


def main():
    demo_db = ROOT_DIR / "simarch_demo.db"
    if demo_db.exists():
        demo_db.unlink()

    try:
        results = run_first_organization_smoke_test(demo_db)
        print("Execution Result:", results)
    finally:
        if demo_db.exists():
            demo_db.unlink()


if __name__ == "__main__":
    main()

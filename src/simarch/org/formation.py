"""SimArch dynamic workforce formation planner."""

import json
from typing import List, Optional
from simarch.core.types import RoleType, generate_id, utc_now_iso
from simarch.db.database import DatabaseManager
from simarch.org.models import Department, Organization, RoleContract


class WorkforceFormationPlanner:
    """Analyzes an organizational objective and synthesizes a proportionate workforce."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def synthesize_organization(self, name: str, objective: str, scale: str = "auto") -> Organization:
        """Form a tailored organization from an objective statement."""
        objective_lower = objective.lower()

        # Determine scale if auto
        if scale == "auto":
            words = len(objective.split())
            if any(k in objective_lower for k in ["enterprise", "global", "multi-department", "5-year", "full company"]):
                scale = "enterprise"
            elif any(k in objective_lower for k in ["product", "release", "system", "architecture", "build"]):
                scale = "standard"
            else:
                scale = "compact"

        org_id = generate_id("org")
        org = Organization(id=org_id, name=name, mission=objective)

        # Domain classification
        is_software = any(k in objective_lower for k in ["software", "code", "app", "release", "build", "system", "bug"])
        is_research = any(k in objective_lower for k in ["research", "market", "study", "analyze", "hypothesis", "survey"])
        is_finance = any(k in objective_lower for k in ["finance", "budget", "cost", "investment", "forecast", "revenue"])

        # 1. Executive / Coordinator Role
        exec_title = "Chief Executive Officer" if scale != "compact" else "Project Coordinator"
        ceo_id = generate_id("role")
        ceo = RoleContract(
            id=ceo_id,
            org_id=org_id,
            title=exec_title,
            role_type=RoleType.EXECUTIVE if scale != "compact" else RoleType.COORDINATOR,
            mission=f"Lead and coordinate organization towards: {objective}",
            responsibilities=[
                "Decompose high-level mission into departmental directives",
                "Approve strategic decisions and budget allocations",
                "Ensure organizational alignment and resolve escalations"
            ],
            decision_authority=["*"],
            tool_permissions=["*"],
            information_access=["*"],
            budget_limit=10000.0,
            delegation_permissions=["*"],
            max_delegation_depth=4,
            review_required=False
        )
        org.roles[ceo.id] = ceo

        # 2. Functional Specialists & Leadership based on scale and domain
        if scale == "compact":
            # Compact: Coordinator + 2 Specialists + 1 Reviewer
            if is_software:
                spec_title = "Lead Software Engineer"
                spec_mission = "Design, implement, and verify software deliverables."
                spec_tools = ["write_code", "run_tests", "fs_read", "fs_write", "git_commit"]
            elif is_research:
                spec_title = "Lead Research Analyst"
                spec_mission = "Investigate target domains, gather evidence, and synthesize findings."
                spec_tools = ["web_search", "document_read", "data_analyze", "fs_write"]
            else:
                spec_title = "Operations Specialist"
                spec_mission = "Execute core operational tasks and deliver structured findings."
                spec_tools = ["data_analyze", "fs_write", "doc_generate"]

            spec_id = generate_id("role")
            spec = RoleContract(
                id=spec_id,
                org_id=org_id,
                title=spec_title,
                role_type=RoleType.SPECIALIST,
                reports_to_id=ceo.id,
                mission=spec_mission,
                responsibilities=["Execute assigned tasks", "Produce verifiable evidence and artifacts"],
                decision_authority=["technical_implementation", "task_execution"],
                tool_permissions=spec_tools,
                budget_limit=2500.0,
                review_required=True
            )
            org.roles[spec.id] = spec

            # Independent Auditor / QA
            qa_id = generate_id("role")
            qa = RoleContract(
                id=qa_id,
                org_id=org_id,
                title="Quality & Verification Auditor",
                role_type=RoleType.AUDITOR,
                reports_to_id=ceo.id,
                mission="Independently review deliverables against stated acceptance criteria.",
                responsibilities=["Inspect deliverables", "Verify test results", "Approve or reject submissions"],
                decision_authority=["deliverable_review", "compliance_signoff"],
                tool_permissions=["fs_read", "verify_deliverable", "run_tests"],
                budget_limit=1000.0,
                review_required=False
            )
            org.roles[qa.id] = qa

        else:
            # Standard / Enterprise Structure
            cto_id = generate_id("role")
            cto = RoleContract(
                id=cto_id,
                org_id=org_id,
                title="Chief Technology Officer",
                role_type=RoleType.EXECUTIVE,
                reports_to_id=ceo.id,
                mission="Architect scalable technical systems and lead engineering execution.",
                responsibilities=["Define technology roadmap", "Supervise engineers", "Enforce code standards"],
                decision_authority=["architecture_selection", "toolchain_approval"],
                tool_permissions=["fs_read", "fs_write", "run_tests", "git_commit"],
                budget_limit=5000.0,
                delegation_permissions=["Senior Software Engineer", "DevOps Engineer"],
                max_delegation_depth=3,
                review_required=False
            )
            org.roles[cto.id] = cto

            eng_id = generate_id("role")
            eng = RoleContract(
                id=eng_id,
                org_id=org_id,
                title="Senior Software Engineer",
                role_type=RoleType.SPECIALIST,
                reports_to_id=cto.id,
                mission="Implement modular, tested, production-grade components.",
                responsibilities=["Write code", "Author tests", "Generate release artifacts"],
                decision_authority=["code_structure"],
                tool_permissions=["write_code", "run_tests", "fs_read", "fs_write"],
                budget_limit=2000.0,
                review_required=True
            )
            org.roles[eng.id] = eng

            cpo_id = generate_id("role")
            cpo = RoleContract(
                id=cpo_id,
                org_id=org_id,
                title="Chief Product Officer",
                role_type=RoleType.EXECUTIVE,
                reports_to_id=ceo.id,
                mission="Define product vision, user requirements, and market research strategy.",
                responsibilities=["Synthesize user requirements", "Validate product-market fit"],
                decision_authority=["feature_prioritization", "release_criteria"],
                tool_permissions=["web_search", "document_read", "fs_write"],
                budget_limit=4000.0,
                review_required=False
            )
            org.roles[cpo.id] = cpo

            qa_id = generate_id("role")
            qa = RoleContract(
                id=qa_id,
                org_id=org_id,
                title="Compliance & Quality Auditor",
                role_type=RoleType.AUDITOR,
                reports_to_id=ceo.id,
                mission="Independently review all deliverables and code against acceptance criteria.",
                responsibilities=["Perform audit reviews", "Verify evidence", "Sign off on releases"],
                decision_authority=["deliverable_review", "security_audit"],
                tool_permissions=["fs_read", "run_tests", "verify_deliverable"],
                budget_limit=1500.0,
                review_required=False
            )
            org.roles[qa.id] = qa

        # Persist organization and roles to database
        self.persist_organization(org)
        return org

    def persist_organization(self, org: Organization) -> None:
        """Save organization and its roles to the database."""
        with self.db.transaction() as cur:
            cur.execute("""
            INSERT OR REPLACE INTO organizations (id, name, mission, governance_model, structure_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                org.id,
                org.name,
                org.mission,
                org.governance_model,
                json.dumps([d.model_dump() for d in org.departments]),
                org.created_at,
                org.updated_at
            ))

            for role in org.roles.values():
                cur.execute("""
                INSERT OR REPLACE INTO roles (
                    id, org_id, title, role_type, reports_to_id, mission,
                    responsibilities_json, decision_authority_json, tool_permissions_json,
                    budget_limit, max_delegation_depth, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    role.id,
                    role.org_id,
                    role.title,
                    role.role_type.value,
                    role.reports_to_id,
                    role.mission,
                    json.dumps(role.responsibilities),
                    json.dumps(role.decision_authority),
                    json.dumps(role.tool_permissions),
                    role.budget_limit,
                    role.max_delegation_depth,
                    role.created_at
                ))

    def load_organization(self, org_id: str) -> Optional[Organization]:
        """Load an organization and its roles from the database."""
        org_row = self.db.fetch_one("SELECT * FROM organizations WHERE id = ?", (org_id,))
        if not org_row:
            return None

        org = Organization(
            id=org_row["id"],
            name=org_row["name"],
            mission=org_row["mission"],
            governance_model=org_row["governance_model"],
            created_at=org_row["created_at"],
            updated_at=org_row["updated_at"]
        )

        role_rows = self.db.fetch_all("SELECT * FROM roles WHERE org_id = ?", (org_id,))
        for r in role_rows:
            contract = RoleContract(
                id=r["id"],
                org_id=r["org_id"],
                title=r["title"],
                role_type=RoleType(r["role_type"]),
                reports_to_id=r["reports_to_id"],
                mission=r["mission"],
                responsibilities=json.loads(r["responsibilities_json"]),
                decision_authority=json.loads(r["decision_authority_json"]),
                tool_permissions=json.loads(r["tool_permissions_json"]),
                budget_limit=r["budget_limit"],
                max_delegation_depth=r["max_delegation_depth"],
                created_at=r["created_at"]
            )
            org.roles[contract.id] = contract

        return org

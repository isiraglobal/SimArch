"""SimArch relevance-based memory retrieval and context assembly."""

import re
from typing import List, Optional
from simarch.core.types import MemoryScope
from simarch.db.database import DatabaseManager
from simarch.memory.scoped_memory import MemoryEntry, ScopedMemoryEngine


class ContextAssembler:
    """Assembles relevance-filtered, budget-constrained context packets for workers."""

    def __init__(self, db: DatabaseManager, memory_engine: ScopedMemoryEngine) -> None:
        self.db = db
        self.memory_engine = memory_engine

    def assemble_context(
        self,
        org_id: str,
        project_id: str,
        query: str,
        role_id: str,
        max_tokens: int = 1500
    ) -> str:
        """Retrieve relevant memories across permitted scopes and format within token limit."""
        # Query words
        tokens = set(re.findall(r"\w+", query.lower()))

        # Fetch candidate memories from Org, Project, and Role scopes
        candidates: List[MemoryEntry] = []
        candidates.extend(self.memory_engine.get_scoped_memories(org_id, MemoryScope.ORGANIZATION, org_id))
        candidates.extend(self.memory_engine.get_scoped_memories(org_id, MemoryScope.PROJECT, project_id))
        candidates.extend(self.memory_engine.get_scoped_memories(org_id, MemoryScope.EMPLOYEE, role_id))

        # Score candidates based on term overlap and provenance relevance
        scored: List[tuple[float, MemoryEntry]] = []
        for entry in candidates:
            entry_words = set(re.findall(r"\w+", entry.content.lower() + " " + entry.key.lower()))
            overlap = len(tokens.intersection(entry_words))
            score = float(overlap)
            if entry.contradiction_flag:
                score *= 0.5  # Penalize contradictory entries
            scored.append((score, entry))

        # Sort by relevance descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Budget-capped assembly (estimating ~4 chars per token)
        char_budget = max_tokens * 4
        current_chars = 0
        assembled_sections: List[str] = []

        for score, entry in scored:
            section = f"[{entry.scope.value.upper()}: {entry.key}]\n{entry.content}\n"
            if entry.provenance:
                section += f"(Source: {entry.provenance.get('source', 'internal')})\n"

            if current_chars + len(section) > char_budget:
                break

            assembled_sections.append(section)
            current_chars += len(section)

        if not assembled_sections:
            return "No prior relevant organizational memories found."

        return "\n---\n".join(assembled_sections)

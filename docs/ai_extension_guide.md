# SimArch AI Extension & Localhost Locking Guide

## 1. Overview

SimArch can be hardwired directly as an extension into modern AI tools and agents, including:
- **Claude Code & Claude Desktop** (via Model Context Protocol stdio server)
- **Cursor & Windsurf IDEs** (via `.cursor/mcp.json` or `.mcp.json`)
- **Google Antigravity / Gemini Agents** (via MCP and direct tool calling)
- **Python Autonomous Agents** (LangChain, CrewAI, AutoGen, LlamaIndex, or raw LLM function calling via `SimArchAIExtension`)

---

## 2. Localhost Locking Policy

### Why is Localhost Locked by Default?
In automated multi-agent environments, running a background web server that listens on localhost (`127.0.0.1:8400`) creates unnecessary socket overhead, port conflicts, and security exposure when the AI agent is operating headlessly.

### How the AI Agent Decides
SimArch locks localhost down by default:
- **Zero open ports** listening on the host machine.
- All operations (organization formation, task DAGs, decision intelligence, discrete-event simulations) execute purely **in-process or over standard I/O (stdio)**.
- If and only if the AI agent determines that a human operator needs visual dashboard inspection, the agent can call:
  ```json
  {
    "name": "simarch_toggle_localhost",
    "arguments": {
      "enable": true,
      "port": 8400
    }
  }
  ```
- When the human inspection is complete or the workflow finishes, the agent can call `simarch_toggle_localhost(enable=false)` to immediately release the socket and lock localhost down again.

---

## 3. Hardwiring as an MCP Extension

### Option A: Configuration File (Zero-Code)
Place a `.mcp.json` file in your repository root, or configure `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "simarch": {
      "command": "simarch-mcp",
      "args": []
    }
  }
}
```

Or when running via the `simarch` CLI:
```json
{
  "mcpServers": {
    "simarch": {
      "command": "simarch",
      "args": ["mcp"]
    }
  }
}
```

### Option B: Available MCP Tools for the AI Agent

| Tool Name | Purpose |
| :--- | :--- |
| `simarch_form_organization` | Synthesizes an autonomous AI organization with roles, contracts, and authority. |
| `simarch_create_task` | Creates an accountable work task in the DAG with acceptance criteria and dependencies. |
| `simarch_submit_deliverable` | Submits deliverable findings and concrete verification evidence. |
| `simarch_evaluate_decision` | Scores multi-criteria decision alternatives, outputs winning rationale and binary tree. |
| `simarch_run_simulation` | Runs time-compressed discrete-event world simulation with causal feedback loops. |
| `simarch_toggle_localhost` | **AI Agent controls localhost**: starts/stops the local HTTP dashboard on demand. |

---

## 4. Python Agent SDK Usage

Any Python AI agent or script can import and use the extension directly without any server or network calls:

```python
from simarch.extension import SimArchAIExtension

# Initialize extension
ext = SimArchAIExtension()

# 1. Form organization
org = ext.form_organization(
    name="Vanguard Intelligence",
    objective="Autonomous security audit and compliance reporting",
    scale="compact"
)

# 2. Add accountable task
task = ext.create_task(
    project_id="proj_alpha",
    org_id=org["org_id"],
    assigned_role_id=org["roles"][1]["id"],
    objective="Audit authentication gateway for privilege escalation",
    acceptance_criteria=["Zero unauthorized role elevations", "Pass regression suite"]
)

# 3. Multi-criteria decision intelligence
decision = ext.evaluate_decision(
    project_id="proj_alpha",
    org_id=org["org_id"],
    owner_role_id=org["roles"][0]["id"],
    objective="Select encryption protocol",
    criteria=[{"name": "Security", "weight": 0.6, "description": "Strength"}],
    alternatives=[
        {"name": "ChaCha20-Poly1305", "description": "Fast AEAD", "scores": {"Security": 9.5}},
        {"name": "AES-256-GCM", "description": "Hardware accelerated", "scores": {"Security": 9.5}}
    ]
)
print("Winning Choice:", decision["chosen_option"])

# 4. Localhost remains locked until agent decides:
status = ext.get_localhost_status()
print("Localhost status:", status)  # {'active': False, 'locked': True}

# If agent decides visual report is helpful for a human:
ext.toggle_localhost(enable=True, port=8400)
# ... human reviews at http://127.0.0.1:8400 ...
# Agent locks it down:
ext.toggle_localhost(enable=False)
```

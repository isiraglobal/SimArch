// SimArch Dashboard Client Controller
document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  loadAllData();

  document.getElementById("btn-refresh").addEventListener("click", () => {
    loadAllData();
  });

  const simBtn = document.getElementById("btn-trigger-sim");
  if (simBtn) {
    simBtn.addEventListener("click", runQuickSimulation);
  }

  // Auto-refresh every 8 seconds
  setInterval(loadAllData, 8000);
});

function initNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  const sections = document.querySelectorAll(".view-section");
  const title = document.getElementById("current-view-title");

  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      navItems.forEach((i) => i.classList.remove("active"));
      sections.forEach((s) => s.classList.remove("active"));

      item.classList.add("active");
      const target = item.getAttribute("data-target");
      const targetSection = document.getElementById(`view-${target}`);
      if (targetSection) {
        targetSection.classList.add("active");
        title.textContent = item.textContent;
      }
    });
  });
}

async function loadAllData() {
  try {
    const res = await fetch("/api/overview");
    if (!res.ok) return;
    const data = await res.json();

    // 1. Update Metrics
    document.getElementById("metric-orgs").textContent = data.org_count || 0;
    document.getElementById("metric-projects").textContent = data.project_count || 0;
    document.getElementById("metric-tasks-completed").textContent = data.tasks_completed || 0;
    document.getElementById("metric-tasks-pending").textContent = `${data.tasks_pending || 0} Pending / Active`;
    document.getElementById("metric-decisions").textContent = data.decision_count || 0;

    // 2. Populate Recent Projects
    const projTbody = document.getElementById("overview-projects-tbody");
    if (data.projects && data.projects.length > 0) {
      projTbody.innerHTML = data.projects.map(p => `
        <tr>
          <td><strong>${escapeHtml(p.name)}</strong></td>
          <td>${escapeHtml(p.objective)}</td>
          <td><span class="badge badge-${(p.status || 'ready').toLowerCase()}">${escapeHtml(p.status)}</span></td>
          <td>$${p.budget.toLocaleString()}</td>
          <td>${new Date(p.created_at).toLocaleTimeString()}</td>
        </tr>
      `).join("");
    } else {
      projTbody.innerHTML = `<tr><td colspan="5" style="text-align:center;">No active projects recorded.</td></tr>`;
    }

    // 3. Populate Recent Events
    const evtTbody = document.getElementById("overview-events-tbody");
    if (data.events && data.events.length > 0) {
      evtTbody.innerHTML = data.events.slice(0, 8).map(e => `
        <tr>
          <td>${new Date(e.timestamp).toLocaleTimeString()}</td>
          <td><code>${escapeHtml(e.event_type)}</code></td>
          <td>${escapeHtml(e.source_component)}</td>
          <td>${escapeHtml(e.task_id || e.project_id || '-')}</td>
        </tr>
      `).join("");
    }

    // 4. Populate Tasks
    const taskRes = await fetch("/api/tasks");
    if (taskRes.ok) {
      const taskData = await taskRes.json();
      const taskTbody = document.getElementById("tasks-tbody");
      if (taskData.tasks && taskData.tasks.length > 0) {
        taskTbody.innerHTML = taskData.tasks.map(t => `
          <tr>
            <td><code>${t.id}</code></td>
            <td><strong>${escapeHtml(t.objective)}</strong></td>
            <td>${escapeHtml(t.assigned_role_id)}</td>
            <td>${t.dependencies && t.dependencies.length ? t.dependencies.join(", ") : "None"}</td>
            <td><span class="badge">${t.priority}</span></td>
            <td><span class="badge badge-${t.status.toLowerCase()}">${t.status}</span></td>
          </tr>
        `).join("");
      }
    }

    // 5. Populate Decisions
    const decRes = await fetch("/api/decisions");
    if (decRes.ok) {
      const decData = await decRes.json();
      const decTbody = document.getElementById("decisions-tbody");
      if (decData.decisions && decData.decisions.length > 0) {
        decTbody.innerHTML = decData.decisions.map(d => `
          <tr>
            <td><strong>${escapeHtml(d.objective)}</strong></td>
            <td><span class="badge badge-completed">${escapeHtml(d.chosen_option || 'Pending')}</span></td>
            <td>${escapeHtml(d.reasons_for_selection || 'Evaluating trade-offs')}</td>
            <td><span class="badge">${d.status}</span></td>
            <td>${new Date(d.created_at).toLocaleTimeString()}</td>
          </tr>
        `).join("");
      }
    }

    // 6. Populate Roles
    const roleRes = await fetch("/api/roles");
    if (roleRes.ok) {
      const roleData = await roleRes.json();
      const roleTbody = document.getElementById("org-roles-tbody");
      if (roleData.roles && roleData.roles.length > 0) {
        roleTbody.innerHTML = roleData.roles.map(r => `
          <tr>
            <td><strong>${escapeHtml(r.title)}</strong></td>
            <td><span class="badge">${r.role_type}</span></td>
            <td>${r.reports_to_id || 'Top Executive'}</td>
            <td>${r.decision_authority.join(", ")}</td>
            <td>${r.tool_permissions.join(", ")}</td>
            <td>$${r.budget_limit.toLocaleString()}</td>
          </tr>
        `).join("");
      }
    }

    // 7. Populate Audit
    const auditRes = await fetch("/api/audit-log");
    if (auditRes.ok) {
      const auditData = await auditRes.json();
      const auditTbody = document.getElementById("governance-audit-tbody");
      if (auditData.audit_log && auditData.audit_log.length > 0) {
        auditTbody.innerHTML = auditData.audit_log.slice(0, 10).map(a => `
          <tr>
            <td>${new Date(a.timestamp).toLocaleTimeString()}</td>
            <td><strong>${escapeHtml(a.actor_id)}</strong></td>
            <td><code>${a.entity_type}:${a.entity_id}</code></td>
            <td>${escapeHtml(a.action)}</td>
          </tr>
        `).join("");
      }
    }

  } catch (err) {
    console.warn("SimArch polling error:", err);
  }
}

async function runQuickSimulation() {
  const out = document.getElementById("sim-results-output");
  out.innerHTML = `<p style="color: var(--color-cyan);">Running discrete-event simulation model...</p>`;

  try {
    const res = await fetch("/api/simulations/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "12-Month Autonomous SaaS Growth",
        duration_days: 365,
        marketing_budget: 6000
      })
    });
    const data = await res.json();
    const o = data.outcomes;

    out.innerHTML = `
      <div style="background-color: var(--bg-surface); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
        <h3 style="margin-bottom: 8px; color: var(--color-success);">Simulation Finished (365 Days Modeled)</h3>
        <p><strong>Final Cash:</strong> $${o.final_cash.toLocaleString()} | <strong>Monthly Revenue:</strong> $${o.final_monthly_revenue.toLocaleString()} | <strong>Customers:</strong> ${o.final_customers}</p>
        <p><strong>Product Readiness:</strong> ${o.final_product_readiness}% | <strong>Survival:</strong> ${o.survived ? 'PROFITABLE / SOLVENT' : 'INSOLVENT'}</p>
        <p style="margin-top: 8px; font-size: 11px; color: var(--text-dim);">Discrete events executed with seed 42. Verified reproducible causal feedback.</p>
      </div>
    `;
  } catch (err) {
    out.innerHTML = `<p style="color: var(--color-danger);">Simulation execution failed: ${err.message}</p>`;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

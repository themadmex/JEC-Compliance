const ROUTES = new Set([
  "home",
  "my-work",
  "agent",
  "tests",
  "reports",
  // Compliance
  "compliance-frameworks",
  "compliance-controls",
  "compliance-policies",
  "compliance-documents",
  "compliance-audits",
  "compliance-settings",
  // Customer trust
  "trust-overview",
  "trust-accounts",
  "trust-center",
  "trust-knowledge",
  "trust-activity",
  "trust-settings",
  // Risk
  "risk-overview",
  "risk-risks",
  "risk-library",
  "risk-actions",
  "risk-snapshots",
  "risk-settings",
  // Vendors
  "vendors",
  // Assets
  "assets",
  "assets-code",
  "assets-vulns",
  "assets-alerts",
  "assets-settings",
  // Personnel
  "personnel",
  "personnel-computers",
  "personnel-access",
  "personnel-settings",
  // Other
  "integrations",
  "evidence",
  "auditor-portal",
  "my-security-tasks",
  // Legacy aliases kept for backwards compat
  "policies",
  "settings",
]);

// Map nav group headers to the sub-routes they contain
const NAV_GROUP_MAP = {
  compliance: ["compliance-frameworks","compliance-controls","compliance-policies","compliance-documents","compliance-audits","compliance-settings"],
  "customer-trust": ["trust-overview","trust-accounts","trust-center","trust-knowledge","trust-activity","trust-settings"],
  risk: ["risk-overview","risk-risks","risk-library","risk-actions","risk-snapshots","risk-settings"],
  vendors: ["vendors"],
  assets: ["assets","assets-code","assets-vulns","assets-alerts","assets-settings"],
  personnel: ["personnel","personnel-computers","personnel-access","personnel-settings"],
};

async function getJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const auditorToken = shouldUseAuditorToken() ? getAuditorToken() : null;
  if (auditorToken && !headers.has("X-Auditor-Token")) {
    headers.set("X-Auditor-Token", auditorToken);
  }
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function shouldUseAuditorToken() {
  return Boolean(getSearchParam("token")) || window.location.hash.replace("#", "") === "auditor-portal";
}

function getAuditorToken() {
  const urlToken = getSearchParam("token");
  if (urlToken) {
    window.localStorage.setItem("auditorToken", urlToken);
    return urlToken;
  }
  return window.localStorage.getItem("auditorToken");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString();
}

function getSearchParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function setRouteSearchParam(name, value) {
  const url = new URL(window.location.href);
  if (value === null || value === undefined || value === "") {
    url.searchParams.delete(name);
  } else {
    url.searchParams.set(name, value);
  }
  window.history.pushState({}, "", url);
}

function navigateTo(route, params = {}) {
  _relationshipModal.open = false;
  const url = new URL(window.location.href);
  url.hash = `#${route}`;
  url.search = "";
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      url.searchParams.set(key, value);
    }
  });
  window.history.pushState({}, "", url);
  renderCurrentPage();
}

function routeButton(label, route, params = {}, variant = "primary") {
  const attrs = Object.entries(params)
    .map(([key, value]) => `data-param-${escapeHtml(key)}="${escapeHtml(value)}"`)
    .join(" ");
  return `<button class="btn btn-${variant}" data-route-target="${escapeHtml(route)}" ${attrs}>${escapeHtml(label)}</button>`;
}

function routeChip(label, route, params = {}, active = false) {
  const attrs = Object.entries(params)
    .map(([key, value]) => `data-param-${escapeHtml(key)}="${escapeHtml(value)}"`)
    .join(" ");
  return `<button class="audit-chip ${active ? "audit-chip-active" : ""}" data-route-target="${escapeHtml(route)}" ${attrs}>${escapeHtml(label)}</button>`;
}

function getDatasetParams(element) {
  return Object.entries(element.dataset)
    .filter(([key]) => key.startsWith("param"))
    .reduce((acc, [key, value]) => {
      const paramName = key.slice(5, 6).toLowerCase() + key.slice(6);
      acc[paramName] = value;
      return acc;
    }, {});
}

function getRoute() {
  const route = window.location.hash.replace("#", "").trim();
  return ROUTES.has(route) ? route : "home";
}

function setActiveNav(route) {
  // Update all links
  document.querySelectorAll(".side-nav a[data-route]").forEach((a) => {
    a.classList.toggle("active", a.dataset.route === route);
  });

  // Open the group containing the active route, close others
  Object.entries(NAV_GROUP_MAP).forEach(([group, routes]) => {
    const groupEl = document.getElementById(`group-${group}`);
    if (!groupEl) return;
    const isActive = routes.includes(route);
    if (isActive) {
      groupEl.classList.add("open", "has-active");
    } else {
      groupEl.classList.remove("has-active");
      // Only close if it wasn't manually opened
      if (!groupEl.dataset.manualOpen) {
        groupEl.classList.remove("open");
      }
    }
  });
}

function setupNavGroups() {
  document.querySelectorAll(".nav-group-header").forEach((btn) => {
    btn.addEventListener("click", () => {
      const groupEl = btn.closest(".nav-group");
      const isOpen = groupEl.classList.toggle("open");
      groupEl.dataset.manualOpen = isOpen ? "1" : "";
    });
  });
}

function shell(title, subtitle, actions = "") {
  return `
    <header style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 24px;">
      <h1 class="page-title serif-text" style="margin-bottom:0;">${escapeHtml(title)}</h1>
      <div class="head-actions">${actions}</div>
    </header>
  `;
}

function vantaHeader(title, subtitle = "", actions = "") {
  return `
    <header class="vanta-header">
      <div>
        <h1>${escapeHtml(title)}</h1>
        ${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ""}
      </div>
      <div class="head-actions">${actions}</div>
    </header>
  `;
}

function vantaProgress(percent, className = "") {
  const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));
  return `<div class="vanta-progress ${escapeHtml(className)}"><span style="width:${safePercent}%"></span></div>`;
}

function vantaToolbar(placeholder, filters = []) {
  return `
    <div class="vanta-toolbar">
      <input class="vanta-search" placeholder="${escapeHtml(placeholder)}" />
      ${filters.map((filter) => `<button class="vanta-filter" type="button">${escapeHtml(filter)} <i class="fa-solid fa-chevron-down" style="font-size:0.65rem;"></i></button>`).join("")}
      <button class="vanta-filter" type="button">+ Add filter</button>
    </div>
  `;
}

function statusRatio(ok, total) {
  return total ? Math.round((Number(ok) / Number(total)) * 100) : 0;
}

function isPositiveStatus(status) {
  const value = String(status || "").toLowerCase();
  return value.includes("pass") || value.includes("ok") || value.includes("implemented") || value.includes("accepted") || value.includes("ready") || value.includes("locked");
}

function vantaTask(icon, title, count = "") {
  return `
    <div class="vanta-task">
      <span class="vanta-mini-icon"><i class="${escapeHtml(icon)}"></i></span>
      <span>${escapeHtml(title)}</span>
      <span class="vanta-subtle">${escapeHtml(count)}</span>
    </div>
  `;
}

function getStatusHtml(status) {
  status = String(status || "").toLowerCase();
  if (status.includes("pass") || status.includes("ok") || status.includes("implemented") || status.includes("accepted")) {
    return `<span class="status-green">${escapeHtml(status)}</span>`;
  }
  if (status.includes("fail") || status.includes("missing")) {
    return `<span class="status-red">${escapeHtml(status)}</span>`;
  }
  return `<span class="status-yellow">${escapeHtml(status)}</span>`;
}

function renderStatusPills(items) {
  if (!items?.length) return `<p class="status-gray">No integration status available.</p>`;
  return items
    .map(
      (item) => `
      <div style="margin-bottom: 12px; display:flex; align-items:center; gap: 8px;">
        <span class="${item.configured ? "status-green" : "status-yellow"}">●</span>
        <strong>${escapeHtml(item.source)}</strong>: 
        <span class="status-gray">${item.configured ? "Configured" : "Needs setup"} - ${escapeHtml(item.detail)}</span>
      </div>
    `
    )
    .join("");
}

function renderTable(headers, rows) {
  return `
    <div class="card data-table-container" style="padding:0; overflow:hidden;">
      <table class="data-table">
        <thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    </div>
  `;
}

function renderBooleanPill(value, truthyLabel = "Ready", falsyLabel = "Not ready") {
  return value
    ? `<span class="status-green">${escapeHtml(truthyLabel)}</span>`
    : `<span class="status-gray">${escapeHtml(falsyLabel)}</span>`;
}

function renderAuditMetricCard(label, value, note = "", icon = "task_alt") {
  return `
    <div class="card metric-card audit-stat-card">
      <div class="audit-stat-top">
        <p class="status-gray audit-stat-label">${escapeHtml(label)}</p>
        <i class="fa-solid ${escapeHtml(icon)} audit-stat-icon"></i>
      </div>
      <div class="metric-value">${escapeHtml(value)}</div>
      ${note ? `<p class="audit-stat-note">${escapeHtml(note)}</p>` : ""}
    </div>
  `;
}

function renderAuditStageCards(summary) {
  const cards = [
    { label: "Scoping", value: summary.controls_in_scope, note: "Controls in scope", tone: "active" },
    { label: "Evidence", value: summary.evidence_items, note: "Artifacts collected", tone: "neutral" },
    { label: "Findings", value: summary.open_findings, note: "Open issues", tone: summary.open_findings ? "alert" : "good" },
  ];
  return `
    <div class="audit-stage-grid">
      ${cards
        .map(
          (card) => `
            <div class="audit-stage-card audit-stage-${card.tone}">
              <p class="audit-stage-label">${escapeHtml(card.label)}</p>
              <p class="audit-stage-value">${escapeHtml(card.value)}</p>
              <p class="audit-stage-note">${escapeHtml(card.note)}</p>
            </div>`
        )
        .join("")}
    </div>
  `;
}

function renderAuditFilterChips() {
  return `
    <div class="audit-chip-row">
      ${routeChip("SOC 2 Type I", "audit_report_soc_2_type_i", {}, true)}
      ${routeChip("In progress", "audit_report_in_progress_controls")}
      ${routeChip("Failed controls", "audit_report_failed_controls")}
      ${routeChip("Evidence attached", "jean_edwards_audit_evidence_list")}
    </div>
  `;
}

function renderAuditControlRows(controls) {
  return controls
    .map(
      (control) => `
        <tr>
          <td><button class="btn btn-outline" data-route-target="compliance-controls" data-param-control="${control.id}" style="padding:4px 8px; font-size:0.8rem;">${escapeHtml(control.control_id)}</button></td>
          <td>
            <div style="font-weight:500;">${escapeHtml(control.title)}</div>
            <div class="status-gray" style="font-size:0.82rem; margin-top:4px;">${escapeHtml(control.owner || "Unassigned")}</div>
          </td>
          <td>${getStatusHtml(control.audit_state)}</td>
          <td>${getStatusHtml(control.latest_evidence_status || "missing")}</td>
          <td class="status-gray">${escapeHtml(control.issue || "No open issue")}</td>
          <td class="status-gray">${formatDate(control.latest_evidence_at)}</td>
        </tr>`
    )
    .join("");
}

function renderAuditEvidenceList(controls) {
  return controls
    .slice(0, 6)
    .map(
      (control) => `
        <div class="audit-evidence-item">
          <div>
            <p class="audit-evidence-title">${escapeHtml(control.control_id)} · ${escapeHtml(control.title)}</p>
            <p class="audit-evidence-sub">${escapeHtml(control.issue || "Evidence attached and ready for review")}</p>
          </div>
          <span>${getStatusHtml(control.latest_evidence_status || "missing")}</span>
        </div>`
    )
    .join("");
}

function renderPolicyMetricCard(label, value, note = "") {
  return `
    <div class="card metric-card policy-metric-card">
      <p class="status-gray policy-metric-label">${escapeHtml(label)}</p>
      <div class="metric-value">${escapeHtml(value)}</div>
      ${note ? `<p class="policy-metric-note">${escapeHtml(note)}</p>` : ""}
    </div>
  `;
}

function renderDocumentRows(items) {
  return items
    .map(
      (item) => `<tr>
        <td>
          <div style="font-weight:500;">${escapeHtml(item.name)}</div>
          <div class="status-gray" style="font-size:0.82rem; margin-top:4px;">${escapeHtml(item.control_title || item.control_ref || "Unlinked document")}</div>
        </td>
        <td>${escapeHtml(item.control_ref || String(item.control_id))}</td>
        <td>${escapeHtml(item.source)}</td>
        <td class="status-gray">${formatDate(item.collected_at)}</td>
        <td>${getStatusHtml(item.status)}</td>
      </tr>`
    )
    .join("");
}

function renderPolicyVersionRows(items) {
  return items
    .map(
      (item) => `<tr>
        <td>
          <div style="font-weight:500;">${escapeHtml(item.policy)}</div>
          <div class="status-gray" style="font-size:0.82rem; margin-top:4px;">${escapeHtml(item.policy_id)}</div>
        </td>
        <td>${getStatusHtml(item.status)}</td>
        <td class="status-gray">${formatDate(item.next_review_at)}</td>
        <td>${escapeHtml(item.version_label)}</td>
        <td class="status-gray">${escapeHtml(item.change_note)}</td>
      </tr>`
    )
    .join("");
}

function renderRiskMetricCard(label, value, note = "", tone = "") {
  return `
    <div class="card metric-card risk-metric-card ${tone}">
      <p class="status-gray risk-metric-label">${escapeHtml(label)}</p>
      <div class="metric-value">${escapeHtml(value)}</div>
      ${note ? `<p class="risk-metric-note">${escapeHtml(note)}</p>` : ""}
    </div>
  `;
}

function renderRiskRows(items) {
  return items
    .map(
      (item) => `<tr>
        <td>
          <div style="font-weight:500;"><button class="btn btn-outline" data-route-target="risk-actions" style="padding:4px 8px; font-size:0.8rem;">${escapeHtml(item.title)}</button></div>
          <div class="status-gray" style="font-size:0.82rem; margin-top:4px;">${escapeHtml(item.control_id)}</div>
        </td>
        <td>${escapeHtml(item.owner || "Unassigned")}</td>
        <td>${getStatusHtml(item.severity)}</td>
        <td>${getStatusHtml(item.status)}</td>
        <td class="status-gray">${escapeHtml(item.reason)}</td>
      </tr>`
    )
    .join("");
}

function renderRiskLibraryRows(items) {
  return items
    .map(
      (item) => `<tr>
        <td><button class="btn btn-outline" data-route-target="risk-risks" style="padding:4px 8px; font-size:0.8rem;">${escapeHtml(item.template)}</button></td>
        <td>${escapeHtml(item.control_id)}</td>
        <td>${escapeHtml(item.owner || "Unassigned")}</td>
        <td>${getStatusHtml(item.state)}</td>
      </tr>`
    )
    .join("");
}

function renderRiskActionRows(items) {
  return items
    .map(
      (item) => `<tr>
        <td>
          <div style="font-weight:500;"><button class="btn btn-outline" data-route-target="risk-risks" style="padding:4px 8px; font-size:0.8rem;">${escapeHtml(item.title)}</button></div>
          <div class="status-gray" style="font-size:0.82rem; margin-top:4px;">${escapeHtml(item.owner || "Unassigned")}</div>
        </td>
        <td>${escapeHtml(item.priority)}</td>
        <td class="status-gray">${formatDate(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString())}</td>
        <td>${getStatusHtml(item.status)}</td>
      </tr>`
    )
    .join("");
}

function renderTrustMetricCard(label, value, note = "") {
  return `
    <div class="card metric-card trust-metric-card">
      <p class="status-gray trust-metric-label">${escapeHtml(label)}</p>
      <div class="metric-value">${escapeHtml(value)}</div>
      ${note ? `<p class="trust-metric-note">${escapeHtml(note)}</p>` : ""}
    </div>
  `;
}

function renderVendorRows(items) {
  return items
    .map(
      (item) => `<tr>
        <td>
          <div style="font-weight:500;">${escapeHtml(item.name)}</div>
          <div class="status-gray" style="font-size:0.82rem; margin-top:4px;">${escapeHtml(item.detail)}</div>
        </td>
        <td>${item.configured ? "Connected" : "Needs setup"}</td>
        <td>${getStatusHtml(item.status)}</td>
      </tr>`
    )
    .join("");
}

function openControlDetail(controlId) {
  setRouteSearchParam("control", controlId);
  _relationshipModal.open = false;
  renderCurrentPage();
}

function backToControls() {
  setRouteSearchParam("control", null);
  _relationshipModal.open = false;
  renderCurrentPage();
}

function openEvidenceDetail(evidenceId, controlId = null) {
  setRouteSearchParam("evidence", evidenceId);
  if (controlId) {
    setRouteSearchParam("control_id", controlId);
  }
  renderCurrentPage();
}

function clearEvidenceDetail() {
  setRouteSearchParam("evidence", null);
  renderCurrentPage();
}

function clearEvidenceControlFilter() {
  setRouteSearchParam("control_id", null);
  setRouteSearchParam("evidence", null);
  renderCurrentPage();
}

async function renderHome() {
  const [overview, integrations, gaps] = await Promise.all([
    getJson("/dashboard/overview"),
    getJson("/integrations/status"),
    getJson("/dashboard/gaps"),
  ]);
  const policiesPct = statusRatio(overview.policies_ok, overview.policies_total);
  const testsPct = statusRatio(overview.tests_ok, overview.tests_total);
  const vendorsPct = statusRatio(overview.vendors_ok, overview.vendors_total);
  const openIntegrationIssues = integrations.filter((item) => !item.configured).length;
  const openTasks = [
    ["fa-regular fa-file-lines", "Update or approve documents", Math.max(overview.policies_total - overview.policies_ok, 0)],
    ["fa-solid fa-list-check", "Resolve failing tests", Math.max(overview.tests_total - overview.tests_ok, 0)],
    ["fa-regular fa-calendar", "Follow up on overdue security tasks", gaps.length],
    ["fa-solid fa-plug", "Reconnect integrations", openIntegrationIssues],
  ];

  return `
    <div class="vanta-page wide">
      ${vantaHeader("Home", "SOC 2 readiness and open program work", '<button class="btn btn-outline">Hide open tasks</button>')}
      <div class="vanta-main-grid">
        <div>
          <h2 class="vanta-card-title" style="margin-bottom:12px;">Compliance progress</h2>
          <div class="vanta-card" style="max-width:560px;">
            <div class="vanta-card-head">
              <h3>SOC 2</h3>
              <i class="fa-solid fa-chevron-right vanta-subtle"></i>
            </div>
            <div class="vanta-big-number">${overview.soc2_progress_percent}%</div>
            ${vantaProgress(overview.soc2_progress_percent)}
            <div class="metric-footer" style="margin-top:10px;">
              <span>${overview.controls_passing} controls passing</span>
              <span>${overview.controls_total} total</span>
            </div>
          </div>

          <h2 class="vanta-card-title" style="margin-bottom:12px;">Monitoring</h2>
          <div class="vanta-monitor-grid">
            ${[
              ["Policies", overview.policies_ok, overview.policies_total, policiesPct, "compliance-policies", "fa-regular fa-file-lines"],
              ["Tests", overview.tests_ok, overview.tests_total, testsPct, "tests", "fa-solid fa-flask"],
              ["Vendors", overview.vendors_ok, overview.vendors_total, vendorsPct, "vendors", "fa-solid fa-store"],
              ["Documents", overview.controls_passing, overview.controls_total, overview.soc2_progress_percent, "compliance-documents", "fa-regular fa-folder-open"],
            ].map(([label, ok, total, pct, route, icon]) => `
              <div class="vanta-card clickable" data-route-target="${route}">
                <div class="vanta-card-head">
                  <h3><span class="vanta-mini-icon"><i class="${icon}"></i></span> ${escapeHtml(label)}</h3>
                  <i class="fa-solid fa-chevron-right vanta-subtle"></i>
                </div>
                <p class="vanta-subtle" style="margin-top:14px;">Needs attention</p>
                <div class="vanta-big-number">${Math.max(total - ok, 0)}</div>
                ${vantaProgress(pct)}
                <div class="metric-footer" style="margin-top:10px;">
                  <span>${ok} OK</span>
                  <span>${total} total</span>
                </div>
              </div>
            `).join("")}
          </div>

          <h2 class="vanta-card-title" style="margin:10px 0 12px;">Client trust workspace</h2>
          <div class="trust-center-banner">
            <h2>Stand up your security packet for buyer reviews</h2>
            <p>Use JEC-approved evidence, policies, and audit status to answer security reviews with consistent source material.</p>
            ${routeButton("Open Trust Center", "trust-center")}
            ${routeButton("View evidence", "evidence", {}, "outline")}
          </div>
        </div>

        <aside>
          <div class="vanta-card">
            <div class="vanta-card-head">
              <h2>Open program tasks</h2>
              <span class="vanta-pill">${openTasks.reduce((sum, item) => sum + Number(item[2] || 0), 0)}</span>
            </div>
            <p class="vanta-subtle" style="margin:10px 0 8px;">Urgent</p>
            <div class="vanta-task-list">
              ${openTasks.map(([icon, title, count]) => vantaTask(icon, title, count)).join("")}
            </div>
            <p class="vanta-subtle" style="margin:18px 0 8px;">Due soon</p>
            <div class="vanta-task-list">
              ${vantaTask("fa-regular fa-file-lines", "Approve renewal evidence", Math.max(overview.controls_total - overview.controls_passing, 0))}
              ${vantaTask("fa-solid fa-user-check", "Confirm owners", "1")}
            </div>
          </div>
        </aside>
      </div>
    </div>
  `;
}

// ── My Work state ─────────────────────────────────────────────
const _mw = {
  allItems: [],   // flat list of individual work items
  activeTab: "all",
  typeFilters: new Set(),
  typeSearch: "",
  dropdownOpen: false,
};

const _relationshipModal = {
  open: false,
  sourceType: "",
  sourceKey: "",
  options: [],
  typeFilter: "all",
  search: "",
  selectedKey: "",
  selectedType: "",
};

const MW_TYPES = [
  "Access request", "Access review", "Access review system",
  "Control", "Deprovisioning task", "Document",
  "Impact assessment", "Information request", "Issue",
  "Policy", "Risk", "Training", "Vendor",
];

const MW_SECTIONS = [
  { key: "urgent",   icon: "fa-regular fa-calendar",      iconColor: "#E53E3E", title: "Urgent" },
  { key: "soon",     icon: "fa-solid fa-calendar-days",   iconColor: "#DD6B20", title: "Coming soon" },
  { key: "unsched",  icon: "fa-regular fa-calendar",      iconColor: "#718096", title: "Unscheduled" },
  { key: "waiting",  icon: "fa-regular fa-hourglass-half",iconColor: "#718096", title: "Waiting on others" },
];

function _buildMwItems(controls, gaps) {
  const items = [];
  const controlMap = new Map(controls.map((c) => [c.id, c]));
  gaps.forEach((g) => {
    const ctrl = controlMap.get(g.control_db_id) || {};
    items.push({
      id: `evidence-${g.control_db_id}`,
      text: g.title,
      action: "Provide or update evidence",
      route: "compliance-controls",
      params: { control: g.control_db_id },
      section: "urgent",
      type: "Control",
      assignedTo: ctrl.owner || null,
      needsApproval: false,
      badge: null,
    });
  });
  controls.filter((c) => c.implementation_status === "in_review").forEach((c) => {
    items.push({
      id: `review-${c.id}`,
      text: c.title,
      action: "Review and approve",
      route: "compliance-controls",
      params: { control: c.id },
      section: "waiting",
      type: "Control",
      assignedTo: c.owner || null,
      needsApproval: true,
      badge: "Needs review",
    });
  });
  return items;
}

function _filterMwItems(items) {
  const tab = _mw.activeTab;
  const currentUser = window._currentUser;
  return items.filter((item) => {
    if (tab === "assigned") {
      if (!currentUser) return false;
      const match = item.assignedTo && (
        item.assignedTo === currentUser.name ||
        item.assignedTo === currentUser.email
      );
      if (!match) return false;
    }
    if (tab === "approval" && !item.needsApproval) return false;
    if (_mw.typeFilters.size > 0 && !_mw.typeFilters.has(item.type)) return false;
    return true;
  });
}

function _mwSectionHtml(section, items, groupAll) {
  let displayItems;
  if (groupAll) {
    // "All" tab: show one summary row per section
    const count = items.length;
    if (count === 0) {
      displayItems = [];
    } else if (section.key === "urgent") {
      displayItems = [{ text: `Provide or update evidence for ${count} control${count !== 1 ? "s" : ""}`, badge: null }];
    } else if (section.key === "waiting") {
      displayItems = [{ text: `Complete assessments for ${count} item${count !== 1 ? "s" : ""}`, badge: `${count} Needs review` }];
    } else {
      displayItems = [{ text: items[0].text, badge: items[0].badge }];
    }
  } else {
    displayItems = items.map((i) => ({ text: `${i.action}: ${i.text}`, badge: i.badge, route: i.route, params: i.params }));
  }

  const bodyHtml = displayItems.length
    ? displayItems.map((item) => `
        <div class="mw-item" ${item.route ? `data-route-target="${escapeHtml(item.route)}" ${Object.entries(item.params || {}).map(([k,v]) => `data-param-${k}="${escapeHtml(v)}"`).join(" ")}` : ""}>
          <i class="fa-regular fa-square-check mw-item-icon"></i>
          <span class="mw-item-text">${escapeHtml(item.text)}</span>
          ${item.badge ? `<span class="mw-item-badge">${escapeHtml(item.badge)}</span>` : ""}
        </div>`).join("")
    : `<div class="mw-empty">
         <p class="mw-empty-title">Nothing here right now</p>
         <p class="mw-empty-sub">You're all caught up in this section.</p>
       </div>`;

  const sectionId = `mw-sec-${section.key}`;
  return `
    <div class="mw-section" id="${sectionId}">
      <button class="mw-section-header" onclick="toggleMwSection('${sectionId}')">
        <i class="fa-solid fa-chevron-down mw-section-chevron"></i>
        <i class="${section.icon} mw-section-icon" style="color:${section.iconColor}"></i>
        <span class="mw-section-title">${escapeHtml(section.title)}</span>
        <span class="mw-section-count">${items.length}</span>
      </button>
      <div class="mw-section-body">${bodyHtml}</div>
    </div>`;
}

function _renderMwSections() {
  const filtered = _filterMwItems(_mw.allItems);
  const grouped = {};
  MW_SECTIONS.forEach((s) => { grouped[s.key] = []; });
  filtered.forEach((item) => { if (grouped[item.section]) grouped[item.section].push(item); });

  const groupAll = _mw.activeTab === "all";
  const totalFiltered = filtered.length;

  if (totalFiltered === 0 && _mw.activeTab !== "all") {
    return `<div class="mw-no-items">
      <p class="mw-no-items-title">You don't have anything here</p>
      <p class="mw-no-items-sub">We'll surface tasks here when you have work assigned to you.</p>
    </div>`;
  }

  return MW_SECTIONS.map((s) => _mwSectionHtml(s, grouped[s.key], groupAll)).join("");
}

function _renderMwTypeDropdown() {
  const q = _mw.typeSearch.toLowerCase();
  const visibleTypes = q ? MW_TYPES.filter((t) => t.toLowerCase().includes(q)) : MW_TYPES;
  const rows = visibleTypes.map((t) => {
    const checked = _mw.typeFilters.has(t) ? "checked" : "";
    return `<label class="mw-type-row">
      <input type="checkbox" ${checked} onchange="toggleMwType(${JSON.stringify(t)})" />
      <span>${escapeHtml(t)}</span>
    </label>`;
  }).join("");
  return `
    <div class="mw-type-dropdown" id="mw-type-dropdown">
      <div class="mw-type-search-wrap">
        <i class="fa-solid fa-magnifying-glass mw-type-search-icon"></i>
        <input class="mw-type-search" type="text" placeholder="Search"
          value="${escapeHtml(_mw.typeSearch)}"
          oninput="updateMwTypeSearch(this.value)" />
      </div>
      <div class="mw-type-list">${rows}</div>
    </div>`;
}

function toggleMwSection(sectionId) {
  const el = document.getElementById(sectionId);
  if (el) el.classList.toggle("mw-collapsed");
}

function switchMwTab(tab) {
  _mw.activeTab = tab;
  _mw.dropdownOpen = false;
  document.querySelectorAll(".mw-tab").forEach((btn) => {
    btn.classList.toggle("mw-tab-active", btn.dataset.tab === tab);
  });
  document.getElementById("mw-sections").innerHTML = _renderMwSections();
  const dd = document.getElementById("mw-type-dropdown");
  if (dd) dd.remove();
}

function toggleMwTypeDropdown() {
  _mw.dropdownOpen = !_mw.dropdownOpen;
  const existing = document.getElementById("mw-type-dropdown");
  if (existing) { existing.remove(); return; }
  const wrap = document.getElementById("mw-type-wrap");
  wrap.insertAdjacentHTML("beforeend", _renderMwTypeDropdown());
  // close on outside click
  setTimeout(() => {
    document.addEventListener("click", _mwDropdownOutsideClick, { once: true });
  }, 0);
}

function _mwDropdownOutsideClick(e) {
  const dd = document.getElementById("mw-type-dropdown");
  const btn = document.getElementById("mw-type-btn");
  if (dd && !dd.contains(e.target) && e.target !== btn) {
    dd.remove();
    _mw.dropdownOpen = false;
  } else if (dd) {
    // re-attach listener if click was inside dropdown
    setTimeout(() => {
      document.addEventListener("click", _mwDropdownOutsideClick, { once: true });
    }, 0);
  }
}

function updateMwTypeSearch(value) {
  _mw.typeSearch = value;
  const dd = document.getElementById("mw-type-dropdown");
  if (dd) dd.outerHTML = _renderMwTypeDropdown();
  // Re-attach search input focus
  const input = document.querySelector(".mw-type-search");
  if (input) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
}

function toggleMwType(type) {
  if (_mw.typeFilters.has(type)) {
    _mw.typeFilters.delete(type);
  } else {
    _mw.typeFilters.add(type);
  }
  const btn = document.getElementById("mw-type-btn");
  if (btn) btn.classList.toggle("mw-tab-active", _mw.typeFilters.size > 0);
  document.getElementById("mw-sections").innerHTML = _renderMwSections();
}

async function renderMyWork() {
  const [controls, gaps] = await Promise.all([getJson("/controls"), getJson("/dashboard/gaps")]);

  // Reset state on page load
  _mw.allItems = _buildMwItems(controls, gaps);
  _mw.activeTab = "all";
  _mw.typeFilters = new Set();
  _mw.typeSearch = "";
  _mw.dropdownOpen = false;

  return `
    <div class="mw-header">
      <h1 class="mw-title">My work</h1>
      <p class="mw-subtitle">View all work items that need your attention</p>
    </div>

    <div class="mw-tabs">
      <button class="mw-tab mw-tab-active" data-tab="all" onclick="switchMwTab('all')">All</button>
      <button class="mw-tab" data-tab="assigned" onclick="switchMwTab('assigned')">Assigned to me</button>
      <button class="mw-tab" data-tab="approval" onclick="switchMwTab('approval')">Needs my approval</button>
      <div class="mw-type-wrap" id="mw-type-wrap">
        <button class="mw-tab mw-tab-dropdown" id="mw-type-btn" onclick="toggleMwTypeDropdown()">
          Type <i class="fa-solid fa-chevron-down" style="font-size:0.65rem;margin-left:4px;"></i>
        </button>
      </div>
    </div>

    <div id="mw-sections">${_renderMwSections()}</div>
  `;
}

async function renderTests() {
  const [controls, evidence] = await Promise.all([getJson("/controls"), getJson("/evidence")]);
  const selectedTestId = getSearchParam("test");
  const latestByControl = new Map();
  evidence.forEach((e) => {
    if (!latestByControl.has(e.control_id)) latestByControl.set(e.control_id, e);
  });
  
  let passedCount = 0;
  let failedCount = 0;
  const selectedControl = controls.find((c) => String(c.id) === String(selectedTestId)) || null;
  const rows = controls.map((c) => {
    const ev = latestByControl.get(c.id);
    const status = ev?.status || "missing";
    if (status.includes("pass") || status.includes("ok") || status.includes("implemented") || status.includes("accepted")) {
       passedCount++;
    } else if (status.includes("fail") || status.includes("missing")) {
       failedCount++;
    }
    return `<tr>
      <td style="color: var(--text-primary); font-weight: 500;">${escapeHtml(c.title)}</td>
      <td>${getStatusHtml(status)}</td>
      <td class="status-gray">${formatDate(c.last_tested_at || ev?.collected_at)}</td>
      <td><button class="btn btn-outline" data-route-target="tests" data-param-test="${c.id}" style="padding: 6px 12px; font-size:0.85rem; border-color: #E0E0E0; color: var(--text-primary);">View Details</button></td>
    </tr>`;
  });

  const total = passedCount + failedCount;
  const passRate = total > 0 ? Math.round((passedCount / total) * 100) : 0;
  const failRate = total > 0 ? Math.round((failedCount / total) * 100) : 0;

  return `
    ${shell("Tests", "")}
    
    <div class="grid-2" style="margin-bottom: 32px;">
      <div class="card" style="border-left: 4px solid var(--accent-gold);">
        <p style="font-size: 1.1rem; margin-bottom: 12px;">Pass Rate</p>
        <div style="display:flex; align-items:baseline; gap: 12px;">
          <span class="metric-value" style="color: var(--accent-gold);">${passRate}%</span>
          <span class="status-gold" style="color: var(--accent-gold); font-weight:500;">Passed: ${passedCount}</span>
        </div>
      </div>
      <div class="card" style="border-left: 4px solid var(--status-fail);">
        <p style="font-size: 1.1rem; margin-bottom: 12px;">Failures</p>
        <div style="display:flex; align-items:baseline; gap: 12px;">
          <span class="metric-value" style="color: var(--status-fail);">${failRate}%</span>
          <span class="status-red" style="font-weight:500;">Failed: ${failedCount}</span>
        </div>
      </div>
    </div>

    ${renderTable(["Test Name", "Status", "Last Test", "Action"], rows)}
    ${selectedControl ? `
      <div class="card surface-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
          <div>
            <h3 class="serif-text section-title">Test Detail</h3>
            <p style="font-weight:500;">${escapeHtml(selectedControl.title)}</p>
            <p class="status-gray">${escapeHtml(selectedControl.description)}</p>
          </div>
          ${routeButton("Open Control", "compliance-controls", { control: selectedControl.id }, "outline")}
        </div>
      </div>` : ""}
  `;
}

async function renderPolicies() {
  const controls = await getJson("/controls");
  const rows = controls.map(
    (c) => `<tr>
      <td style="font-weight:500;">${escapeHtml(c.control_id)}</td>
      <td style="font-weight:500;">${escapeHtml(c.title)}</td>
      <td>${escapeHtml(c.owner || "-")}</td>
      <td>${getStatusHtml(c.implementation_status)}</td>
      <td class="status-gray">${formatDate(c.next_review_at)}</td>
    </tr>`
  );

  return `
    ${shell("Policies", "")}
    ${renderTable(["Policy ID", "Policy", "Owner", "Status", "Next Review"], rows)}
  `;
}

async function renderControls() {
  const controlId = getSearchParam("control");
  if (controlId) {
    return renderControlDetail(controlId);
  }

  const [controls, evidence] = await Promise.all([getJson("/controls"), getJson("/evidence")]);
  const latestByControl = new Map();
  evidence.forEach((item) => {
    const current = latestByControl.get(item.control_id);
    if (!current || new Date(item.collected_at) > new Date(current.collected_at)) {
      latestByControl.set(item.control_id, item);
    }
  });

  const implementedCount = controls.filter((c) => c.implementation_status === "implemented").length;
  const evidenceReadyCount = controls.filter((c) => latestByControl.has(c.id)).length;
  const rows = controls.map((control) => {
    const latestEvidence = latestByControl.get(control.id);
    return `<tr>
      <td style="font-weight:500;">${escapeHtml(control.control_id)}</td>
      <td>
        <div style="font-weight:500; color:var(--text-primary);">${escapeHtml(control.title)}</div>
        <div class="status-gray" style="font-size:0.85rem; margin-top:4px;">${escapeHtml(control.description)}</div>
      </td>
      <td>${escapeHtml(control.owner || "Unassigned")}</td>
      <td>${getStatusHtml(control.implementation_status)}</td>
      <td>${latestEvidence ? getStatusHtml(latestEvidence.status) : '<span class="status-gray">missing</span>'}</td>
      <td class="status-gray">${formatDate(control.next_review_at)}</td>
      <td>
        <button class="btn btn-outline" onclick="openControlDetail(${control.id})" style="padding: 6px 12px; font-size:0.85rem; border-color:#E0E0E0; color:var(--text-primary);">
          View
        </button>
      </td>
    </tr>`;
  });

  return `
    ${shell("Controls", "")}
    <div class="grid-3" style="margin-bottom:24px;">
      <div class="card">
        <p class="status-gray" style="margin-bottom:10px;">Total controls</p>
        <div class="metric-value">${controls.length}</div>
      </div>
      <div class="card">
        <p class="status-gray" style="margin-bottom:10px;">Implemented</p>
        <div class="metric-value" style="color:var(--accent-gold);">${implementedCount}</div>
      </div>
      <div class="card">
        <p class="status-gray" style="margin-bottom:10px;">With evidence</p>
        <div class="metric-value">${evidenceReadyCount}</div>
      </div>
    </div>
    ${renderTable(["ID", "Control", "Owner", "Status", "Evidence", "Next Review", ""], rows)}
  `;
}

async function renderControlDetail(controlId) {
  const [control, evidence] = await Promise.all([
    getJson(`/controls/${controlId}`),
    getJson(`/evidence?control_id=${encodeURIComponent(controlId)}`),
  ]);

  const evidenceRows = evidence.length
    ? evidence.map(
        (item) => `<tr>
          <td style="font-weight:500;">${escapeHtml(item.name)}</td>
          <td>${escapeHtml(item.source)}</td>
          <td>${getStatusHtml(item.status)}</td>
          <td class="status-gray">${formatDate(item.collected_at)}</td>
        </tr>`
      )
    : [`<tr><td colspan="4" class="status-gray" style="padding:20px;">No evidence attached yet.</td></tr>`];

  return `
    <div style="display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:24px; flex-wrap:wrap;">
      <div>
        <button class="btn btn-outline" onclick="backToControls()" style="margin-bottom:16px;">Back to controls</button>
        <h1 class="page-title serif-text" style="margin-bottom:6px;">${escapeHtml(control.control_id)} · ${escapeHtml(control.title)}</h1>
        <p class="status-gray">${escapeHtml(control.description)}</p>
      </div>
      <div class="head-actions">
        <a href="#evidence" onclick="setRouteSearchParam('control_id', ${control.id})" class="btn btn-primary">Add Evidence</a>
      </div>
    </div>

    <div class="grid-2" style="margin-bottom:24px;">
      <div class="card">
        <h3 class="serif-text" style="font-size:1.25rem; margin-bottom:16px;">Control Overview</h3>
        <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:16px 24px;">
          <div><p class="status-gray" style="margin-bottom:6px;">Owner</p><p style="font-weight:500;">${escapeHtml(control.owner || "Unassigned")}</p></div>
          <div><p class="status-gray" style="margin-bottom:6px;">Status</p><p>${getStatusHtml(control.implementation_status)}</p></div>
          <div><p class="status-gray" style="margin-bottom:6px;">Type I readiness</p><p>${renderBooleanPill(control.type1_ready)}</p></div>
          <div><p class="status-gray" style="margin-bottom:6px;">Type II readiness</p><p>${renderBooleanPill(control.type2_ready)}</p></div>
          <div><p class="status-gray" style="margin-bottom:6px;">Last tested</p><p>${formatDate(control.last_tested_at)}</p></div>
          <div><p class="status-gray" style="margin-bottom:6px;">Next review</p><p>${formatDate(control.next_review_at)}</p></div>
        </div>
      </div>
      <div class="card">
        <h3 class="serif-text" style="font-size:1.25rem; margin-bottom:16px;">Update Status</h3>
        <form id="control-status-form" data-control-id="${control.id}" style="display:flex; flex-direction:column; gap:12px;">
          <select id="control-status" style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;">
            ${["draft", "implemented", "needs_evidence", "in_review"]
              .map(
                (status) =>
                  `<option value="${status}" ${control.implementation_status === status ? "selected" : ""}>${escapeHtml(status)}</option>`
              )
              .join("")}
          </select>
          <button type="submit" class="btn btn-primary" style="align-self:flex-start;">Save status</button>
        </form>
        <p id="control-status-result" class="status-gray" style="margin-top:12px;"></p>
      </div>
    </div>

    <div class="card">
      <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:16px;">
        <h3 class="serif-text" style="font-size:1.25rem; margin-bottom:0;">Evidence History</h3>
        <span class="status-gray">${evidence.length} item${evidence.length === 1 ? "" : "s"}</span>
      </div>
      ${renderTable(["Name", "Source", "Status", "Collected"], evidenceRows)}
    </div>
  `;
}

async function renderVendors() {
  const workspace = await getJson("/workspaces/vendors");
  return `
    ${shell("Vendors", "", routeButton("Open Vendor Detail", "vendor_detail_view_1", {}, "outline"))}
    <div class="grid-3" style="margin-bottom:24px;">
      <div class="card metric-card"><p class="status-gray" style="margin-bottom:10px;">Vendors</p><div class="metric-value">${workspace.summary.vendors_total}</div></div>
      <div class="card metric-card"><p class="status-gray" style="margin-bottom:10px;">Active</p><div class="metric-value">${workspace.summary.active_vendors}</div></div>
      <div class="card metric-card"><p class="status-gray" style="margin-bottom:10px;">Recent checks</p><div class="metric-value">${workspace.summary.recent_checks}</div></div>
    </div>
    <div class="grid-2">
      <div class="card surface-card">
        <h3 class="serif-text section-title">Provider status</h3>
        <div>${renderStatusPills(workspace.vendors.map((vendor) => ({ source: vendor.name, configured: vendor.configured, detail: vendor.detail })))}</div>
        <div style="margin-top:16px;">
          ${renderTable(["Vendor", "Connection", "Status"], [renderVendorRows(workspace.vendors)])}
        </div>
      </div>
      <div class="surface-panel">
        <h3 class="serif-text section-title">Recent checks</h3>
        ${renderTable(
          ["Source", "Status", "Started", "Details"],
          workspace.runs.slice(0, 8).map(
            (r) =>
              `<tr>
                <td style="font-weight:500;">${escapeHtml(r.source)}</td>
                <td>${getStatusHtml(r.status)}</td>
                <td class="status-gray">${formatDate(r.started_at)}</td>
                <td class="status-gray">${escapeHtml(r.details)}</td>
               </tr>`
          )
        )}
      </div>
    </div>
  `;
}

async function renderAssets() {
  const evidence = await getJson("/evidence");
  const rows = evidence.map(
    (e) => `<tr>
      <td style="font-weight:500;">${escapeHtml(e.name)}</td>
      <td>${escapeHtml(e.source)}</td>
      <td class="status-gray">${escapeHtml(e.artifact_path)}</td>
      <td class="status-gray">${formatDate(e.collected_at)}</td>
      <td>${getStatusHtml(e.status)}</td>
    </tr>`
  );
  return `
    ${shell("Asset Inventory", "")}
    ${renderTable(["Asset", "Source", "Path", "Collected", "Status"], rows)}
  `;
}

async function renderIntegrations() {
  const [statuses, runs, spStatus] = await Promise.all([
    getJson("/integrations/status"),
    getJson("/integrations/runs"),
    getJson("/sharepoint/status").catch(() => ({ ok: false })),
  ]);

  const spProvisionCard = `
    <div class="card" style="margin-bottom:24px;">
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
        <div>
          <h3 class="serif-text" style="font-size:1.25rem; margin-bottom:4px;">
            <i class="fa-brands fa-microsoft" style="color:var(--accent-gold);"></i> SharePoint Folder Structure
          </h3>
          <p class="status-gray" style="font-size:0.875rem;">
            ${spStatus.ok
              ? "Creates the compliance folder tree on SharePoint to mirror the sidebar navigation."
              : "SharePoint not connected — add <code>SHAREPOINT_SITE_URL</code> to <code>.env</code> to enable."}
          </p>
        </div>
        ${spStatus.ok
          ? `<button id="provision-btn" class="btn btn-primary" style="white-space:nowrap;">
               <i class="fa-solid fa-folder-plus" style="margin-right:6px;"></i>Build Folder Structure
             </button>`
          : ""}
      </div>
      <div id="provision-result" style="margin-top:12px;"></div>
    </div>`;

  return `
    ${shell("Integrations", "", '<button id="sync-btn" class="btn btn-primary">Run Sync</button>')}
    ${spProvisionCard}
    <div class="grid-2">
      <div class="card">
        <h3 class="serif-text" style="font-size:1.5rem; margin-bottom:16px;">Connection Status</h3>
        <div>${renderStatusPills(statuses)}</div>
        <p id="sync-status" class="status-gray" style="margin-top:16px;"></p>
      </div>
      <div>
        <h3 class="serif-text" style="font-size:1.5rem; margin-bottom:16px;">Sync History</h3>
        ${renderTable(
          ["Source", "Started", "Status"],
          runs.map(
            (r) =>
              `<tr>
                <td style="font-weight:500;">${escapeHtml(r.source)}</td>
                <td class="status-gray">${formatDate(r.started_at)}</td>
                <td>${getStatusHtml(r.status)}</td>
               </tr>`
          )
        )}
      </div>
    </div>
  `;
}

async function renderEvidence() {
  const [evidence, spStatus] = await Promise.all([
    getJson("/evidence"),
    getJson("/sharepoint/status").catch(() => ({ ok: false })),
  ]);

  const spBrowser = spStatus.ok
    ? `
      <div class="card" style="margin-bottom:24px;">
        <h3 class="serif-text" style="font-size:1.25rem; margin-bottom:16px;">
          <i class="fa-brands fa-microsoft" style="color:var(--accent-gold);"></i> SharePoint — Browse &amp; Attach
        </h3>
        <div style="display:flex; gap:8px; margin-bottom:12px;">
          <input id="sp-folder" type="text" placeholder="Folder path (leave blank for root)" style="flex:1; padding:8px; border:1px solid #EAEAEA; border-radius:4px; font-size:0.9rem;" />
          <button id="sp-browse-btn" class="btn btn-outline" style="padding:8px 16px;">Browse</button>
        </div>
        <div id="sp-file-list" class="status-gray" style="font-size:0.9rem;">Click Browse to load files.</div>
      </div>`
    : `<div class="card" style="margin-bottom:24px; border-left:3px solid #EAEAEA;">
        <p class="status-gray" style="font-size:0.9rem;"><i class="fa-brands fa-microsoft"></i> SharePoint not connected — add <code>SHAREPOINT_SITE_URL</code> to your <code>.env</code> to enable file browsing.</p>
       </div>`;

  return `
    ${shell("Evidence Locker", "")}
    ${spBrowser}
    <div class="grid-2">
      <div class="card">
        <h3 class="serif-text" style="font-size:1.5rem; margin-bottom:16px;">Upload Evidence</h3>
        <form id="upload-form" style="display:flex; flex-direction:column; gap:16px;">
          <input type="number" name="control_id" placeholder="Control DB ID" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;" />
          <input type="text" name="title" placeholder="Evidence title" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;"/>
          <input type="text" name="source_type" value="manual" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;"/>
          <input type="date" name="valid_from" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;"/>
          <textarea name="description" placeholder="Notes (optional)" style="padding:10px; border:1px solid #EAEAEA; border-radius:4px; min-height:80px;"></textarea>
          <input type="file" name="file" required style="margin-top:8px;"/>
          <button type="submit" class="btn btn-primary" style="align-self:flex-start;">Upload evidence</button>
        </form>
        <p id="upload-status" class="status-gray" style="margin-top:16px;"></p>
      </div>
      <div>
        <h3 class="serif-text" style="font-size:1.5rem; margin-bottom:16px;">Recent Evidence</h3>
        ${renderTable(
          ["Name", "Control", "Status"],
          evidence.slice(0, 12).map(
            (e) =>
              `<tr>
                <td style="font-weight:500;">${escapeHtml(e.title || e.name)}</td>
                <td class="status-gray">${escapeHtml(e.control_id)}</td>
                <td>${getStatusHtml(e.status)}</td>
               </tr>`
          )
        )}
      </div>
    </div>
  `;
}

async function renderPersonnel() {
  return renderEnhancedPersonnel();
}

async function renderEnhancedEvidence() {
  const [evidence, spStatus, controls] = await Promise.all([
    getJson("/evidence"),
    getJson("/sharepoint/status").catch(() => ({ ok: false })),
    getJson("/controls"),
  ]);
  const selectedControlId = getSearchParam("control_id");
  const selectedEvidenceId = getSearchParam("evidence");
  const controlsById = new Map(controls.map((control) => [String(control.id), control]));
  const filteredEvidence = selectedControlId
    ? evidence.filter((item) => String(item.control_id) === String(selectedControlId))
    : evidence;
  const selectedControl = selectedControlId ? controlsById.get(String(selectedControlId)) : null;
  const selectedEvidence =
    (selectedEvidenceId && filteredEvidence.find((item) => String(item.id) === String(selectedEvidenceId))) ||
    filteredEvidence[0] ||
    null;
  const staleOrPendingCount = filteredEvidence.filter((item) => ["pending", "rejected", "stale"].includes(item.status)).length;
  const attachedControlCount = new Set(filteredEvidence.map((item) => item.control_id)).size;

  const spBrowser = spStatus.ok
    ? `
      <div class="card" style="margin-bottom:24px;">
        <h3 class="serif-text" style="font-size:1.25rem; margin-bottom:16px;">
          <i class="fa-brands fa-microsoft" style="color:var(--accent-gold);"></i> SharePoint Browse &amp; Attach
        </h3>
        <div style="display:flex; gap:8px; margin-bottom:12px;">
          <input id="sp-folder" type="text" placeholder="Folder path (leave blank for root)" style="flex:1; padding:8px; border:1px solid #EAEAEA; border-radius:4px; font-size:0.9rem;" />
          <button id="sp-browse-btn" class="btn btn-outline" style="padding:8px 16px;">Browse</button>
        </div>
        <div id="sp-file-list" class="status-gray" style="font-size:0.9rem;">Click Browse to load files.</div>
      </div>`
    : `<div class="card" style="margin-bottom:24px; border-left:3px solid #EAEAEA;">
        <p class="status-gray" style="font-size:0.9rem;"><i class="fa-brands fa-microsoft"></i> SharePoint not connected - add <code>SHAREPOINT_SITE_URL</code> to your <code>.env</code> to enable file browsing.</p>
       </div>`;

  const contextCard = selectedControl
    ? `
      <div class="card" style="margin-bottom:24px; border-left:4px solid var(--accent-gold);">
        <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px; flex-wrap:wrap;">
          <div>
            <p class="status-gray" style="margin-bottom:6px;">Filtered to control</p>
            <h3 class="serif-text" style="font-size:1.35rem; margin-bottom:6px;">${escapeHtml(selectedControl.control_id)} · ${escapeHtml(selectedControl.title)}</h3>
            <p class="status-gray">${escapeHtml(selectedControl.description)}</p>
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <a href="#compliance-controls" onclick="setRouteSearchParam('control', ${selectedControl.id})" class="btn btn-outline">View Control</a>
            <button class="btn btn-outline" onclick="clearEvidenceControlFilter()">Clear Filter</button>
          </div>
        </div>
      </div>`
    : "";

  const controlOptions = controls
    .map(
      (control) =>
        `<option value="${control.id}" ${String(control.id) === String(selectedControlId || "") ? "selected" : ""}>${escapeHtml(control.control_id)} · ${escapeHtml(control.title)}</option>`
    )
    .join("");

  const evidenceRows = filteredEvidence.length
    ? filteredEvidence
        .slice(0, 12)
        .map(
          (item) =>
            `<tr>
              <td style="font-weight:500;">${escapeHtml(item.title || item.name)}</td>
              <td class="status-gray">${escapeHtml(controlsById.get(String(item.control_id))?.control_id || item.control_id)}</td>
              <td>${getStatusHtml(item.status)}</td>
              <td class="status-gray">${formatDate(item.valid_from || item.collected_at)}</td>
              <td>
                <button class="btn btn-outline" onclick="openEvidenceDetail(${item.id}, ${item.control_id})" style="padding: 6px 12px; font-size:0.85rem; border-color:#E0E0E0; color:var(--text-primary);">
                  View
                </button>
              </td>
             </tr>`
        )
    : [`<tr><td colspan="5" class="status-gray" style="padding:20px;">No evidence found for this view.</td></tr>`];

  const evidenceDetailCard = selectedEvidence
    ? `
      <div class="card">
        <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:16px;">
          <div>
            <p class="status-gray" style="margin-bottom:6px;">Evidence detail</p>
            <h3 class="serif-text" style="font-size:1.3rem; margin-bottom:4px;">${escapeHtml(selectedEvidence.title || selectedEvidence.name)}</h3>
            <p class="status-gray">${escapeHtml(controlsById.get(String(selectedEvidence.control_id))?.control_id || selectedEvidence.control_id)} · ${escapeHtml(controlsById.get(String(selectedEvidence.control_id))?.title || "Unknown control")}</p>
          </div>
          <button class="btn btn-outline" onclick="clearEvidenceDetail()">Close</button>
        </div>
        <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:16px 24px;">
          <div><p class="status-gray" style="margin-bottom:6px;">Status</p><p>${getStatusHtml(selectedEvidence.status)}</p></div>
          <div><p class="status-gray" style="margin-bottom:6px;">Collected</p><p>${formatDate(selectedEvidence.valid_from || selectedEvidence.collected_at)}</p></div>
          <div><p class="status-gray" style="margin-bottom:6px;">Source</p><p>${escapeHtml(selectedEvidence.source_type || selectedEvidence.source)}</p></div>
          <div><p class="status-gray" style="margin-bottom:6px;">Artifact</p><p style="word-break:break-word;">${(selectedEvidence.sharepoint_url || selectedEvidence.local_path || selectedEvidence.artifact_path || "").startsWith("http") ? `<a href="${escapeHtml(selectedEvidence.sharepoint_url || selectedEvidence.local_path || selectedEvidence.artifact_path)}" target="_blank" rel="noopener">${escapeHtml(selectedEvidence.sharepoint_url || selectedEvidence.local_path || selectedEvidence.artifact_path)}</a>` : escapeHtml(selectedEvidence.local_path || selectedEvidence.artifact_path || "-")}</p></div>
        </div>
        <div style="margin-top:16px;">
          <p class="status-gray" style="margin-bottom:6px;">Notes</p>
          <p>${escapeHtml(selectedEvidence.description || selectedEvidence.notes || "No notes added.")}</p>
        </div>
      </div>`
    : `
      <div class="card">
        <p class="status-gray">Select an evidence item to inspect its details.</p>
      </div>`;

  return `
    <div class="vanta-page wide">
      ${vantaHeader("Evidence", selectedControl ? `${selectedControl.control_id} evidence detail` : "Evidence locker and audit-ready artifacts", routeButton("Upload evidence", "evidence"))}
      ${contextCard}
      <div class="vanta-card">
        <div class="vanta-card-head">
          <div>
            <h2>Evidence tracker</h2>
            <p class="vanta-subtle">${filteredEvidence.length} visible artifacts across ${attachedControlCount} controls</p>
          </div>
          <span class="vanta-pill">${staleOrPendingCount} need attention</span>
        </div>
        <div class="vanta-progress segmented" style="margin-top:16px;">
          <span class="blue" style="width:${statusRatio(filteredEvidence.length - staleOrPendingCount, Math.max(filteredEvidence.length, 1))}%"></span>
          <span class="red" style="width:${statusRatio(staleOrPendingCount, Math.max(filteredEvidence.length, 1))}%"></span>
          <span class="gray" style="width:8%"></span>
        </div>
        <div class="audit-readiness-legend">
          <span><strong>${filteredEvidence.length - staleOrPendingCount}</strong> Ready for audit</span>
          <span><strong>${staleOrPendingCount}</strong> Not ready</span>
          <span><strong>${attachedControlCount}</strong> Controls covered</span>
        </div>
      </div>
      ${vantaToolbar("Search evidence", ["Type", "Created by"])}
      <div class="grid-2 audit-layout">
        <div>
          ${renderTable(["Evidence", "Control", "Status", "Last updated", ""], evidenceRows)}
        </div>
        <div class="audit-side-stack">
          ${evidenceDetailCard}
          ${spBrowser}
          <div class="vanta-card">
            <h3 style="margin-bottom:16px;">Upload evidence</h3>
        <form id="upload-form" style="display:flex; flex-direction:column; gap:16px;">
          <select name="control_id" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;">
            <option value="">Select a control</option>
            ${controlOptions}
          </select>
          <input type="text" name="title" placeholder="Evidence title" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;"/>
          <input type="text" name="source_type" value="manual" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;"/>
          <input type="date" name="valid_from" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;"/>
          <textarea name="description" placeholder="Notes (optional)" style="padding:10px; border:1px solid #EAEAEA; border-radius:4px; min-height:80px;"></textarea>
          <input type="file" name="file" required style="margin-top:8px;"/>
          <button type="submit" class="btn btn-primary" style="align-self:flex-start;">Upload evidence</button>
        </form>
        <p id="upload-status" class="status-gray" style="margin-top:16px;"></p>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function renderEnhancedPersonnel() {
  const controls = await getJson("/controls");
  const ownerCount = new Map();
  controls.forEach((c) => {
    const owner = c.owner || "Unassigned";
    ownerCount.set(owner, (ownerCount.get(owner) || 0) + 1);
  });
  const rows = [...ownerCount.entries()].map(
    ([owner, count]) => `<tr><td style="font-weight:500;">${escapeHtml(owner)}</td><td>${count}</td><td class="status-gray">Control Owner</td><td><span class="status-green">Active</span></td></tr>`
  );
  return `
    ${shell("Personnel", "")}
    ${renderTable(["Name", "Assigned Controls", "Role", "Status"], rows)}
  `;
}

async function renderReports() {
  const [gaps, runs] = await Promise.all([getJson("/dashboard/gaps"), getJson("/integrations/runs")]);
  const selectedModule = getSearchParam("module");
  const events = [
    ...gaps.map((g) => ({
      timestamp: new Date().toISOString(),
      actor: "System",
      action: `Gap detected: ${g.reason}`,
      module: "Compliance",
    })),
    ...runs.map((r) => ({
      timestamp: r.started_at,
      actor: "Integration Worker",
      action: `${r.source} sync ${r.status}`,
      module: "Integrations",
    })),
  ]
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 20);

  return `
    ${shell("Audit Logs", "", routeButton("Open Audits", "compliance-audits", {}, "outline"))}
    ${renderTable(
      ["Timestamp", "Actor", "Action", "Module"],
      events.map(
        (e) =>
          `<tr>
            <td class="status-gray">${formatDate(e.timestamp)}</td>
            <td style="font-weight:500;">${escapeHtml(e.actor)}</td>
            <td class="status-gray">${escapeHtml(e.action)}</td>
            <td><button class="btn btn-outline" data-route-target="reports" data-param-module="${escapeHtml(e.module)}" style="padding:4px 8px; font-size:0.8rem;">${escapeHtml(e.module)}</button></td>
           </tr>`
      )
    )}
    ${selectedModule ? `<div class="card surface-card"><h3 class="serif-text section-title">Filtered Module</h3><p>${escapeHtml(selectedModule)}</p></div>` : ""}
  `;
}

async function renderSettings() {
  const statuses = await getJson("/integrations/status");
  return `
    ${shell("Settings", "")}
    <div class="grid-3">
      <div class="card">
        <h3 class="serif-text" style="font-size:1.25rem; margin-bottom:16px;">Security</h3>
        <p class="status-gray" style="margin-bottom:8px;">Two-factor authentication</p>
        <p class="status-green" style="font-size:1.1rem; margin-bottom:24px;">Enabled</p>
        ${routeButton("Manage Sessions", "personnel-access", {}, "outline")}
      </div>
      <div class="card">
        <h3 class="serif-text" style="font-size:1.25rem; margin-bottom:16px;">SSO Providers</h3>
        <div style="display:flex; flex-direction:column; gap:12px;">
          <span style="padding:12px; border:1px solid #EAEAEA; border-radius:4px; font-weight:500;">Azure AD</span>
        </div>
      </div>
      <div class="card">
        <h3 class="serif-text" style="font-size:1.25rem; margin-bottom:16px;">Integration Config</h3>
        <div>${renderStatusPills(statuses)}</div>
      </div>
    </div>
  `;
}

async function renderAgent() {
  const [overview, gaps, runs] = await Promise.all([
    getJson("/dashboard/overview"),
    getJson("/dashboard/gaps"),
    getJson("/integrations/runs"),
  ]);
  const suggestions = [
    `Close ${gaps.length} open compliance gap${gaps.length === 1 ? "" : "s"}`,
    `Review ${Math.max(overview.controls_total - overview.controls_passing, 0)} controls not yet passing`,
    `Check ${runs.filter((run) => run.status !== "ok").length} recent integration run${runs.filter((run) => run.status !== "ok").length === 1 ? "" : "s"}`,
  ];

  return `
    ${shell("JEC Agent", "", routeButton("Open My Work", "my-work"))}
    <div class="grid-3" style="margin-bottom:24px;">
      <div class="card"><p class="status-gray" style="margin-bottom:10px;">Open gaps</p><div class="metric-value">${gaps.length}</div></div>
      <div class="card"><p class="status-gray" style="margin-bottom:10px;">Passing controls</p><div class="metric-value">${overview.controls_passing}</div></div>
      <div class="card"><p class="status-gray" style="margin-bottom:10px;">Recent sync runs</p><div class="metric-value">${runs.length}</div></div>
    </div>
    <div class="grid-2">
      <div class="card">
        <h3 class="serif-text" style="font-size:1.35rem; margin-bottom:16px;">Suggested work</h3>
        ${suggestions.map((item) => `<div style="padding:12px 0; border-bottom:1px solid #F0F0F0;" data-route-target="my-work">${escapeHtml(item)}</div>`).join("")}
      </div>
      <div class="card">
        <h3 class="serif-text" style="font-size:1.35rem; margin-bottom:16px;">Assistant prompt ideas</h3>
        <div class="status-gray" style="display:flex; flex-direction:column; gap:10px;">
          <button class="btn btn-outline" data-route-target="compliance-controls" data-param-filter="needs_evidence">Show controls missing evidence</button>
          <button class="btn btn-outline" data-route-target="compliance-audits">Summarize audit readiness</button>
          <button class="btn btn-outline" data-route-target="personnel">Which owners need follow-up this week?</button>
        </div>
      </div>
    </div>
  `;
}

async function renderFrameworks() {
  const controls = await getJson("/controls");
  const implemented = controls.filter((control) => control.implementation_status === "implemented").length;
  const rows = [
    {
      name: "SOC 2",
      version: "2017 TSC",
      controls: controls.length,
      implemented,
      status: controls.length ? "active" : "draft",
    },
  ];

  return `
    ${shell("Frameworks", "", routeButton("View Controls", "compliance-controls"))}
    <div class="grid-3" style="margin-bottom:24px;">
      <div class="card"><p class="status-gray" style="margin-bottom:10px;">Active frameworks</p><div class="metric-value">${rows.length}</div></div>
      <div class="card"><p class="status-gray" style="margin-bottom:10px;">Mapped controls</p><div class="metric-value">${controls.length}</div></div>
      <div class="card"><p class="status-gray" style="margin-bottom:10px;">Implemented controls</p><div class="metric-value">${implemented}</div></div>
    </div>
    ${renderTable(
      ["Framework", "Version", "Controls", "Implemented", "Status"],
      rows.map(
        (row) => `<tr>
          <td style="font-weight:500;">${escapeHtml(row.name)}</td>
          <td>${escapeHtml(row.version)}</td>
          <td>${row.controls}</td>
          <td>${row.implemented}</td>
          <td>${getStatusHtml(row.status)}</td>
        </tr>`
      )
    )}
  `;
}

async function renderDocuments() {
  const workspace = await getJson("/workspaces/documents");
  const attentionItems = workspace.items.filter((item) => ["pending", "rejected", "stale"].includes(item.status));

  return `
    ${shell("Documents", "", routeButton("Upload Document", "evidence"))}
    <div class="status-gray" style="margin:-8px 0 16px; font-size:0.9rem;">
      <a href="#home" data-route-target="home" style="color:inherit;">Home</a> /
      <a href="#compliance-documents" data-route-target="compliance-documents" style="color:inherit;"> Documents</a>
    </div>
    <div class="grid-3" style="margin-bottom:24px;">
      ${renderPolicyMetricCard("Documents tracked", workspace.summary.total_documents, "Compliance artifacts on file")}
      ${renderPolicyMetricCard("Controls linked", workspace.summary.controls_covered, "Mapped to live controls")}
      ${renderPolicyMetricCard("Need attention", workspace.summary.attention_count, "Pending, rejected, or stale")}
    </div>
    <div class="card hero-card">
      <div class="hero-copy">
        <p class="hero-eyebrow">Document workspace</p>
        <h3 class="serif-text hero-title">Track owners, review state, and mapped controls for every compliance document</h3>
        <p class="hero-subtitle">Structured to feel closer to the document inventory mockups, with quick focus on items that need attention.</p>
      </div>
    </div>
    <div class="audit-chip-row">
      ${routeChip("Overall status", "compliance-documents", {}, true)}
      ${routeChip("Framework", "compliance-frameworks")}
      ${routeChip("Category", "compliance-policies")}
      ${routeChip("Owner", "personnel")}
    </div>
    <div class="grid-2 audit-layout">
      <div>
        ${renderTable(["Document", "Control", "Source", "Collected", "Status"], [renderDocumentRows(workspace.items)])}
      </div>
      <div class="audit-side-stack">
        <div class="card surface-card">
          <h3 class="serif-text section-title">Attention Queue</h3>
          <div class="audit-evidence-list">
            ${(attentionItems.length ? attentionItems : workspace.items.slice(0, 4))
              .map(
                (item) => `
                  <div class="audit-evidence-item">
                    <div>
                      <p class="audit-evidence-title">${escapeHtml(item.name)}</p>
                      <p class="audit-evidence-sub">${escapeHtml(item.control_ref || "Unlinked")} · ${escapeHtml(item.source)}</p>
                    </div>
                    <span>${getStatusHtml(item.status)}</span>
                  </div>`
              )
              .join("")}
          </div>
        </div>
        <div class="card surface-card">
          <h3 class="serif-text section-title">Document Actions</h3>
          <div class="audit-timeline">
            <div class="audit-timeline-item"><span class="audit-timeline-dot"></span><div><p class="audit-timeline-title">Upload new document</p><p class="audit-timeline-sub">Attach a new policy, procedure, or evidence-backed record</p></div></div>
            <div class="audit-timeline-item"><span class="audit-timeline-dot"></span><div><p class="audit-timeline-title">Review ownership</p><p class="audit-timeline-sub">Confirm each document has an owner and mapped control</p></div></div>
            <div class="audit-timeline-item"><span class="audit-timeline-dot audit-timeline-alert"></span><div><p class="audit-timeline-title">Resolve stale items</p><p class="audit-timeline-sub">${workspace.summary.attention_count} document(s) need follow-up</p></div></div>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function renderAudits() {
  const workspace = await getJson("/workspaces/audits");

  return `
    ${shell("Audits", "", routeButton("Start Audit", "new_audit_firm_selection"))}
    <div class="grid-3" style="margin-bottom:24px;">
      ${renderAuditMetricCard("Controls in scope", workspace.summary.controls_in_scope, "Current audit scope", "fa-clipboard-check")}
      ${renderAuditMetricCard("Open findings", workspace.summary.open_findings, "Needs auditor follow-up", "fa-triangle-exclamation")}
      ${renderAuditMetricCard("Evidence items", workspace.summary.evidence_items, "Collected artifacts", "fa-folder-open")}
    </div>
    <div class="card hero-card">
      <div class="hero-copy">
        <p class="hero-eyebrow">Audit workspace</p>
        <h3 class="serif-text hero-title">Track readiness by control, finding, and freshest evidence</h3>
        <p class="hero-subtitle">Mirror the audit flow from scoping through evidence review and issue resolution.</p>
      </div>
    </div>
    ${renderAuditStageCards(workspace.summary)}
    ${renderAuditFilterChips()}
    <div class="grid-2 audit-layout">
      <div>
        ${renderTable(
          ["Control", "Title", "State", "Evidence", "Finding", "Latest Evidence"],
          [renderAuditControlRows(workspace.controls)]
        )}
      </div>
      <div class="audit-side-stack">
        <div class="card surface-card">
          <h3 class="serif-text section-title">Evidence Queue</h3>
          <div class="audit-evidence-list">${renderAuditEvidenceList(workspace.controls)}</div>
        </div>
        <div class="card surface-card">
          <h3 class="serif-text section-title">Audit Timeline</h3>
          <div class="audit-timeline">
            <div class="audit-timeline-item"><span class="audit-timeline-dot"></span><div><p class="audit-timeline-title">Framework scoping complete</p><p class="audit-timeline-sub">SOC 2 scope confirmed for current cycle</p></div></div>
            <div class="audit-timeline-item"><span class="audit-timeline-dot"></span><div><p class="audit-timeline-title">Evidence review in progress</p><p class="audit-timeline-sub">${workspace.summary.evidence_items} evidence items reviewed so far</p></div></div>
            <div class="audit-timeline-item"><span class="audit-timeline-dot audit-timeline-alert"></span><div><p class="audit-timeline-title">Findings require remediation</p><p class="audit-timeline-sub">${workspace.summary.open_findings} controls still need attention</p></div></div>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function renderTrustOverview() {
  const workspace = await getJson("/workspaces/trust");
  return `
    ${shell("Customer Trust Overview", "")}
    <div class="grid-3" style="margin-bottom:24px;">
      ${renderTrustMetricCard("Trust posture", `${workspace.summary.trust_posture_percent}%`, "Public readiness signal")}
      ${renderTrustMetricCard("Customer-facing issues", workspace.summary.open_findings, "Exceptions visible to review")}
      ${renderTrustMetricCard("Trust center status", "Live", "Preview-ready experience")}
    </div>
    <div class="card hero-card">
      <div class="hero-copy">
        <p class="hero-eyebrow">Customer trust</p>
        <h3 class="serif-text hero-title">Present a polished trust posture backed by live readiness and evidence activity</h3>
        <p class="hero-subtitle">Updated to align more closely with the trust center preview and customer trust mockup family.</p>
      </div>
    </div>
    <div class="audit-chip-row">
      ${routeChip("Overview", "trust-overview", {}, true)}
      ${routeChip("Accounts", "trust-accounts")}
      ${routeChip("Trust Center", "trust-center")}
      ${routeChip("Activity", "trust-activity")}
    </div>
    <div class="grid-2 audit-layout">
      <div class="card surface-card">
        <h3 class="serif-text section-title">Customer Trust Activity</h3>
        ${renderTable(
          ["Time", "Actor", "Action"],
          workspace.activity.slice(0, 8).map(
            (event) => `<tr>
              <td class="status-gray">${formatDate(event.timestamp)}</td>
              <td style="font-weight:500;">${escapeHtml(event.actor)}</td>
              <td>${escapeHtml(event.action)}</td>
            </tr>`
          )
        )}
      </div>
      <div class="audit-side-stack">
        <div class="card surface-card">
          <h3 class="serif-text section-title">Trust Signals</h3>
          <div class="audit-evidence-list">
            <div class="audit-evidence-item"><div><p class="audit-evidence-title">Controls passing</p><p class="audit-evidence-sub">Backed by workspace readiness</p></div><span class="status-green">${workspace.summary.controls_passing}</span></div>
            <div class="audit-evidence-item"><div><p class="audit-evidence-title">Documents ready</p><p class="audit-evidence-sub">Evidence-backed customer artifacts</p></div><span class="status-green">${workspace.summary.documents_ready}</span></div>
            <div class="audit-evidence-item"><div><p class="audit-evidence-title">Open findings</p><p class="audit-evidence-sub">Exceptions requiring review</p></div><span>${getStatusHtml(workspace.summary.open_findings ? "attention" : "ready")}</span></div>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function renderTrustAccounts() {
  const workspace = await getJson("/workspaces/trust");
  return `
    ${shell("Accounts", "", routeButton("Open Trust Center", "trust-center", {}, "outline"))}
    ${renderTable(
      ["Account", "Owner", "Last Activity", "Status"],
      workspace.activity.slice(0, 8).map(
        (run, index) => `<tr>
          <td style="font-weight:500;">Customer ${index + 1}</td>
          <td>${escapeHtml(run.actor)}</td>
          <td class="status-gray">${formatDate(run.timestamp)}</td>
          <td><button class="btn btn-outline" data-route-target="trust-center" style="padding:4px 8px; font-size:0.8rem;">Open</button></td>
        </tr>`
      )
    )}
  `;
}

async function renderTrustCenter() {
  const workspace = await getJson("/workspaces/trust");
  return `
    ${shell("Trust Center", "", routeButton("Preview Public Page", "trust-overview"))}
    <div class="trust-center-banner" style="margin-top:0;">
      <h2>Security & Compliance</h2>
      <p>Share your control readiness and evidence-backed posture with customers in a polished trust center.</p>
      ${routeButton("Publish Changes", "trust-activity")}
    </div>
    <div class="grid-3" style="margin-top:24px;">
      ${renderTrustMetricCard("Controls passing", workspace.summary.controls_passing, "Visible in trust profile")}
      ${renderTrustMetricCard("Documents ready", workspace.summary.documents_ready, "Ready for customer sharing")}
      ${renderTrustMetricCard("Open findings", workspace.summary.open_findings, "Need remediation before publish")}
    </div>
    <div class="card surface-card">
      <h3 class="serif-text section-title">Preview Highlights</h3>
      <div class="audit-evidence-list">
        <div class="audit-evidence-item"><div><p class="audit-evidence-title">Security posture</p><p class="audit-evidence-sub">Current trust posture score</p></div><span class="status-green">${workspace.summary.trust_posture_percent}%</span></div>
        <div class="audit-evidence-item"><div><p class="audit-evidence-title">Control coverage</p><p class="audit-evidence-sub">Customer-visible control set</p></div><span class="status-green">${workspace.summary.controls_passing}</span></div>
        <div class="audit-evidence-item"><div><p class="audit-evidence-title">Recent activity</p><p class="audit-evidence-sub">Updates to evidence and sync activity</p></div><span class="status-green">${workspace.activity.length}</span></div>
      </div>
    </div>
  `;
}

async function renderTrustKnowledge() {
  const controls = await getJson("/controls");
  return `
    ${shell("Knowledge Base", "", routeButton("New Article", "trust-knowledge"))}
    ${renderTable(
      ["Article", "Mapped Control", "Owner", "Status"],
      controls.map(
        (control) => `<tr>
          <td style="font-weight:500;">${escapeHtml(control.title)} FAQ</td>
          <td>${escapeHtml(control.control_id)}</td>
          <td>${escapeHtml(control.owner || "Unassigned")}</td>
          <td><button class="btn btn-outline" data-route-target="compliance-controls" data-param-control="${control.id}" style="padding:4px 8px; font-size:0.8rem;">Open</button></td>
        </tr>`
      )
    )}
  `;
}

async function renderTrustActivity() {
  const workspace = await getJson("/workspaces/trust");
  return `
    ${shell("Activity", "")}
    <div class="card surface-card" style="margin-bottom:24px;">
      <h3 class="serif-text section-title">Customer-facing activity feed</h3>
      <p class="audit-note-block">Blend trust-facing updates with sync history to keep the preview lively and informative.</p>
    </div>
    ${renderTable(
      ["Time", "Actor", "Action"],
      workspace.activity.map(
        (event) => `<tr>
          <td class="status-gray">${formatDate(event.timestamp)}</td>
          <td style="font-weight:500;">${escapeHtml(event.actor)}</td>
          <td>${escapeHtml(event.action)}</td>
        </tr>`
      )
    )}
  `;
}

async function renderRiskOverview() {
  const workspace = await getJson("/workspaces/risk");
  return `
    ${shell("Risk Overview", "")}
    <div class="grid-3" style="margin-bottom:24px;">
      ${renderRiskMetricCard("Open risks", workspace.summary.open_risks, "Current register issues", "risk-tone-alert")}
      ${renderRiskMetricCard("Implemented controls", workspace.summary.implemented_controls, "Backed by control owners")}
      ${renderRiskMetricCard("Coverage", `${workspace.summary.coverage_percent}%`, "Overall readiness trend", "risk-tone-good")}
    </div>
    <div class="card hero-card">
      <div class="hero-copy">
        <p class="hero-eyebrow">Risk management</p>
        <h3 class="serif-text hero-title">Monitor risk posture, templates, remediation tasks, and historical snapshots</h3>
        <p class="hero-subtitle">Updated to align more closely with the risk overview and library mockups.</p>
      </div>
    </div>
    <div class="audit-chip-row">
      ${routeChip("Overview", "risk-overview", {}, true)}
      ${routeChip("Register", "risk-risks")}
      ${routeChip("Library", "risk-library")}
      ${routeChip("Actions", "risk-actions")}
      ${routeChip("Snapshots", "risk-snapshots")}
    </div>
    <div class="grid-2 audit-layout">
      <div class="card surface-card">
        <h3 class="serif-text section-title">Current Risk Register</h3>
        ${renderTable(["Risk", "Owner", "Severity", "Status", "Reason"], [renderRiskRows(workspace.risks)])}
      </div>
      <div class="audit-side-stack">
        <div class="card surface-card">
          <h3 class="serif-text section-title">Snapshot Trend</h3>
          <div class="audit-evidence-list">
            ${workspace.snapshots.map(
              (item) => `
                <div class="audit-evidence-item">
                  <div>
                    <p class="audit-evidence-title">${escapeHtml(item.label)}</p>
                    <p class="audit-evidence-sub">${item.open_risks} open risk(s)</p>
                  </div>
                  <span class="status-green">${item.readiness_percent}%</span>
                </div>`
            ).join("")}
          </div>
        </div>
        <div class="card surface-card">
          <h3 class="serif-text section-title">Remediation Focus</h3>
          <div class="audit-timeline">
            <div class="audit-timeline-item"><span class="audit-timeline-dot"></span><div><p class="audit-timeline-title">Review high severity items</p><p class="audit-timeline-sub">${workspace.risks.filter((item) => item.severity === "high").length} risk(s) currently marked high severity</p></div></div>
            <div class="audit-timeline-item"><span class="audit-timeline-dot"></span><div><p class="audit-timeline-title">Update risk library</p><p class="audit-timeline-sub">${workspace.library.length} templates available for standardization</p></div></div>
            <div class="audit-timeline-item"><span class="audit-timeline-dot audit-timeline-alert"></span><div><p class="audit-timeline-title">Track open actions</p><p class="audit-timeline-sub">${workspace.actions.length} remediation action(s) in queue</p></div></div>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function renderRisks() {
  const workspace = await getJson("/workspaces/risk");
  return `
    ${shell("Risks", "", routeButton("Add Risk", "risk-library"))}
    <div class="audit-chip-row">
      ${routeChip("All Categories", "risk-risks", {}, true)}
      ${routeChip("Operational", "risk-library")}
      ${routeChip("Security", "risk-actions")}
      ${routeChip("Compliance", "compliance-controls")}
    </div>
    ${renderTable(["Risk", "Owner", "Severity", "Status", "Reason"], [renderRiskRows(workspace.risks)])}
  `;
}

async function renderRiskLibrary() {
  const workspace = await getJson("/workspaces/risk");
  return `
    ${shell("Risk Library", "")}
    <div class="audit-chip-row">
      ${routeChip("All Categories", "risk-library", {}, true)}
      ${routeChip("Recommended", "risk-overview")}
      ${routeChip("Recently Used", "risk-snapshots")}
      ${routeChip("Export", "reports")}
    </div>
    <div class="card hero-card">
      <div class="hero-copy">
        <p class="hero-eyebrow">Risk library</p>
        <h3 class="serif-text hero-title">Standard risk scenarios for rapid register population</h3>
        <p class="hero-subtitle">Organized to reflect the enterprise library mockup with template-style browsing.</p>
      </div>
    </div>
    ${renderTable(["Template", "Linked Control", "Owner", "State"], [renderRiskLibraryRows(workspace.library)])}
  `;
}

async function renderRiskActions() {
  const workspace = await getJson("/workspaces/risk");
  return `
    ${shell("Action Tracker", "")}
    <div class="audit-chip-row">
      ${routeChip("All Tasks", "risk-actions", {}, true)}
      ${routeChip("Policy Reviews", "compliance-policies")}
      ${routeChip("Security Tests", "tests")}
      ${routeChip("Remediation", "risk-risks")}
    </div>
    <div class="card surface-card" style="margin-bottom:24px;">
      <div class="audit-progress-head">
        <div>
          <p class="audit-stage-label">Action workload</p>
          <h3 class="serif-text section-title" style="margin-bottom:4px;">Remediation queue and owner follow-up</h3>
        </div>
        <div class="audit-progress-value">${workspace.actions.length}</div>
      </div>
      <div class="audit-note-block">Track open tasks, assign owners, and work through the remediation backlog with a more action-tracker-like layout.</div>
    </div>
    ${renderTable(["Action", "Priority", "Due", "Status"], [renderRiskActionRows(workspace.actions)])}
  `;
}

async function renderRiskSnapshots() {
  const workspace = await getJson("/workspaces/risk");
  return `
    ${shell("Snapshots", "")}
    <div class="grid-3" style="margin-bottom:24px;">
      ${workspace.snapshots
        .map(
          (item) =>
            renderRiskMetricCard(item.label, `${item.readiness_percent}%`, `${item.open_risks} open risk(s)`, item.open_risks ? "risk-tone-alert" : "risk-tone-good")
        )
        .join("")}
    </div>
    ${renderTable(
      ["Snapshot", "Readiness", "Open Risks"],
      workspace.snapshots.map(
        (item) => `<tr>
          <td style="font-weight:500;">${escapeHtml(item.label)}</td>
          <td>${item.readiness_percent}%</td>
          <td>${item.open_risks}</td>
        </tr>`
      )
    )}
  `;
}

async function renderAssetsCode() {
  const controls = await getJson("/controls");
  return `
    ${shell("Code Changes", "")}
    ${renderTable(
      ["Repository", "Mapped Control", "Owner", "Status"],
      controls.map(
        (control, index) => `<tr>
          <td style="font-weight:500;">jec-platform-${index + 1}</td>
          <td>${escapeHtml(control.control_id)}</td>
          <td>${escapeHtml(control.owner || "Unassigned")}</td>
          <td>${getStatusHtml(control.implementation_status)}</td>
        </tr>`
      )
    )}
  `;
}

async function renderAssetsVulns() {
  const gaps = await getJson("/dashboard/gaps");
  return `
    ${shell("Vulnerabilities", "")}
    ${renderTable(
      ["Asset", "Finding", "Severity", "Status"],
      gaps.map(
        (gap, index) => `<tr>
          <td style="font-weight:500;">asset-${index + 1}</td>
          <td>${escapeHtml(gap.title)}</td>
          <td>${getStatusHtml(gap.reason.includes("No evidence") ? "critical" : "medium")}</td>
          <td>${getStatusHtml("open")}</td>
        </tr>`
      )
    )}
  `;
}

async function renderAssetsAlerts() {
  const runs = await getJson("/integrations/runs");
  return `
    ${shell("Security Alerts", "")}
    ${renderTable(
      ["Alert", "Source", "Detected", "Status"],
      runs.map(
        (run) => `<tr>
          <td style="font-weight:500;">${escapeHtml(run.details || `${run.source} event`)}</td>
          <td>${escapeHtml(run.source)}</td>
          <td class="status-gray">${formatDate(run.started_at)}</td>
          <td>${getStatusHtml(run.status)}</td>
        </tr>`
      )
    )}
  `;
}

async function renderPersonnelComputers() {
  const controls = await getJson("/controls");
  return `
    ${shell("Computers", "")}
    ${renderTable(
      ["Device", "Assigned To", "Control", "Status"],
      controls.map(
        (control, index) => `<tr>
          <td style="font-weight:500;">JEC-LT-${100 + index}</td>
          <td>${escapeHtml(control.owner || "Unassigned")}</td>
          <td>${escapeHtml(control.control_id)}</td>
          <td>${getStatusHtml(control.implementation_status === "implemented" ? "managed" : "review")}</td>
        </tr>`
      )
    )}
  `;
}

async function renderPersonnelAccess() {
  const controls = await getJson("/controls");
  return `
    ${shell("Access", "")}
    ${renderTable(
      ["User", "Role", "Mapped Control", "Review State"],
      controls.map(
        (control) => `<tr>
          <td style="font-weight:500;">${escapeHtml(control.owner || "Unassigned")}</td>
          <td>Control Owner</td>
          <td>${escapeHtml(control.control_id)}</td>
          <td>${getStatusHtml(control.implementation_status)}</td>
        </tr>`
      )
    )}
  `;
}

async function renderSecurityTasks() {
  const [controls, gaps] = await Promise.all([getJson("/controls"), getJson("/dashboard/gaps")]);
  const controlMap = new Map(controls.map((control) => [control.id, control]));
  return `
    ${shell("My Security Tasks", "")}
    ${renderTable(
      ["Task", "Owner", "Priority", "Status"],
      gaps.map(
        (gap) => `<tr>
          <td style="font-weight:500;">Address ${escapeHtml(gap.reason.toLowerCase())}</td>
          <td>${escapeHtml(controlMap.get(gap.control_db_id)?.owner || "Unassigned")}</td>
          <td>${getStatusHtml("high")}</td>
          <td>${getStatusHtml("open")}</td>
        </tr>`
      )
    )}
  `;
}

async function renderDetailedControlWorkspace(title = "Control Detail") {
  const controls = await getJson("/controls");
  const control = controls[0];
  if (!control) return renderPlaceholder(title, "No controls available yet.");
  setRouteSearchParam("control", control.id);
  return renderControlDetail(control.id);
}

async function renderPolicyLifecycle(title = "Policy Version History") {
  const workspace = await getJson("/workspaces/policies");
  return `
    ${shell(title, "", routeButton("Publish Version", "publish_policy_confirmation"))}
    <div class="grid-3" style="margin-bottom:24px;">
      ${renderPolicyMetricCard("Policies", workspace.summary.total_policies, "Tracked policy set")}
      ${renderPolicyMetricCard("Published", workspace.summary.published_policies, "Ready for audit")}
      ${renderPolicyMetricCard("Need review", workspace.summary.needs_review, "Pending updates")}
    </div>
    <div class="card hero-card">
      <div class="hero-copy">
        <p class="hero-eyebrow">Policy lifecycle</p>
        <h3 class="serif-text hero-title">${escapeHtml(title)}</h3>
        <p class="hero-subtitle">Review version history, compare changes, and prepare the next publish-ready policy set.</p>
      </div>
    </div>
    <div class="audit-chip-row">
      ${routeChip("Version history", "policy_version_history_details", {}, true)}
      ${routeChip("Unified diff", "policy_comparison_unified_diff_view")}
      ${routeChip("Archived", "policy_details_v2.4_archived")}
      ${routeChip("Publish", "publish_policy_confirmation")}
    </div>
    <div class="grid-2 audit-layout">
      <div>
        ${renderTable(["Policy", "Status", "Next Review", "Version", "Version Note"], [renderPolicyVersionRows(workspace.versions)])}
      </div>
      <div class="audit-side-stack">
        <div class="card surface-card">
          <h3 class="serif-text section-title">Publish Checklist</h3>
          <div class="audit-timeline">
            <div class="audit-timeline-item"><span class="audit-timeline-dot"></span><div><p class="audit-timeline-title">Review changed sections</p><p class="audit-timeline-sub">Confirm edits are reflected in the new policy version</p></div></div>
            <div class="audit-timeline-item"><span class="audit-timeline-dot"></span><div><p class="audit-timeline-title">Validate mapped controls</p><p class="audit-timeline-sub">Ensure each policy still supports active controls</p></div></div>
            <div class="audit-timeline-item"><span class="audit-timeline-dot audit-timeline-alert"></span><div><p class="audit-timeline-title">Approve for publish</p><p class="audit-timeline-sub">${workspace.summary.needs_review} policy item(s) still need review</p></div></div>
          </div>
        </div>
        <div class="card surface-card">
          <h3 class="serif-text section-title">Latest Notes</h3>
          <div class="audit-evidence-list">
            ${workspace.versions.slice(0, 4).map(
              (item) => `
                <div class="audit-evidence-item">
                  <div>
                    <p class="audit-evidence-title">${escapeHtml(item.policy)}</p>
                    <p class="audit-evidence-sub">${escapeHtml(item.version_label)} · ${escapeHtml(item.change_note)}</p>
                  </div>
                  <span>${getStatusHtml(item.status)}</span>
                </div>`
            ).join("")}
          </div>
        </div>
      </div>
    </div>
  `;
}

async function renderVendorDetailWorkspace(title = "Vendor Detail") {
  const workspace = await getJson("/workspaces/vendors");
  const vendor = workspace.vendors[0];
  return `
    ${shell(title, "", routeButton("Request Document", "vendor_documents_tab_1"))}
    <div class="grid-2 audit-layout">
      <div class="card surface-card">
        <h3 class="serif-text section-title">Vendor profile</h3>
        <div style="display:flex; flex-direction:column; gap:12px;">
          <div><p class="status-gray">Vendor</p><p style="font-weight:500;">${escapeHtml(vendor?.name || "Microsoft 365")}</p></div>
          <div><p class="status-gray">Category</p><p>Infrastructure / Productivity</p></div>
          <div><p class="status-gray">Status</p><p>${getStatusHtml(vendor?.status || "review")}</p></div>
          <div><p class="status-gray">Connection Detail</p><p>${escapeHtml(vendor?.detail || "Needs configuration")}</p></div>
        </div>
      </div>
      <div class="card surface-card">
        <h3 class="serif-text section-title">Recent checks</h3>
        ${renderTable(
          ["Source", "Started", "Status"],
          workspace.runs.slice(0, 5).map(
            (run) => `<tr>
              <td style="font-weight:500;">${escapeHtml(run.source)}</td>
              <td class="status-gray">${formatDate(run.started_at)}</td>
              <td>${getStatusHtml(run.status)}</td>
            </tr>`
          )
        )}
      </div>
    </div>
  `;
}

async function renderAuditVariant(title = "Audit Workflow") {
  const workspace = await getJson("/workspaces/audits");
  const titleLower = title.toLowerCase();
  const filteredControls = workspace.controls.filter((control) => {
    if (titleLower.includes("failed")) return Boolean(control.issue);
    if (titleLower.includes("in progress")) return control.audit_state !== "ready";
    return true;
  });
  const progressPercent = titleLower.includes("new audit") ? 40 : titleLower.includes("report") ? 85 : 65;
  return `
    ${shell(title, "", routeButton("Advance Workflow", "compliance-audits"))}
    <div class="card surface-card" style="margin-bottom:24px;">
      <div class="audit-progress-head">
        <div>
          <p class="audit-stage-label">Workflow Progress</p>
          <h3 class="serif-text section-title" style="margin-bottom:4px;">${escapeHtml(title)}</h3>
        </div>
        <div class="audit-progress-value">${progressPercent}%</div>
      </div>
      <div class="progress-container" style="margin-bottom:0;">
        <div class="progress-bar" style="width:${progressPercent}%"></div>
      </div>
    </div>
    ${renderAuditStageCards(workspace.summary)}
    ${renderAuditFilterChips()}
    <div class="grid-2 audit-layout">
      <div>
        ${renderTable(
          ["Control", "Title", "State", "Evidence", "Finding", "Latest Evidence"],
          [renderAuditControlRows(filteredControls)]
        )}
      </div>
      <div class="audit-side-stack">
        <div class="card surface-card">
          <h3 class="serif-text section-title">Review Notes</h3>
          <div class="audit-note-block">
            <p>Use this stage to validate framework scoping, assign audit contacts, and isolate controls that still need remediation before report signoff.</p>
          </div>
        </div>
        <div class="card surface-card">
          <h3 class="serif-text section-title">Evidence Sidebar</h3>
          <div class="audit-evidence-list">${renderAuditEvidenceList(filteredControls)}</div>
        </div>
      </div>
    </div>
  `;
}

async function renderTrustReportDetail(title = "Customer Trust Report") {
  const [overview, gaps] = await Promise.all([getJson("/dashboard/overview"), getJson("/dashboard/gaps")]);
  return `
    ${shell(title, "", routeButton("Export PDF", "reports"))}
    <div class="grid-3" style="margin-bottom:24px;">
      <div class="card"><p class="status-gray" style="margin-bottom:10px;">Readiness</p><div class="metric-value">${overview.soc2_progress_percent}%</div></div>
      <div class="card"><p class="status-gray" style="margin-bottom:10px;">Passing controls</p><div class="metric-value">${overview.controls_passing}</div></div>
      <div class="card"><p class="status-gray" style="margin-bottom:10px;">Open findings</p><div class="metric-value">${gaps.length}</div></div>
    </div>
    <div class="card"><p class="status-gray">This report view packages readiness, evidence freshness, and current exceptions for customer sharing.</p></div>
  `;
}

async function renderReferenceCapture(routeName) {
  return `
    ${shell("Reference Capture", "")}
    <div class="card">
      <p class="status-gray" style="margin-bottom:12px;">This route preserves a mockup/capture name from the screen folder.</p>
      <p style="font-weight:500;">${escapeHtml(routeName)}</p>
    </div>
  `;
}

function renderPlaceholder(title, subtitle = "") {
  return Promise.resolve(`
    ${shell(title, "")}
    <div class="card">
      <p class="status-gray" style="font-size:1rem;">${escapeHtml(subtitle || "This section is coming soon.")}</p>
    </div>
  `);
}

function renderAuditorMetric(label, value, note = "") {
  return `
    <div class="card metric-card audit-stat-card">
      <p class="status-gray audit-stat-label">${escapeHtml(label)}</p>
      <div class="metric-value">${escapeHtml(value)}</div>
      ${note ? `<p class="audit-stat-note">${escapeHtml(note)}</p>` : ""}
    </div>
  `;
}

function getControlRef(control) {
  return control.control_ref || control.control_code || control.control_id || "-";
}

function renderAuditorAuditPicker(audits, selectedAuditId) {
  if (audits.length <= 1) return "";
  return `
    <div class="audit-chip-row">
      ${audits
        .map((audit) =>
          routeChip(
            `${audit.audit_firm || "Audit"} #${audit.id}`,
            "auditor-portal",
            { audit: audit.id },
            String(audit.id) === String(selectedAuditId)
          )
        )
        .join("")}
    </div>
  `;
}

function renderAuditorControlsTable(controls) {
  const rows = controls.map(
    (control) => `
      <tr>
        <td style="font-weight:500;">${escapeHtml(getControlRef(control))}</td>
        <td>
          <div style="font-weight:500;">${escapeHtml(control.title)}</div>
          <div class="status-gray" style="font-size:0.82rem; margin-top:4px;">${escapeHtml(control.owner || "Unassigned")}</div>
        </td>
        <td>${getStatusHtml(control.evidence_status || "missing")}</td>
        <td class="status-gray">${escapeHtml(control.auditor_notes || "-")}</td>
      </tr>
    `
  );
  return renderTable(["Control", "Title", "Evidence", "Auditor notes"], rows);
}

function renderAuditorEvidenceTable(evidence) {
  if (!evidence.length) {
    return `<div class="card"><p class="status-gray">No evidence has been shared for this audit yet.</p></div>`;
  }
  return renderTable(
    ["Control", "Evidence", "Status", "Valid from", "File"],
    evidence.map(
      (item) => `
        <tr>
          <td style="font-weight:500;">${escapeHtml(item.control_ref || item.control_id)}</td>
          <td>${escapeHtml(item.title || item.name || "Evidence")}</td>
          <td>${getStatusHtml(item.status)}</td>
          <td class="status-gray">${formatDate(item.valid_from || item.collected_at)}</td>
          <td class="status-gray">${escapeHtml(item.file_name || "-")}</td>
        </tr>
      `
    )
  );
}

function renderAuditorRequests(requests, evidence, controls) {
  if (!requests.length) {
    return `<div class="card"><p class="status-gray">No auditor requests yet.</p></div>`;
  }
  const controlRefs = new Map(controls.map((control) => [String(control.control_id), getControlRef(control)]));
  const canAttachEvidence = window._currentUser?.role !== "auditor";
  return requests
    .map(
      (request) => {
        const eligibleEvidence = evidence.filter((item) => !request.control_id || String(item.control_id) === String(request.control_id));
        return `
        <div class="card auditor-request-card">
          <div class="mapped-elements-header compact">
            <div>
              <p class="audit-stage-label">Request #${escapeHtml(request.id)}</p>
              <h3 class="serif-text section-title" style="margin-bottom:4px;">${escapeHtml(request.title)}</h3>
              <p class="status-gray">${escapeHtml(request.description || "No description provided.")}</p>
            </div>
            ${getStatusHtml(request.status || "open")}
          </div>
          <div class="grid-3" style="margin-bottom:18px;">
            <div><p class="status-gray">Control</p><p>${escapeHtml(request.control_id ? controlRefs.get(String(request.control_id)) || request.control_id : "General")}</p></div>
            <div><p class="status-gray">Due</p><p>${formatDate(request.due_date)}</p></div>
            <div><p class="status-gray">Evidence attached</p><p>${escapeHtml((request.evidence || []).length)}</p></div>
          </div>
          <div class="audit-evidence-list" style="margin-bottom:18px;">
            ${(request.evidence || [])
              .map(
                (item) => `
                  <div class="audit-evidence-item">
                    <div>
                      <p class="audit-evidence-title">${escapeHtml(item.title || item.file_name || `Evidence #${item.id}`)}</p>
                      <p class="audit-evidence-sub">${escapeHtml(item.file_name || "-")}</p>
                    </div>
                    ${getStatusHtml(item.status)}
                  </div>
                `
              )
              .join("") || `<p class="status-gray">Waiting on evidence attachment.</p>`}
          </div>
          <div class="audit-evidence-list" style="margin-bottom:18px;">
            ${(request.comments || [])
              .map(
                (comment) => `
                  <div class="audit-evidence-item">
                    <div>
                      <p class="audit-evidence-title">${escapeHtml(comment.is_internal ? "Internal note" : "Comment")}</p>
                      <p class="audit-evidence-sub">${escapeHtml(comment.body)}</p>
                    </div>
                    <span class="status-gray">${formatDate(comment.created_at)}</span>
                  </div>
                `
              )
              .join("") || `<p class="status-gray">No comments yet.</p>`}
          </div>
          <form class="auditor-status-form" data-request-id="${escapeHtml(request.id)}" style="display:flex; gap:10px; align-items:center; margin-bottom:12px;">
            <select name="status" style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;">
              ${["open", "in_progress", "fulfilled", "closed"].map((status) => `<option value="${status}" ${request.status === status ? "selected" : ""}>${escapeHtml(status.replaceAll("_", " "))}</option>`).join("")}
            </select>
            <button class="btn btn-outline" type="submit">Update status</button>
          </form>
          ${
            canAttachEvidence
              ? `<form class="auditor-attach-form" data-request-id="${escapeHtml(request.id)}" style="display:flex; gap:10px; align-items:center; margin-bottom:12px;">
                  <select name="evidence_id" required style="flex:1; padding:10px; border:1px solid #EAEAEA; border-radius:4px;">
                    <option value="">Attach existing evidence</option>
                    ${eligibleEvidence.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title || item.file_name || `Evidence #${item.id}`)} (${escapeHtml(item.status)})</option>`).join("")}
                  </select>
                  <button class="btn btn-outline" type="submit" ${eligibleEvidence.length ? "" : "disabled"}>Attach</button>
                </form>`
              : ""
          }
          <form class="auditor-comment-form" data-request-id="${escapeHtml(request.id)}" style="display:flex; gap:10px; align-items:flex-start;">
            <textarea name="body" placeholder="Add a comment" required style="flex:1; min-height:48px; padding:10px; border:1px solid #EAEAEA; border-radius:4px;"></textarea>
            <button class="btn btn-outline" type="submit">Send</button>
          </form>
          <p class="status-gray auditor-form-status" style="margin-top:8px;"></p>
        </div>
      `;
      }
    )
    .join("");
}

function renderAuditorRequestForm(auditId, controls) {
  return `
    <div class="card surface-card">
      <h3 class="serif-text section-title">Request evidence</h3>
      <form id="auditor-request-form" data-audit-id="${escapeHtml(auditId)}" style="display:flex; flex-direction:column; gap:12px;">
        <input name="title" type="text" placeholder="Request title" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;" />
        <textarea name="description" placeholder="Describe the sample, population, or period needed" style="padding:10px; border:1px solid #EAEAEA; border-radius:4px; min-height:90px;"></textarea>
        <select name="control_id" style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;">
          <option value="">General request</option>
          ${controls.map((control) => `<option value="${escapeHtml(control.control_id)}">${escapeHtml(getControlRef(control))} - ${escapeHtml(control.title)}</option>`).join("")}
        </select>
        <input name="due_date" type="date" style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;" />
        <button class="btn btn-primary" type="submit">Create request</button>
      </form>
      <p id="auditor-request-status" class="status-gray" style="margin-top:10px;"></p>
    </div>
  `;
}

async function renderAuditorPortal() {
  const audits = await getJson("/api/v1/audits");
  if (!audits.length) {
    return `
      ${shell("Auditor portal", "")}
      <div class="card"><p class="status-gray">No active audits are assigned to this auditor account.</p></div>
    `;
  }

  const selectedAuditId = getSearchParam("audit") || audits[0].id;
  const [workspace, readiness] = await Promise.all([
    getJson(`/api/v1/audits/${selectedAuditId}`),
    getJson(`/api/v1/audits/${selectedAuditId}/readiness/type2`),
  ]);
  const controls = workspace.controls || [];
  const evidence = workspace.evidence || [];
  const requests = workspace.requests || [];
  const findings = workspace.findings || [];

  return `
    <div class="vanta-page wide">
      <div class="auditor-topbar">
        <div class="vanta-card-head">
          <div>
            <h1>Audit: ${escapeHtml(workspace.audit.audit_firm || "Assigned audit")}</h1>
            <p class="vanta-subtle">${escapeHtml(workspace.period?.name || "Audit workspace")} · ${escapeHtml(workspace.audit.framework || "SOC 2")}</p>
          </div>
          <div class="head-actions">
            <button class="btn btn-outline">View SLAs</button>
            <button class="btn btn-outline">Export</button>
          </div>
        </div>
      </div>
      ${renderAuditorAuditPicker(audits, selectedAuditId)}
      <div class="vanta-card">
        <div class="vanta-card-head">
          <div>
            <h2>Evidence</h2>
            <p class="vanta-subtle">Review scoped evidence, request updates, and record auditor assessment.</p>
          </div>
          <span class="vanta-pill">${readiness.overall_score}% ready</span>
        </div>
        <div class="vanta-progress segmented" style="margin-top:16px;">
          <span class="red" style="width:${statusRatio(requests.filter((item) => item.status !== "closed").length, Math.max(evidence.length + requests.length, 1))}%"></span>
          <span class="blue" style="width:${statusRatio(readiness.controls_ready || 0, Math.max(controls.length, 1))}%"></span>
          <span class="gray" style="width:8%"></span>
        </div>
        <div class="audit-readiness-legend">
          <span><strong>${requests.filter((item) => item.status !== "closed").length}</strong> Not ready for audit</span>
          <span><strong>${readiness.controls_ready}</strong> Ready for audit</span>
          <span><strong>${evidence.length}</strong> Evidence items</span>
        </div>
      </div>
      ${vantaToolbar("Search evidence", ["Type", "Created by"])}
      <div class="grid-2 audit-layout">
        <div>
          <div class="surface-panel">
            <h3 class="section-title">Shared evidence</h3>
            ${renderAuditorEvidenceTable(evidence)}
          </div>
          <div class="surface-panel">
            <h3 class="section-title">Controls</h3>
            ${renderAuditorControlsTable(controls)}
          </div>
          <div class="surface-panel">
            <h3 class="section-title">Findings</h3>
            ${
              findings.length
                ? renderTable(["Finding", "Severity", "Status"], findings.map((finding) => `<tr><td>${escapeHtml(finding.title)}</td><td>${getStatusHtml(finding.severity)}</td><td>${getStatusHtml(finding.status)}</td></tr>`))
                : `<p class="status-gray">No findings have been opened.</p>`
            }
          </div>
        </div>
        <div class="audit-side-stack">
          ${renderAuditorRequestForm(selectedAuditId, controls)}
          <div>
            <h3 class="section-title">Requests and comments</h3>
            ${renderAuditorRequests(requests, evidence, controls)}
          </div>
        </div>
      </div>
    </div>
  `;
}

const PAGE_RENDERERS = {
  home: renderHome,
  "my-work": renderMyWork,
  agent: renderAgent,
  tests: renderTests,
  reports: renderReports,
  // Compliance
  "compliance-frameworks": renderFrameworks,
  "compliance-controls": renderControls,
  "compliance-policies": renderPolicies,
  "compliance-documents": renderDocuments,
  "compliance-audits": renderAudits,
  "compliance-settings": renderSettings,
  // Customer trust
  "trust-overview": renderTrustOverview,
  "trust-accounts": renderTrustAccounts,
  "trust-center": renderTrustCenter,
  "trust-knowledge": renderTrustKnowledge,
  "trust-activity": renderTrustActivity,
  "trust-settings": renderSettings,
  // Risk
  "risk-overview": renderRiskOverview,
  "risk-risks": renderRisks,
  "risk-library": renderRiskLibrary,
  "risk-actions": renderRiskActions,
  "risk-snapshots": renderRiskSnapshots,
  "risk-settings": renderSettings,
  // Vendors
  vendors: renderVendors,
  // Assets
  assets: renderAssets,
  "assets-code": renderAssetsCode,
  "assets-vulns": renderAssetsVulns,
  "assets-alerts": renderAssetsAlerts,
  "assets-settings": renderSettings,
  // Personnel
  personnel: renderPersonnel,
  "personnel-computers": renderPersonnelComputers,
  "personnel-access": renderPersonnelAccess,
  "personnel-settings": renderSettings,
  // Other
  integrations: renderIntegrations,
  evidence: renderEnhancedEvidence,
  "auditor-portal": renderAuditorPortal,
  "my-security-tasks": renderSecurityTasks,
  // Legacy aliases
  policies: renderPolicies,
  settings: renderSettings,
};

[
  "add_document_dialog",
  "assets_inventory",
  "assets_inventory_1",
  "assets_inventory_2",
  "audit_firm_filter_expanded",
  "audit_framework_filter_expanded",
  "audit_initiation_success",
  "audit_report_failed_controls",
  "audit_report_in_progress_controls",
  "audit_report_soc_2_type_i",
  "audit_status_filter_expanded",
  "audit_type_filter_expanded",
  "control_detail_view_1",
  "control_detail_view_2",
  "customer_trust_report_pdf_export",
  "edit_control_framework_mapping_expanded",
  "edit_control_upload_evidence_dialog_1",
  "edit_control_upload_evidence_dialog_2",
  "edit_control_view",
  "edit_policy_view_1",
  "edit_policy_view_2",
  "evidence_updated_success",
  "generated_screen_1",
  "generated_screen_2",
  "integrations",
  "jean_edwards_action_tracker",
  "jean_edwards_audit_evidence_list",
  "jean_edwards_audit_evidence_sidebar_expanded",
  "jean_edwards_audit_logs_screen",
  "jean_edwards_audits_overview_1",
  "jean_edwards_audits_overview_2",
  "jean_edwards_audits_redesign",
  "jean_edwards_available_frameworks",
  "jean_edwards_brand_dashboard",
  "jean_edwards_comprehensive_settings",
  "jean_edwards_controls_inventory",
  "jean_edwards_controls_page",
  "jean_edwards_documents_page",
  "jean_edwards_documents_page_redesign",
  "jean_edwards_evidence_detail_panel",
  "jean_edwards_evidence_locker",
  "jean_edwards_je_agent_interface",
  "jean_edwards_login_screen",
  "jean_edwards_my_security_tasks",
  "jean_edwards_my_work_screen",
  "jean_edwards_policies_page",
  "jean_edwards_policies_page_redesign_1",
  "jean_edwards_policies_page_redesign_2",
  "jean_edwards_policies_redesign",
  "jean_edwards_report_detail_customer_trust",
  "jean_edwards_reports_overview",
  "jean_edwards_risk_library_1",
  "jean_edwards_risk_library_2",
  "jean_edwards_risk_overview_1",
  "jean_edwards_risk_overview_2",
  "jean_edwards_risk_register_1",
  "jean_edwards_risk_register_2",
  "jean_edwards_security_sso_settings",
  "jean_edwards_settings_permissions",
  "jean_edwards_tests_detail_page",
  "jean_edwards_trust_center_preview_1",
  "jean_edwards_trust_center_preview_2",
  "jean_edwards_vanta_agent",
  "jean_edwards_vendors_list_1",
  "jean_edwards_vendors_list_2",
  "jean_edwards_vendors_page",
  "new_audit_firm_selection",
  "new_audit_framework_scoping",
  "new_audit_review_confirm",
  "new_audit_timeline_contacts",
  "personnel_directory",
  "personnel_directory_1",
  "personnel_directory_2",
  "personnel_directory_3",
  "policy_comparison_unified_diff_view",
  "policy_comparison_v2.4_vs_v2.5",
  "policy_details_v2.4_archived",
  "policy_version_history_details",
  "publish_policy_confirmation",
  "remediation_details_ac_01",
  "remediation_details_ds_05",
  "update_evidence_dialog",
  "updated_evidence_locker",
  "updated_policy_version_history",
  "vendor_detail_view_1",
  "vendor_detail_view_2",
  "vendor_documents_tab_1",
  "vendor_documents_tab_2",
  "image.png",
  "image.png_1",
  "image.png_2",
  "image.png_3",
  "image.png_4",
  "image.png_5",
  "image.png_6",
  "image.png_7",
  "image.png_8",
  "image.png_9",
  "image.png_10",
  "image.png_11",
  "image.png_12",
  "image.png_13",
  "image.png_14",
  "image.png_15",
  "image.png_16",
  "image.png_17",
  "image.png_18",
  "image.png_19",
  "image.png_20",
  "image.png_21",
  "image.png_22",
  "image.png_23",
  "image.png_24",
  "image.png_25",
  "screenshot_2026_03_12_140250.png",
  "screenshot_2026_03_12_140301.png",
  "screenshot_2026_03_12_140306.png",
  "screenshot_2026_03_12_140316.png",
].forEach((route) => ROUTES.add(route));

Object.assign(PAGE_RENDERERS, {
  add_document_dialog: renderDocuments,
  assets_inventory: renderAssets,
  assets_inventory_1: renderAssets,
  assets_inventory_2: renderAssets,
  audit_firm_filter_expanded: () => renderAuditVariant("Audit Firm Filter"),
  audit_framework_filter_expanded: () => renderAuditVariant("Audit Framework Filter"),
  audit_initiation_success: () => renderAuditVariant("Audit Initiation"),
  audit_report_failed_controls: () => renderAuditVariant("Audit Report - Failed Controls"),
  audit_report_in_progress_controls: () => renderAuditVariant("Audit Report - In Progress Controls"),
  audit_report_soc_2_type_i: () => renderAuditVariant("Audit Report - SOC 2 Type I"),
  audit_status_filter_expanded: () => renderAuditVariant("Audit Status Filter"),
  audit_type_filter_expanded: () => renderAuditVariant("Audit Type Filter"),
  control_detail_view_1: () => renderDetailedControlWorkspace("Control Detail View"),
  control_detail_view_2: () => renderDetailedControlWorkspace("Control Detail View"),
  customer_trust_report_pdf_export: () => renderTrustReportDetail("Customer Trust Report PDF Export"),
  edit_control_framework_mapping_expanded: () => renderDetailedControlWorkspace("Edit Control Framework Mapping"),
  edit_control_upload_evidence_dialog_1: renderEnhancedEvidence,
  edit_control_upload_evidence_dialog_2: renderEnhancedEvidence,
  edit_control_view: () => renderDetailedControlWorkspace("Edit Control"),
  edit_policy_view_1: () => renderPolicyLifecycle("Edit Policy"),
  edit_policy_view_2: () => renderPolicyLifecycle("Edit Policy"),
  evidence_updated_success: renderEnhancedEvidence,
  generated_screen_1: () => renderReferenceCapture("generated_screen_1"),
  generated_screen_2: () => renderReferenceCapture("generated_screen_2"),
  jean_edwards_action_tracker: renderRiskActions,
  jean_edwards_audit_evidence_list: () => renderAuditVariant("Audit Evidence List"),
  jean_edwards_audit_evidence_sidebar_expanded: () => renderAuditVariant("Audit Evidence Sidebar"),
  jean_edwards_audit_logs_screen: renderReports,
  jean_edwards_audits_overview_1: renderAudits,
  jean_edwards_audits_overview_2: renderAudits,
  jean_edwards_audits_redesign: renderAudits,
  jean_edwards_available_frameworks: renderFrameworks,
  jean_edwards_brand_dashboard: renderHome,
  jean_edwards_comprehensive_settings: renderSettings,
  jean_edwards_controls_inventory: renderControls,
  jean_edwards_controls_page: renderControls,
  jean_edwards_documents_page: renderDocuments,
  jean_edwards_documents_page_redesign: renderDocuments,
  jean_edwards_evidence_detail_panel: renderEnhancedEvidence,
  jean_edwards_evidence_locker: renderEnhancedEvidence,
  jean_edwards_je_agent_interface: renderAgent,
  jean_edwards_login_screen: () => renderReferenceCapture("jean_edwards_login_screen"),
  jean_edwards_my_security_tasks: renderSecurityTasks,
  jean_edwards_my_work_screen: renderMyWork,
  jean_edwards_policies_page: renderPolicies,
  jean_edwards_policies_page_redesign_1: renderPolicies,
  jean_edwards_policies_page_redesign_2: renderPolicies,
  jean_edwards_policies_redesign: renderPolicies,
  jean_edwards_report_detail_customer_trust: () => renderTrustReportDetail("Customer Trust Report Detail"),
  jean_edwards_reports_overview: renderReports,
  jean_edwards_risk_library_1: renderRiskLibrary,
  jean_edwards_risk_library_2: renderRiskLibrary,
  jean_edwards_risk_overview_1: renderRiskOverview,
  jean_edwards_risk_overview_2: renderRiskOverview,
  jean_edwards_risk_register_1: renderRisks,
  jean_edwards_risk_register_2: renderRisks,
  jean_edwards_security_sso_settings: renderSettings,
  jean_edwards_settings_permissions: renderSettings,
  jean_edwards_tests_detail_page: renderTests,
  jean_edwards_trust_center_preview_1: renderTrustCenter,
  jean_edwards_trust_center_preview_2: renderTrustCenter,
  jean_edwards_vanta_agent: renderAgent,
  jean_edwards_vendors_list_1: renderVendors,
  jean_edwards_vendors_list_2: renderVendors,
  jean_edwards_vendors_page: renderVendors,
  new_audit_firm_selection: () => renderAuditVariant("New Audit - Firm Selection"),
  new_audit_framework_scoping: () => renderAuditVariant("New Audit - Framework Scoping"),
  new_audit_review_confirm: () => renderAuditVariant("New Audit - Review & Confirm"),
  new_audit_timeline_contacts: () => renderAuditVariant("New Audit - Timeline & Contacts"),
  personnel_directory: renderPersonnel,
  personnel_directory_1: renderPersonnel,
  personnel_directory_2: renderPersonnel,
  personnel_directory_3: renderPersonnel,
  policy_comparison_unified_diff_view: () => renderPolicyLifecycle("Policy Comparison - Unified Diff"),
  "policy_comparison_v2.4_vs_v2.5": () => renderPolicyLifecycle("Policy Comparison - v2.4 vs v2.5"),
  "policy_details_v2.4_archived": () => renderPolicyLifecycle("Policy Details - Archived"),
  policy_version_history_details: () => renderPolicyLifecycle("Policy Version History"),
  publish_policy_confirmation: () => renderPolicyLifecycle("Publish Policy Confirmation"),
  remediation_details_ac_01: renderRiskActions,
  remediation_details_ds_05: renderRiskActions,
  update_evidence_dialog: renderEnhancedEvidence,
  updated_evidence_locker: renderEnhancedEvidence,
  updated_policy_version_history: () => renderPolicyLifecycle("Updated Policy Version History"),
  vendor_detail_view_1: () => renderVendorDetailWorkspace("Vendor Detail View"),
  vendor_detail_view_2: () => renderVendorDetailWorkspace("Vendor Detail View"),
  vendor_documents_tab_1: () => renderVendorDetailWorkspace("Vendor Documents"),
  vendor_documents_tab_2: () => renderVendorDetailWorkspace("Vendor Documents"),
  "image.png": () => renderReferenceCapture("image.png"),
  "image.png_1": () => renderReferenceCapture("image.png_1"),
  "image.png_2": () => renderReferenceCapture("image.png_2"),
  "image.png_3": () => renderReferenceCapture("image.png_3"),
  "image.png_4": () => renderReferenceCapture("image.png_4"),
  "image.png_5": () => renderReferenceCapture("image.png_5"),
  "image.png_6": () => renderReferenceCapture("image.png_6"),
  "image.png_7": () => renderReferenceCapture("image.png_7"),
  "image.png_8": () => renderReferenceCapture("image.png_8"),
  "image.png_9": () => renderReferenceCapture("image.png_9"),
  "image.png_10": () => renderReferenceCapture("image.png_10"),
  "image.png_11": () => renderReferenceCapture("image.png_11"),
  "image.png_12": () => renderReferenceCapture("image.png_12"),
  "image.png_13": () => renderReferenceCapture("image.png_13"),
  "image.png_14": () => renderReferenceCapture("image.png_14"),
  "image.png_15": () => renderReferenceCapture("image.png_15"),
  "image.png_16": () => renderReferenceCapture("image.png_16"),
  "image.png_17": () => renderReferenceCapture("image.png_17"),
  "image.png_18": () => renderReferenceCapture("image.png_18"),
  "image.png_19": () => renderReferenceCapture("image.png_19"),
  "image.png_20": () => renderReferenceCapture("image.png_20"),
  "image.png_21": () => renderReferenceCapture("image.png_21"),
  "image.png_22": () => renderReferenceCapture("image.png_22"),
  "image.png_23": () => renderReferenceCapture("image.png_23"),
  "image.png_24": () => renderReferenceCapture("image.png_24"),
  "image.png_25": () => renderReferenceCapture("image.png_25"),
  "screenshot_2026_03_12_140250.png": () => renderReferenceCapture("screenshot_2026_03_12_140250.png"),
  "screenshot_2026_03_12_140301.png": () => renderReferenceCapture("screenshot_2026_03_12_140301.png"),
  "screenshot_2026_03_12_140306.png": () => renderReferenceCapture("screenshot_2026_03_12_140306.png"),
  "screenshot_2026_03_12_140316.png": () => renderReferenceCapture("screenshot_2026_03_12_140316.png"),
});

const GRAPH_ROUTE_CONFIG = {
  control: { route: "compliance-controls", param: "control", label: "Controls", detailMode: "drawer" },
  policy: { route: "compliance-policies", param: "policy", label: "Policies", detailMode: "page" },
  document: { route: "compliance-documents", param: "document", label: "Documents", detailMode: "page" },
  audit: { route: "compliance-audits", param: "audit", label: "Audits", detailMode: "page" },
  risk: { route: "risk-risks", param: "risk", label: "Risk scenarios", detailMode: "page" },
  vendor: { route: "vendors", param: "vendor", label: "Vendors", detailMode: "page" },
  test: { route: "tests", param: "test", label: "Tests", detailMode: "page" },
  integration: { route: "integrations", param: "integration", label: "Integrations", detailMode: "page" },
  framework: { route: "compliance-frameworks", param: "framework", label: "Frameworks", detailMode: "page" },
};

async function getGraphList(objectType) {
  return (await getJson(`/graph/${encodeURIComponent(objectType)}`)).items;
}

async function getGraphDetail(objectType, objectKey) {
  return getJson(`/graph/${encodeURIComponent(objectType)}/${encodeURIComponent(objectKey)}`);
}

async function getGraphOptions(objectType, objectKey) {
  return (await getJson(`/graph/${encodeURIComponent(objectType)}/${encodeURIComponent(objectKey)}/options`)).items;
}

function openGraphObject(objectType, objectKey) {
  _relationshipModal.open = false;
  const config = GRAPH_ROUTE_CONFIG[objectType];
  if (!config) return;
  navigateTo(config.route, { [config.param]: objectKey });
}

function clearGraphObject(objectType) {
  const config = GRAPH_ROUTE_CONFIG[objectType];
  if (!config) return;
  _relationshipModal.open = false;
  setRouteSearchParam(config.param, null);
  renderCurrentPage();
}

async function openRelationshipModal(sourceType, sourceKey) {
  const options = await getGraphOptions(sourceType, sourceKey);
  _relationshipModal.open = true;
  _relationshipModal.sourceType = sourceType;
  _relationshipModal.sourceKey = String(sourceKey);
  _relationshipModal.options = options;
  _relationshipModal.typeFilter = options[0]?.object_type || "all";
  _relationshipModal.search = "";
  _relationshipModal.selectedType = _relationshipModal.typeFilter === "all" ? (options[0]?.object_type || "") : _relationshipModal.typeFilter;
  _relationshipModal.selectedKey = "";
  renderCurrentPage();
}

function closeRelationshipModal() {
  _relationshipModal.open = false;
  _relationshipModal.options = [];
  _relationshipModal.search = "";
  _relationshipModal.selectedKey = "";
  _relationshipModal.selectedType = "";
}

function setRelationshipTypeFilter(value) {
  _relationshipModal.typeFilter = value;
  if (value !== "all") {
    _relationshipModal.selectedType = value;
  }
  _relationshipModal.selectedKey = "";
  renderCurrentPage();
}

function setRelationshipSearch(value) {
  _relationshipModal.search = value;
  renderCurrentPage();
}

function selectRelationshipTarget(objectType, objectKey) {
  _relationshipModal.selectedType = objectType;
  _relationshipModal.selectedKey = String(objectKey);
  renderCurrentPage();
}

function getFilteredRelationshipOptions() {
  const query = _relationshipModal.search.trim().toLowerCase();
  return _relationshipModal.options.filter((item) => {
    if (_relationshipModal.typeFilter !== "all" && item.object_type !== _relationshipModal.typeFilter) {
      return false;
    }
    if (!query) return true;
    return [item.title, item.subtitle, item.external_key, item.object_type]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
  });
}

function renderRelationshipModal() {
  if (!_relationshipModal.open) return "";
  const options = getFilteredRelationshipOptions();
  const types = ["all", ...new Set(_relationshipModal.options.map((item) => item.object_type))];
  return `
    <div class="relationship-modal-shell">
      <div class="relationship-modal-backdrop" data-close-relationship="1"></div>
      <div class="relationship-modal">
        <div class="relationship-modal-head">
          <div>
            <p class="mapped-elements-kicker">Create relationship</p>
            <h3 class="serif-text section-title" style="margin-bottom:4px;">Add connection</h3>
            <p class="graph-detail-subtitle">Link this ${escapeHtml(_relationshipModal.sourceType)} to another object anywhere in the program.</p>
          </div>
          <button class="detail-drawer-close" data-close-relationship="1">Close</button>
        </div>
        <div class="relationship-toolbar">
          <select id="relationship-type-filter" class="relationship-select">
            ${types.map((type) => `<option value="${escapeHtml(type)}" ${_relationshipModal.typeFilter === type ? "selected" : ""}>${escapeHtml(type === "all" ? "All object types" : GRAPH_ROUTE_CONFIG[type]?.label || type)}</option>`).join("")}
          </select>
          <input id="relationship-search" class="relationship-search" type="search" placeholder="Search by name or key" value="${escapeHtml(_relationshipModal.search)}" />
        </div>
        <div class="relationship-option-list">
          ${
            options.length
              ? options.map((item) => `
                  <button class="relationship-option ${_relationshipModal.selectedKey === String(item.external_key) && _relationshipModal.selectedType === item.object_type ? "active" : ""}" data-relationship-option="1" data-target-type="${escapeHtml(item.object_type)}" data-target-key="${escapeHtml(item.external_key)}">
                    <span class="relationship-option-title">${escapeHtml(item.title)}</span>
                    <span class="relationship-option-meta">${escapeHtml((GRAPH_ROUTE_CONFIG[item.object_type] || {}).label || item.object_type)} · ${escapeHtml(item.external_key)}${item.subtitle ? ` · ${escapeHtml(item.subtitle)}` : ""}</span>
                  </button>
                `).join("")
              : `<p class="status-gray">No objects match this filter.</p>`
          }
        </div>
        <div class="relationship-modal-actions">
          <button class="btn btn-outline" data-close-relationship="1">Cancel</button>
          <button class="btn btn-primary" id="relationship-submit" ${!_relationshipModal.selectedKey ? "disabled" : ""}>Add connection</button>
        </div>
      </div>
    </div>
  `;
}

function renderGraphMetric(label, value, note = "") {
  return `
    <div class="card graph-metric-card">
      <p class="graph-metric-label">${escapeHtml(label)}</p>
      <div class="metric-value">${escapeHtml(value)}</div>
      ${note ? `<p class="graph-metric-note">${escapeHtml(note)}</p>` : ""}
    </div>
  `;
}

function renderGraphSummaryGrid(detail) {
  const metadata = detail.metadata || {};
  const entries = [
    ["Status", detail.status || "-"],
    ["Owner", detail.owner || "-"],
    ["Subtitle", detail.subtitle || "-"],
  ];

  if (detail.object_type === "control") {
    entries.push(["Control ID", metadata.control_id || detail.subtitle || "-"]);
    entries.push(["Type I", metadata.type1_ready ? "Ready" : "Not ready"]);
    entries.push(["Type II", metadata.type2_ready ? "Ready" : "Not ready"]);
    entries.push(["Next review", formatDate(metadata.next_review_at)]);
  } else if (detail.object_type === "policy") {
    entries.push(["Renewal", metadata.renewal_frequency || "-"]);
    entries.push(["Frameworks", (metadata.frameworks || []).join(", ") || "-"]);
    entries.push(["Latest version", metadata.latest_version_label || "-"]);
  } else if (detail.object_type === "document") {
    entries.push(["Source", detail.subtitle || "-"]);
    entries.push(["Collected", formatDate(metadata.collected_at)]);
    entries.push(["Artifact", metadata.artifact_path || "-"]);
  } else if (detail.object_type === "risk") {
    entries.push(["Inherent risk", metadata.inherent_risk ?? "-"]);
    entries.push(["Residual risk", metadata.residual_risk ?? "-"]);
    entries.push(["Treatment", metadata.treatment_plan || "-"]);
    entries.push(["Category", metadata.category || "-"]);
  } else if (detail.object_type === "vendor") {
    entries.push(["Category", metadata.category || "-"]);
    entries.push(["Inherent risk", metadata.inherent_risk || "-"]);
    entries.push(["Security review", metadata.security_review_status || "-"]);
  } else if (detail.object_type === "audit") {
    entries.push(["Audit type", metadata.audit_type || "-"]);
    entries.push(["Firm", metadata.firm_name || "-"]);
    entries.push(["Period", metadata.audit_period_id || "-"]);
  } else if (detail.object_type === "test") {
    entries.push(["SLA", metadata.sla_days ? `${metadata.sla_days} days` : "-"]);
    entries.push(["Integration", metadata.integration_name || "-"]);
  } else if (detail.object_type === "integration") {
    entries.push(["Capabilities", (metadata.capabilities || []).join(", ") || "-"]);
  }

  return `
    <div class="card graph-summary-card">
      <div class="graph-summary-grid">
        ${entries
          .map(
            ([label, value]) => `
              <div class="graph-summary-item">
                <p class="graph-summary-label">${escapeHtml(label)}</p>
                <p class="graph-summary-value">${escapeHtml(value || "-")}</p>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderMappedElements(detail, compact = false) {
  const sections = detail.mapped_elements || [];
  const headerClass = compact ? "mapped-elements-header compact" : "mapped-elements-header";
  return `
    <div class="card mapped-elements-card ${compact ? "compact" : ""}">
      <div class="${headerClass}">
        <div>
          <p class="mapped-elements-kicker">Connected objects</p>
          <h3 class="serif-text section-title" style="margin-bottom:4px;">Mapped elements</h3>
        </div>
        <button class="btn btn-outline relationship-add" data-source-type="${escapeHtml(detail.object_type)}" data-source-key="${escapeHtml(detail.external_key)}">Add connection</button>
      </div>
      <div class="mapped-elements-sections">
        ${
          sections.length
            ? sections
                .map(
                  (section) => `
                    <section class="mapped-section">
                      <div class="mapped-section-head">
                        <h4>${escapeHtml(section.section)}</h4>
                        <span>${section.items.length}</span>
                      </div>
                      <div class="mapped-list">
                        ${section.items
                          .map(
                            (item) => `
                              <article class="mapped-item">
                                <button class="mapped-item-main" data-open-object="1" data-object-type="${escapeHtml(item.object_type)}" data-object-key="${escapeHtml(item.external_key)}">
                                  <span class="mapped-item-title">${escapeHtml(item.title)}</span>
                                  <span class="mapped-item-sub">${escapeHtml(item.subtitle || item.status || item.link_type || "")}</span>
                                </button>
                                <div class="mapped-item-meta">
                                  ${item.status ? `<span class="mapped-pill">${escapeHtml(item.status)}</span>` : ""}
                                  <button class="mapped-item-remove relationship-remove" data-relationship-id="${item.relationship_id}" title="Remove connection">Remove</button>
                                </div>
                              </article>
                            `
                          )
                          .join("")}
                      </div>
                    </section>
                  `
                )
                .join("")
            : `<p class="status-gray">No mapped elements yet.</p>`
        }
      </div>
    </div>
  `;
}

function renderGraphPageFrame(detail, backRoute, backLabel, body) {
  return `
    <div class="graph-detail-page">
      <button class="graph-back-link" data-route-target="${escapeHtml(backRoute)}">${escapeHtml(backLabel)}</button>
      <header class="graph-detail-header">
        <div>
          <p class="graph-detail-eyebrow">${escapeHtml((GRAPH_ROUTE_CONFIG[detail.object_type] || {}).label || detail.object_type)}</p>
          <h1 class="page-title serif-text" style="margin-bottom:8px;">${escapeHtml(detail.title)}</h1>
          <p class="graph-detail-subtitle">${escapeHtml(detail.description || detail.subtitle || "")}</p>
        </div>
        <div class="head-actions">
          <button class="btn btn-outline relationship-add" data-source-type="${escapeHtml(detail.object_type)}" data-source-key="${escapeHtml(detail.external_key)}">Add connection</button>
        </div>
      </header>
      ${body}
    </div>
  `;
}

function renderAuditWorkspaceTable(workspace) {
  if (!workspace?.controls?.length) {
    return `<div class="card"><p class="status-gray">No controls are in scope for this audit yet.</p></div>`;
  }
  return renderTable(
    ["Control", "Title", "State", "Evidence", "Finding"],
    workspace.controls.map(
      (control) => `
        <tr>
          <td style="font-weight:500;">${escapeHtml(control.control_id)}</td>
          <td>${escapeHtml(control.title)}</td>
          <td>${getStatusHtml(control.audit_state)}</td>
          <td>${getStatusHtml(control.latest_evidence_status || "missing")}</td>
          <td>${escapeHtml(control.issue || "-")}</td>
        </tr>
      `
    )
  );
}

function renderAuditReadinessBar(workspace) {
  const controls = workspace?.controls || [];
  if (!controls.length) return "";
  const segments = [
    { label: "Ready", count: controls.filter((item) => item.audit_state === "ready").length, className: "good" },
    { label: "Attention", count: controls.filter((item) => item.audit_state !== "ready").length, className: "alert" },
  ];
  const total = Math.max(segments.reduce((sum, segment) => sum + segment.count, 0), 1);
  return `
    <div class="surface-panel">
      <h3 class="serif-text section-title">Evidence tracker</h3>
      <div class="audit-readiness-bar">
        ${segments
          .map((segment) => `<span class="audit-readiness-segment ${segment.className}" style="width:${(segment.count / total) * 100}%"></span>`)
          .join("")}
      </div>
      <div class="audit-readiness-legend">
        ${segments
          .map((segment) => `<span><strong>${segment.count}</strong> ${escapeHtml(segment.label)}</span>`)
          .join("")}
      </div>
    </div>
  `;
}

function renderDocumentHistory(detail) {
  const metadata = detail.metadata || {};
  const currentCollected = metadata.collected_at ? formatDate(metadata.collected_at) : "-";
  const rows = [
    `<tr>
      <td style="font-weight:500;">${escapeHtml(detail.title)}</td>
      <td>${escapeHtml(detail.subtitle || "manual")}</td>
      <td>${currentCollected}</td>
      <td>${getStatusHtml(detail.status || "submitted")}</td>
    </tr>`,
  ];
  return renderTable(["Version", "Source", "Collected", "Status"], rows);
}

function renderAuditAccessManagement(detail, eligibleAuditors) {
  const workspace = detail.workspace || {};
  const auditors = workspace.auditors || [];
  const auditId = detail.external_key;
  const assignedIds = new Set(auditors.map((item) => String(item.user_id)));
  const availableAuditors = eligibleAuditors.filter((item) => !assignedIds.has(String(item.id)));
  const assignedRows = auditors.length
    ? auditors.map(
        (auditor) => `
          <tr>
            <td>
              <div style="font-weight:500;">${escapeHtml(auditor.name || auditor.email)}</div>
              <div class="status-gray" style="font-size:0.82rem;">${escapeHtml(auditor.email)}</div>
            </td>
            <td class="status-gray">${formatDate(auditor.access_expires_at || auditor.token_expires_at)}</td>
            <td>
              <input readonly value="${escapeHtml(`${window.location.origin}/?token=${auditor.scoped_token || ""}#auditor-portal`)}" style="width:100%; padding:8px; border:1px solid #EAEAEA; border-radius:4px;" />
            </td>
            <td><button class="btn btn-outline audit-revoke-btn" data-audit-id="${escapeHtml(auditId)}" data-user-id="${escapeHtml(auditor.user_id)}">Revoke</button></td>
          </tr>
        `
      )
    : [`<tr><td colspan="4" class="status-gray">No auditors assigned yet.</td></tr>`];

  return `
    <div class="card graph-story-card">
      <div class="mapped-elements-header compact">
        <div>
          <p class="mapped-elements-kicker">Auditor access</p>
          <h3 class="serif-text section-title" style="margin-bottom:4px;">Manage external access</h3>
          <p class="status-gray">Assign auditors, review link expiry, revoke access, and preview their workspace.</p>
        </div>
        <button class="btn btn-outline audit-preview-btn" data-audit-id="${escapeHtml(auditId)}">Preview as auditor</button>
      </div>
      <form id="audit-auditor-form" data-audit-id="${escapeHtml(auditId)}" style="display:grid; grid-template-columns: minmax(180px, 1fr) 180px auto; gap:10px; align-items:center; margin-bottom:16px;">
        <select name="user_id" required style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;">
          <option value="">Select auditor</option>
          ${availableAuditors.map((auditor) => `<option value="${escapeHtml(auditor.id)}">${escapeHtml(auditor.name || auditor.email)} (${escapeHtml(auditor.email)})</option>`).join("")}
        </select>
        <input name="access_expires_at" type="date" style="padding:10px; border:1px solid #EAEAEA; border-radius:4px;" />
        <button class="btn btn-primary" type="submit" ${availableAuditors.length ? "" : "disabled"}>Assign</button>
      </form>
      <p id="audit-auditor-status" class="status-gray" style="margin-bottom:12px;"></p>
      ${renderTable(["Auditor", "Expires", "Portal link", ""], assignedRows)}
      <div id="audit-preview-result" class="surface-panel" style="display:none; margin-top:16px;"></div>
    </div>
  `;
}

async function renderObjectSpecificPanels(detail) {
  const metadata = detail.metadata || {};
  if (detail.object_type === "policy") {
    return `
      <div class="card graph-story-card">
        <h3 class="serif-text section-title">Version status</h3>
        <p class="graph-story-title">${escapeHtml(metadata.latest_version_label || "Approved version")}</p>
        <p class="status-gray">Renew ${escapeHtml(metadata.renewal_frequency || "annually")} with linked controls and audit references kept in sync.</p>
      </div>
    `;
  }
  if (detail.object_type === "document") {
    const evidence = detail.evidence || {};
    return `
      <div class="card graph-story-card">
        <h3 class="serif-text section-title">Document instructions</h3>
        <p class="graph-story-title">${escapeHtml(detail.title)}</p>
        <p class="status-gray">${escapeHtml(detail.description || "This document supports linked controls and audit evidence flows.")}</p>
      </div>
      <div class="card graph-story-card">
        <h3 class="serif-text section-title">Latest version</h3>
        <p class="graph-story-title">${escapeHtml(evidence.name || detail.title)}</p>
        <p class="status-gray">Collected ${formatDate((detail.metadata || {}).collected_at)} from ${escapeHtml(detail.subtitle || "manual")}. Artifact path: ${escapeHtml((detail.metadata || {}).artifact_path || "-")}</p>
      </div>
      <div class="card graph-story-card">
        <h3 class="serif-text section-title">Version history</h3>
        ${renderDocumentHistory(detail)}
      </div>
    `;
  }
  if (detail.object_type === "risk") {
    return `
      <div class="card graph-story-card">
        <h3 class="serif-text section-title">Treatment plan</h3>
        <p class="graph-story-title">${escapeHtml(metadata.treatment_plan || "Mitigate")}</p>
        <p class="status-gray">Treatment status: ${escapeHtml(metadata.treatment_status || "incomplete")}. This view keeps controls, tasks, and policies connected to the scenario.</p>
      </div>
    `;
  }
  if (detail.object_type === "vendor") {
    return `
      <div class="card graph-story-card">
        <h3 class="serif-text section-title">Security review</h3>
        <p class="graph-story-title">${escapeHtml(metadata.security_review_status || "needs_review")}</p>
        <p class="status-gray">Linked integrations, risks, and documents keep the vendor record connected to the rest of the program.</p>
      </div>
    `;
  }
  if (detail.object_type === "audit") {
    const eligibleAuditors = await getJson("/api/v1/auditors").catch(() => []);
    return `
      ${renderAuditReadinessBar(detail.workspace)}
      <div class="grid-3" style="margin-bottom:18px;">
        ${renderGraphMetric("Controls in scope", detail.workspace?.summary?.controls_in_scope || 0, "Current audit scope")}
        ${renderGraphMetric("Evidence items", detail.workspace?.summary?.evidence_items || 0, "Collected artifacts")}
        ${renderGraphMetric("Open findings", detail.workspace?.summary?.open_findings || 0, "Needs follow-up")}
      </div>
      ${renderAuditAccessManagement(detail, eligibleAuditors)}
      ${renderAuditWorkspaceTable(detail.workspace)}
    `;
  }
  if (detail.object_type === "test") {
    return `
      <div class="vanta-card graph-story-card">
        <div class="vanta-card-head">
          <div>
            <h3 class="section-title">Latest version</h3>
            <p class="graph-story-title">${escapeHtml(detail.title)}</p>
            <p class="vanta-subtle">Completed evidence and renewal history stay tied to the mapped controls.</p>
          </div>
          ${getStatusHtml(detail.status || "attention")}
        </div>
      </div>
      <div class="vanta-card graph-story-card">
        <h3 class="section-title">Document instructions</h3>
        <p class="vanta-subtle">Review implementation and evidence collection guidance before renewing this sample.</p>
      </div>
    `;
  }
  if (detail.object_type === "integration") {
    return `
      <div class="card graph-story-card">
        <h3 class="serif-text section-title">Connection scope</h3>
        <p class="graph-story-title">${escapeHtml(detail.status || "review")}</p>
        <p class="status-gray">Capabilities: ${escapeHtml((metadata.capabilities || []).join(", ") || "access")}</p>
      </div>
    `;
  }
  return "";
}

async function renderGraphDetailPage(objectType, objectKey) {
  const detail = await getGraphDetail(objectType, objectKey);
  const config = GRAPH_ROUTE_CONFIG[objectType];
  const objectPanels = await renderObjectSpecificPanels(detail);
  return renderGraphPageFrame(
    detail,
    config.route,
    `Back to ${config.label}`,
    `
      <div class="grid-2 audit-layout graph-detail-layout">
        <div class="graph-main-stack">
          ${renderGraphSummaryGrid(detail)}
          ${objectPanels}
        </div>
        <div class="graph-side-stack">
          ${renderMappedElements(detail)}
        </div>
      </div>
    `
  );
}

function renderControlDrawer(detail) {
  const metadata = detail.metadata || {};
  return `
    <aside class="detail-drawer-shell">
      <div class="detail-drawer-backdrop" onclick="backToControls()"></div>
      <div class="detail-drawer">
        <div class="detail-drawer-head">
          <div>
            <p class="graph-detail-eyebrow">Control</p>
            <h2>${escapeHtml(detail.title)}</h2>
            <p class="graph-detail-subtitle">${escapeHtml(detail.description || "")}</p>
          </div>
          <button class="detail-drawer-close" onclick="backToControls()">x</button>
        </div>
        <div class="vanta-detail-meta">
          <span class="vanta-pill">ID ${escapeHtml(detail.external_key || detail.subtitle || "-")}</span>
          <span class="vanta-pill">Source ${escapeHtml(detail.subtitle || "JEC")}</span>
          <span class="vanta-pill">Owner ${escapeHtml(detail.owner || "Unassigned")}</span>
        </div>
        <div class="vanta-drawer-tabs">
          <span class="active">Mapped elements</span>
          <span>History</span>
          <span>Comments</span>
        </div>
        <div class="vanta-card">
          <div class="graph-summary-grid">
            <div class="graph-summary-item"><p class="graph-summary-label">Status</p><p class="graph-summary-value">${getStatusHtml(detail.status || "draft")}</p></div>
            <div class="graph-summary-item"><p class="graph-summary-label">Domain</p><p class="graph-summary-value">${escapeHtml(metadata.domain || metadata.category || "Compliance")}</p></div>
            <div class="graph-summary-item"><p class="graph-summary-label">Type I readiness</p><p class="graph-summary-value">${metadata.type1_ready ? `<span class="status-green">ready</span>` : `<span class="status-gray">pending</span>`}</p></div>
            <div class="graph-summary-item"><p class="graph-summary-label">Type II readiness</p><p class="graph-summary-value">${metadata.type2_ready ? `<span class="status-green">ready</span>` : `<span class="status-gray">pending</span>`}</p></div>
          </div>
        </div>
        ${renderMappedElements(detail, true)}
        <div class="vanta-card mapped-elements-card compact">
          <div class="mapped-elements-header compact">
            <div>
              <p class="mapped-elements-kicker">Evidence</p>
              <h3 class="section-title" style="margin-bottom:4px;">Recent evidence</h3>
            </div>
            <button class="btn btn-outline" data-route-target="evidence" data-param-control_id="${escapeHtml(detail.external_key)}">Add evidence</button>
          </div>
          ${
            detail.evidence?.length
              ? renderTable(
                  ["Name", "Source", "Status"],
                  detail.evidence.slice(0, 8).map(
                    (item) => `
                      <tr>
                        <td style="font-weight:500;">${escapeHtml(item.name)}</td>
                        <td>${escapeHtml(item.source)}</td>
                        <td>${getStatusHtml(item.status)}</td>
                      </tr>
                    `
                  )
                )
              : `<p class="status-gray">No evidence attached yet.</p>`
          }
        </div>
        <div class="vanta-card">
          <div class="mapped-elements-header compact">
            <div>
              <p class="mapped-elements-kicker">Frameworks</p>
              <h3 class="section-title" style="margin-bottom:4px;">SOC 2 mappings</h3>
            </div>
          </div>
          <span class="vanta-pill">SOC 2</span>
          <span class="vanta-pill">CC series</span>
        </div>
      </div>
    </aside>
  `;
}

async function renderControlsGraph() {
  const controlKey = getSearchParam("control");
  const controls = await getGraphList("control");
  const selectedDetail = controlKey ? await getGraphDetail("control", controlKey) : null;

  const implementedCount = controls.filter((item) => item.status === "implemented").length;
  const readyCount = controls.filter((item) => (item.metadata || {}).type1_ready).length;
  const assignedCount = controls.filter((item) => item.owner).length;
  const rows = controls.map(
    (control) => `
      <tr>
        <td><input type="checkbox" aria-label="Select ${escapeHtml(control.external_key)}" /></td>
        <td style="font-weight:500;">${escapeHtml(control.subtitle || control.external_key)}</td>
        <td>
          <div style="font-weight:500; color:var(--text-primary);">${escapeHtml(control.title)}</div>
          <div class="status-gray" style="font-size:0.85rem; margin-top:4px;">${escapeHtml(control.description || "")}</div>
        </td>
        <td>${escapeHtml(control.owner || "Unassigned")}</td>
        <td><span class="vanta-pill">SOC 2</span></td>
        <td>${getStatusHtml(control.status || "draft")}</td>
        <td>${(control.metadata || {}).type1_ready ? `<span class="status-green">ready</span>` : `<span class="status-gray">pending</span>`}</td>
        <td><button class="btn btn-outline" onclick="openControlDetail('${escapeHtml(control.external_key)}')">...</button></td>
      </tr>
    `
  );

  return `
    <div class="vanta-page wide">
      ${vantaHeader("Controls", "Control ownership, framework mapping, and evidence readiness", `${routeButton("Add control", "compliance-controls")} <button class="btn btn-outline">...</button>`)}
      <div class="vanta-kpi-grid" style="margin-bottom:14px;">
        <div class="vanta-card">
          <h2>Assignment</h2>
          <div style="display:grid; grid-template-columns:180px 1fr; gap:18px; align-items:center;">
            <div class="vanta-donut" style="--value:${statusRatio(assignedCount, controls.length)}%;">
              <div class="vanta-donut-core"><div><strong>${statusRatio(assignedCount, controls.length)}%</strong><br><span class="vanta-subtle">Assigned</span></div></div>
            </div>
            <div class="vanta-legend">
              <span><span class="legend-dot gray"></span>Unassigned <strong style="float:right;">${controls.length - assignedCount}</strong></span>
              <span><span class="legend-dot"></span>Assigned <strong style="float:right;">${assignedCount}</strong></span>
              <span><span class="legend-dot red"></span>Needs reassignment <strong style="float:right;">0</strong></span>
            </div>
          </div>
        </div>
        <div class="vanta-card">
          <h2>Controls</h2>
          <div class="vanta-big-number">${statusRatio(readyCount, controls.length)}%</div>
          <p class="vanta-subtle">of controls have passing evidence</p>
          ${vantaProgress(statusRatio(readyCount, controls.length))}
          <div class="metric-footer" style="margin-top:10px;"><span>${readyCount} controls</span><span>${controls.length} total</span></div>
        </div>
      </div>
      ${vantaToolbar("Search controls", ["Frameworks", "Owner", "Domain", "Source", "Framework code", "Status"])}
      <div class="graph-list-layout ${selectedDetail ? "has-drawer" : ""}">
        ${renderTable(["", "ID", "Control", "Owner", "Frameworks", "Status", "Readiness", ""], rows)}
      </div>
      ${selectedDetail ? renderControlDrawer(selectedDetail) : ""}
    </div>
  `;
}

function renderGraphListTable(items, columns, objectType) {
  const rows = items.map((item) => {
    const metadata = item.metadata || {};
    const values = columns.map((column) => {
      if (column === "__open") {
        return `<td><button class="btn btn-outline" data-open-object="1" data-object-type="${escapeHtml(objectType)}" data-object-key="${escapeHtml(item.external_key)}">Open</button></td>`;
      }
      if (column === "title") return `<td style="font-weight:500;">${escapeHtml(item.title)}</td>`;
      if (column === "status") return `<td>${getStatusHtml(item.status || "draft")}</td>`;
      if (column === "owner") return `<td>${escapeHtml(item.owner || "-")}</td>`;
      if (column === "subtitle") return `<td>${escapeHtml(item.subtitle || "-")}</td>`;
      return `<td>${escapeHtml(metadata[column] ?? "-")}</td>`;
    });
    return `<tr>${values.join("")}</tr>`;
  });
  const headers = columns.map((column) => {
    if (column === "__open") return "";
    if (column === "title") return "Name";
    if (column === "status") return "Status";
    if (column === "owner") return "Owner";
    if (column === "subtitle") return "Subtitle";
    return column
      .replaceAll("_", " ")
      .replace(/\b\w/g, (match) => match.toUpperCase());
  });
  return renderTable(headers, rows);
}

async function renderPoliciesGraph() {
  const key = getSearchParam("policy");
  if (key) return renderGraphDetailPage("policy", key);
  const items = await getGraphList("policy");
  return `
    ${shell("Policies", "", routeButton("Add connection-rich policy", "compliance-policies"))}
    <div class="grid-3" style="margin-bottom:24px;">
      ${renderGraphMetric("Policies", items.length, "Graph-backed policy records")}
      ${renderGraphMetric("Approved", items.filter((item) => item.status === "approved").length, "Ready for audits")}
      ${renderGraphMetric("Need review", items.filter((item) => item.status !== "approved").length, "Requires owner attention")}
    </div>
    ${renderGraphListTable(items, ["title", "status", "owner", "subtitle", "__open"], "policy")}
  `;
}

async function renderDocumentsGraph() {
  const key = getSearchParam("document");
  if (key) return renderGraphDetailPage("document", key);
  const items = await getGraphList("document");
  return `
    ${shell("Documents", "", routeButton("Upload document", "evidence"))}
    <div class="grid-3" style="margin-bottom:24px;">
      ${renderGraphMetric("Documents", items.length, "Evidence and reference documents")}
      ${renderGraphMetric("Locked", items.filter((item) => item.status === "locked").length, "Immutable audit-ready artifacts")}
      ${renderGraphMetric("Attention", items.filter((item) => ["rejected", "stale", "pending"].includes(item.status)).length, "Requires follow-up")}
    </div>
    ${renderGraphListTable(items, ["title", "status", "subtitle", "collected_at", "__open"], "document")}
  `;
}

async function renderAuditsGraph() {
  const key = getSearchParam("audit");
  if (key) return renderGraphDetailPage("audit", key);
  const items = await getGraphList("audit");
  const workspace = await getJson("/workspaces/audits");
  const ready = Math.max(workspace.summary.controls_in_scope - workspace.summary.open_findings, 0);
  return `
    <div class="vanta-page">
      ${vantaHeader("Audits", "Active audit cycles and evidence readiness", `<button class="btn btn-outline">...</button> ${routeButton("Add audit", "new_audit_firm_selection")}`)}
      <div class="vanta-tabs">
        <button class="vanta-tab active">Active</button>
        <button class="vanta-tab">Completed</button>
      </div>
      ${vantaToolbar("Search", ["Audit firm", "Framework", "Status", "Audit type"])}
      ${
        items.length
          ? items.map((audit) => `
            <div class="vanta-card">
              <div class="vanta-card-head">
                <div class="vanta-title-row" style="justify-content:flex-start;">
                  <span class="vanta-mini-icon"><i class="fa-solid fa-shield-halved"></i></span>
                  <h2>${escapeHtml(audit.title)}</h2>
                  <span class="vanta-pill">${escapeHtml(audit.status || "in audit")}</span>
                  <span class="vanta-pill">${escapeHtml(audit.subtitle || "SOC 2")}</span>
                </div>
                <button class="btn btn-outline" data-open-object="1" data-object-type="audit" data-object-key="${escapeHtml(audit.external_key)}">Open audit</button>
              </div>
              <div class="grid-2" style="margin-top:18px;">
                <div class="surface-panel" style="margin:0;">
                  <h3>Timeline</h3>
                  <div class="vanta-timeline" style="margin-top:12px;">
                    ${vantaTask("fa-regular fa-eye", "Auditor gets access", "Mar 23, 2026")}
                    ${vantaTask("fa-solid fa-hourglass-start", "Audit starts", "Mar 23, 2026")}
                    ${vantaTask("fa-regular fa-circle-check", "Audit ends", "Jun 23, 2026")}
                  </div>
                </div>
                <div class="surface-panel" style="margin:0;">
                  <h3>Evidence tracker</h3>
                  <div class="vanta-progress segmented" style="margin-top:16px;">
                    <span class="red" style="width:${statusRatio(workspace.summary.open_findings, Math.max(workspace.summary.controls_in_scope, 1))}%"></span>
                    <span class="blue" style="width:${statusRatio(ready, Math.max(workspace.summary.controls_in_scope, 1))}%"></span>
                    <span class="gray" style="width:8%"></span>
                  </div>
                  <div class="audit-readiness-legend">
                    <span><strong>${workspace.summary.open_findings}</strong> Not ready for audit</span>
                    <span><strong>${ready}</strong> Ready for audit</span>
                    <span><strong>${workspace.summary.evidence_items}</strong> Evidence items</span>
                  </div>
                </div>
              </div>
            </div>
          `).join("")
          : `<div class="vanta-card"><p class="vanta-subtle">No audit records exist yet. Start one to open the full workspace view.</p></div>`
      }
    </div>
  `;
}

async function renderRisksGraph() {
  const key = getSearchParam("risk");
  if (key) return renderGraphDetailPage("risk", key);
  const items = await getGraphList("risk");
  return `
    ${shell("Risk scenarios", "", routeButton("Open risk library", "risk-library"))}
    <div class="grid-3" style="margin-bottom:24px;">
      ${renderGraphMetric("Open risks", items.length, "Connected risk scenarios")}
      ${renderGraphMetric("High severity", items.filter((item) => ((item.metadata || {}).severity || "") === "high").length, "Needs priority mitigation")}
      ${renderGraphMetric("Approved", items.filter((item) => item.status === "approved").length, "Reviewed scenarios")}
    </div>
    ${renderGraphListTable(items, ["subtitle", "title", "owner", "severity", "status", "__open"], "risk")}
  `;
}

async function renderVendorsGraph() {
  const key = getSearchParam("vendor");
  if (key) return renderGraphDetailPage("vendor", key);
  const items = await getGraphList("vendor");
  return `
    ${shell("Vendors", "", routeButton("Open integrations", "integrations", {}, "outline"))}
    <div class="grid-3" style="margin-bottom:24px;">
      ${renderGraphMetric("Vendors", items.length, "Third-party records")}
      ${renderGraphMetric("Active", items.filter((item) => item.status === "active").length, "Operational vendors")}
      ${renderGraphMetric("Need review", items.filter((item) => item.status !== "active").length, "Relationship follow-up")}
    </div>
    ${renderGraphListTable(items, ["title", "status", "category", "inherent_risk", "security_review_status", "__open"], "vendor")}
  `;
}

async function renderTestsGraph() {
  const key = getSearchParam("test");
  if (key) return renderGraphDetailPage("test", key);
  const items = await getGraphList("test");
  const passing = items.filter((item) => isPositiveStatus(item.status)).length;
  const attention = items.length - passing;
  return `
    <div class="vanta-page wide">
      ${vantaHeader("Tests", "Automated and document-based compliance tests", '<button class="btn btn-outline">...</button>')}
      <div class="vanta-kpi-grid" style="margin-bottom:14px;">
        <div class="vanta-card">
          <div class="vanta-card-head">
            <h2>Tests passing</h2>
            <span class="vanta-pill">${passing}</span>
          </div>
          <div class="vanta-big-number">${statusRatio(passing, items.length)}%</div>
          <p class="vanta-subtle">${passing} of ${items.length} passing</p>
          ${vantaProgress(statusRatio(passing, items.length))}
          <div class="vanta-monitor-grid two" style="margin-top:18px;">
            <div>
              <p class="vanta-subtle">Automated tests</p>
              ${vantaProgress(statusRatio(passing, items.length))}
            </div>
            <div>
              <p class="vanta-subtle">Documents</p>
              ${vantaProgress(statusRatio(Math.max(passing - 1, 0), items.length))}
            </div>
          </div>
        </div>
        <div class="vanta-card">
          <div class="vanta-card-head">
            <h2>Tests that need attention</h2>
            <span class="vanta-pill">${attention}</span>
          </div>
          <div class="vanta-task-list" style="margin-top:14px;">
            ${vantaTask("fa-regular fa-calendar-xmark", "Overdue", attention)}
            ${vantaTask("fa-solid fa-diamond", "Needs remediation", Math.ceil(attention / 4))}
            ${vantaTask("fa-regular fa-clock", "Due soon", Math.ceil(attention / 3))}
          </div>
        </div>
      </div>
      ${vantaToolbar("Search", ["Category", "Framework", "Control", "Integration", "Owner", "Type", "Status", "Rollout"])}
      ${renderGraphListTable(items, ["title", "owner", "status", "integration_name", "subtitle", "__open"], "test")}
    </div>
  `;
}

async function renderIntegrationsGraph() {
  const key = getSearchParam("integration");
  if (key) return renderGraphDetailPage("integration", key);
  return renderIntegrations();
}

PAGE_RENDERERS.tests = renderTestsGraph;
PAGE_RENDERERS["compliance-controls"] = renderControlsGraph;
PAGE_RENDERERS["compliance-policies"] = renderPoliciesGraph;
PAGE_RENDERERS["compliance-documents"] = renderDocumentsGraph;
PAGE_RENDERERS["compliance-audits"] = renderAuditsGraph;
PAGE_RENDERERS["risk-risks"] = renderRisksGraph;
PAGE_RENDERERS.vendors = renderVendorsGraph;
PAGE_RENDERERS.integrations = renderIntegrationsGraph;

async function setupActions() {
  document.querySelectorAll("[data-route-target]").forEach((element) => {
    if (element.dataset.boundClick === "1") return;
    element.dataset.boundClick = "1";
    element.addEventListener("click", (event) => {
      event.preventDefault();
      const route = element.dataset.routeTarget;
      const params = getDatasetParams(element);
      navigateTo(route, params);
    });
  });

  const syncBtn = document.getElementById("sync-btn");
  if (syncBtn) {
    const status = document.getElementById("sync-status");
    syncBtn.addEventListener("click", async () => {
      if (status) status.textContent = "Running sync...";
      try {
        const res = await getJson("/integrations/sync", { method: "POST" });
        const okCount = res.results.filter((r) => r.status === "ok").length;
        if (status) status.textContent = `Sync complete. ${okCount}/${res.results.length} returned data.`;
      } catch (error) {
        if (status) status.textContent = `Sync failed: ${error.message}`;
      }
    });
  }

  const provisionBtn = document.getElementById("provision-btn");
  if (provisionBtn) {
    const resultEl = document.getElementById("provision-result");
    provisionBtn.addEventListener("click", async () => {
      provisionBtn.disabled = true;
      provisionBtn.textContent = "Building…";
      if (resultEl) resultEl.innerHTML = `<p class="status-gray" style="font-size:0.875rem;">Creating folders on SharePoint…</p>`;
      try {
        const res = await getJson("/sharepoint/provision-folders", { method: "POST" });
        const lines = [];
        if (res.created.length) lines.push(`<span class="status-green">✓ Created (${res.created.length}):</span> ${res.created.map(escapeHtml).join(", ")}`);
        if (res.skipped.length) lines.push(`<span class="status-gray">↩ Already existed (${res.skipped.length}):</span> ${res.skipped.map(escapeHtml).join(", ")}`);
        if (res.errors.length)  lines.push(`<span class="status-red">✗ Errors (${res.errors.length}):</span> ${res.errors.map(escapeHtml).join(", ")}`);
        if (resultEl) resultEl.innerHTML = lines.map((l) => `<p style="font-size:0.85rem;margin-top:6px;">${l}</p>`).join("");
      } catch (err) {
        if (resultEl) resultEl.innerHTML = `<p class="status-red" style="font-size:0.875rem;">Failed: ${escapeHtml(err.message)}</p>`;
      } finally {
        provisionBtn.disabled = false;
        provisionBtn.innerHTML = '<i class="fa-solid fa-folder-plus" style="margin-right:6px;"></i>Build Folder Structure';
      }
    });
  }

  const spBrowseBtn = document.getElementById("sp-browse-btn");
  if (spBrowseBtn) {
    spBrowseBtn.addEventListener("click", async () => {
      const folder = document.getElementById("sp-folder")?.value.trim() ?? "";
      const listEl = document.getElementById("sp-file-list");
      if (listEl) listEl.textContent = "Loading…";
      try {
        const files = await getJson(`/sharepoint/browse${folder ? `?folder=${encodeURIComponent(folder)}` : ""}`);
        if (!files.length) {
          listEl.textContent = "No files found.";
          return;
        }
        listEl.innerHTML = files
          .map(
            (f) =>
              `<div style="display:flex; align-items:center; justify-content:space-between; padding:8px 0; border-bottom:1px solid #F0F0F0;">
                <span>
                  <i class="fa-solid ${f.is_folder ? "fa-folder" : "fa-file"}" style="color:var(--accent-gold); margin-right:8px;"></i>
                  <a href="${escapeHtml(f.web_url)}" target="_blank" rel="noopener" style="color:var(--text-primary);">${escapeHtml(f.name)}</a>
                </span>
                ${f.is_folder ? "" : `<button class="btn btn-outline sp-attach-btn" style="padding:4px 10px; font-size:0.8rem;" data-id="${escapeHtml(f.id)}" data-name="${escapeHtml(f.name)}">Attach as evidence</button>`}
              </div>`
          )
          .join("");
        listEl.querySelectorAll(".sp-attach-btn").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const controlId = prompt("Enter Control DB ID to attach this file to:");
            if (!controlId) return;
            try {
              await getJson("/sharepoint/attach", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ control_id: parseInt(controlId, 10), item_id: btn.dataset.id, name: btn.dataset.name }),
              });
              btn.textContent = "Attached ✓";
              btn.disabled = true;
            } catch (err) {
              alert(`Failed to attach: ${err.message}`);
            }
          });
        });
      } catch (err) {
        if (listEl) listEl.textContent = `Error: ${err.message}`;
      }
    });
  }

  document.querySelectorAll("[data-open-object]").forEach((element) => {
    if (element.dataset.boundGraphOpen === "1") return;
    element.dataset.boundGraphOpen = "1";
    element.addEventListener("click", (event) => {
      event.preventDefault();
      openGraphObject(element.dataset.objectType, element.dataset.objectKey);
    });
  });

  document.querySelectorAll(".relationship-add").forEach((element) => {
    if (element.dataset.boundRelationshipAdd === "1") return;
    element.dataset.boundRelationshipAdd = "1";
    element.addEventListener("click", async () => {
      try {
        await openRelationshipModal(element.dataset.sourceType, element.dataset.sourceKey);
      } catch (error) {
        alert(`Unable to open relationship picker: ${error.message}`);
      }
    });
  });

  document.querySelectorAll("[data-close-relationship]").forEach((element) => {
    if (element.dataset.boundRelationshipClose === "1") return;
    element.dataset.boundRelationshipClose = "1";
    element.addEventListener("click", () => {
      closeRelationshipModal();
      renderCurrentPage();
    });
  });

  const relationshipTypeFilter = document.getElementById("relationship-type-filter");
  if (relationshipTypeFilter && relationshipTypeFilter.dataset.boundChange !== "1") {
    relationshipTypeFilter.dataset.boundChange = "1";
    relationshipTypeFilter.addEventListener("change", (event) => {
      setRelationshipTypeFilter(event.target.value);
    });
  }

  const relationshipSearch = document.getElementById("relationship-search");
  if (relationshipSearch && relationshipSearch.dataset.boundInput !== "1") {
    relationshipSearch.dataset.boundInput = "1";
    relationshipSearch.addEventListener("input", (event) => {
      setRelationshipSearch(event.target.value);
    });
  }

  document.querySelectorAll("[data-relationship-option]").forEach((element) => {
    if (element.dataset.boundRelationshipPick === "1") return;
    element.dataset.boundRelationshipPick = "1";
    element.addEventListener("click", () => {
      selectRelationshipTarget(element.dataset.targetType, element.dataset.targetKey);
    });
  });

  const relationshipSubmit = document.getElementById("relationship-submit");
  if (relationshipSubmit && relationshipSubmit.dataset.boundSubmit !== "1") {
    relationshipSubmit.dataset.boundSubmit = "1";
    relationshipSubmit.addEventListener("click", async () => {
      try {
        await getJson("/graph/relationships", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_type: _relationshipModal.sourceType,
            source_key: _relationshipModal.sourceKey,
            target_type: _relationshipModal.selectedType,
            target_key: _relationshipModal.selectedKey,
          }),
        });
        closeRelationshipModal();
        renderCurrentPage();
      } catch (error) {
        alert(`Unable to create relationship: ${error.message}`);
      }
    });
  }

  document.querySelectorAll(".relationship-remove").forEach((element) => {
    if (element.dataset.boundRelationshipRemove === "1") return;
    element.dataset.boundRelationshipRemove = "1";
    element.addEventListener("click", async () => {
      if (!confirm("Remove this connection?")) return;
      try {
        await fetch(`/graph/relationships/${encodeURIComponent(element.dataset.relationshipId)}`, { method: "DELETE" });
        renderCurrentPage();
      } catch (error) {
        alert(`Unable to remove relationship: ${error.message}`);
      }
    });
  });

  const auditAuditorForm = document.getElementById("audit-auditor-form");
  if (auditAuditorForm && auditAuditorForm.dataset.boundSubmit !== "1") {
    auditAuditorForm.dataset.boundSubmit = "1";
    const output = document.getElementById("audit-auditor-status");
    auditAuditorForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (output) output.textContent = "Assigning auditor...";
      const formData = new FormData(auditAuditorForm);
      const expiresAt = formData.get("access_expires_at");
      const payload = {
        user_id: Number(formData.get("user_id")),
        access_expires_at: expiresAt ? `${expiresAt}T23:59:59Z` : null,
      };
      try {
        await getJson(`/api/v1/audits/${auditAuditorForm.dataset.auditId}/auditors`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (output) output.textContent = "Auditor assigned.";
        renderCurrentPage();
      } catch (error) {
        if (output) output.textContent = `Assign failed: ${error.message}`;
      }
    });
  }

  document.querySelectorAll(".audit-revoke-btn").forEach((button) => {
    if (button.dataset.boundClick === "1") return;
    button.dataset.boundClick = "1";
    button.addEventListener("click", async () => {
      if (!confirm("Revoke this auditor's access to the audit?")) return;
      try {
        const response = await fetch(`/api/v1/audits/${button.dataset.auditId}/auditors/${button.dataset.userId}`, {
          method: "DELETE",
        });
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        renderCurrentPage();
      } catch (error) {
        alert(`Revoke failed: ${error.message}`);
      }
    });
  });

  document.querySelectorAll(".audit-preview-btn").forEach((button) => {
    if (button.dataset.boundClick === "1") return;
    button.dataset.boundClick = "1";
    button.addEventListener("click", async () => {
      const output = document.getElementById("audit-preview-result");
      if (!output) return;
      output.style.display = "block";
      output.innerHTML = `<p class="status-gray">Loading auditor preview...</p>`;
      try {
        const preview = await getJson(`/api/v1/audits/${button.dataset.auditId}/preview-as-auditor`);
        output.innerHTML = `
          <h3 class="serif-text section-title">Auditor preview</h3>
          <div class="grid-3">
            ${renderAuditorMetric("Controls", (preview.controls || []).length, "Visible to auditor")}
            ${renderAuditorMetric("Evidence", (preview.evidence || []).length, "Shared artifacts")}
            ${renderAuditorMetric("Requests", (preview.requests || []).length, "Non-internal comments only")}
          </div>
        `;
      } catch (error) {
        output.innerHTML = `<p class="status-red">Preview failed: ${escapeHtml(error.message)}</p>`;
      }
    });
  });

  const auditorRequestForm = document.getElementById("auditor-request-form");
  if (auditorRequestForm && auditorRequestForm.dataset.boundSubmit !== "1") {
    auditorRequestForm.dataset.boundSubmit = "1";
    const output = document.getElementById("auditor-request-status");
    auditorRequestForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (output) output.textContent = "Creating request...";
      const formData = new FormData(auditorRequestForm);
      const payload = {
        title: formData.get("title"),
        description: formData.get("description") || null,
        control_id: formData.get("control_id") ? Number(formData.get("control_id")) : null,
        due_date: formData.get("due_date") ? `${formData.get("due_date")}T00:00:00Z` : null,
      };
      try {
        await getJson(`/api/v1/audits/${auditorRequestForm.dataset.auditId}/requests`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (output) output.textContent = "Request created.";
        renderCurrentPage();
      } catch (error) {
        if (output) output.textContent = `Request failed: ${error.message}`;
      }
    });
  }

  document.querySelectorAll(".auditor-comment-form").forEach((form) => {
    if (form.dataset.boundSubmit === "1") return;
    form.dataset.boundSubmit = "1";
    const output = form.parentElement?.querySelector(".auditor-form-status");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (output) output.textContent = "Sending comment...";
      const formData = new FormData(form);
      try {
        await getJson(`/api/v1/requests/${form.dataset.requestId}/comments`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ body: formData.get("body"), is_internal: false }),
        });
        if (output) output.textContent = "Comment added.";
        renderCurrentPage();
      } catch (error) {
        if (output) output.textContent = `Comment failed: ${error.message}`;
      }
    });
  });

  document.querySelectorAll(".auditor-status-form").forEach((form) => {
    if (form.dataset.boundSubmit === "1") return;
    form.dataset.boundSubmit = "1";
    const output = form.parentElement?.querySelector(".auditor-form-status");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (output) output.textContent = "Updating request...";
      const formData = new FormData(form);
      try {
        await getJson(`/api/v1/requests/${form.dataset.requestId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: formData.get("status") }),
        });
        if (output) output.textContent = "Request updated.";
        renderCurrentPage();
      } catch (error) {
        if (output) output.textContent = `Update failed: ${error.message}`;
      }
    });
  });

  document.querySelectorAll(".auditor-attach-form").forEach((form) => {
    if (form.dataset.boundSubmit === "1") return;
    form.dataset.boundSubmit = "1";
    const output = form.parentElement?.querySelector(".auditor-form-status");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (output) output.textContent = "Attaching evidence...";
      const formData = new FormData(form);
      try {
        await getJson(`/api/v1/requests/${form.dataset.requestId}/evidence`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ evidence_id: Number(formData.get("evidence_id")) }),
        });
        if (output) output.textContent = "Evidence attached.";
        renderCurrentPage();
      } catch (error) {
        if (output) output.textContent = `Attach failed: ${error.message}`;
      }
    });
  });

  const uploadForm = document.getElementById("upload-form");
  if (uploadForm) {
    const presetControlId = getSearchParam("control_id");
    if (presetControlId) {
      const controlIdInput = uploadForm.querySelector('[name="control_id"]');
      if (controlIdInput) controlIdInput.value = presetControlId;
    }
    const output = document.getElementById("upload-status");
    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (output) output.textContent = "Uploading evidence...";
      try {
        const formData = new FormData(uploadForm);
        const res = await getJson("/evidence/upload", { method: "POST", body: formData });
        if (output) output.textContent = `Uploaded evidence #${res.id}`;
        setRouteSearchParam("control_id", res.control_id);
        setRouteSearchParam("evidence", res.id);
        renderCurrentPage();
      } catch (error) {
        if (output) output.textContent = `Upload failed: ${error.message}`;
      }
    });
  }

  const statusForm = document.getElementById("control-status-form");
  if (statusForm) {
    const result = document.getElementById("control-status-result");
    statusForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const controlId = statusForm.dataset.controlId;
      const status = document.getElementById("control-status")?.value;
      if (result) result.textContent = "Saving status...";
      try {
        await getJson(`/controls/${controlId}/status`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ implementation_status: status }),
        });
        if (result) result.textContent = "Status updated.";
        renderCurrentPage();
      } catch (error) {
        if (result) result.textContent = `Update failed: ${error.message}`;
      }
    });
  }
}

async function renderCurrentPage() {
  const route = getRoute();
  setActiveNav(route);
  const root = document.getElementById("page-root");

  try {
    root.innerHTML = `${await PAGE_RENDERERS[route]()}${renderRelationshipModal()}`;
  } catch (error) {
    root.innerHTML = `
      ${shell("Screen Error", "Unable to load this screen")}
      <div class="card"><p class="status-red">${escapeHtml(error.message)}</p></div>
    `;
  }

  await setupActions();
}

async function boot() {
  let currentUser = null;
  try {
    currentUser = await getJson("/auth/me");
    window._currentUser = currentUser;
  } catch {
    document.getElementById("login-wall").style.display = "flex";
    document.querySelector(".app-shell").style.display = "none";
    return;
  }

  const nameEl = document.getElementById("sidebar-user-name");
  if (nameEl && currentUser) {
    nameEl.textContent = currentUser.name || currentUser.email;
  }

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      window.localStorage.removeItem("auditorToken");
      await fetch("/auth/logout", { method: "POST" });
      window.location.reload();
    });
  }

  setupNavGroups();

  if (!window.location.hash || !ROUTES.has(window.location.hash.replace("#", ""))) {
    window.location.hash = currentUser.role === "auditor" ? "#auditor-portal" : "#home";
  }
  window.addEventListener("hashchange", renderCurrentPage);
  window.addEventListener("popstate", renderCurrentPage);
  renderCurrentPage();
}

boot();

async (page) => {
  const controls = [
    {
      id: 1,
      control_id: "AST-1",
      title: "Asset disposal procedures utilized",
      description: "The company has electronic media containing confidential information purged or destroyed in accordance with best practices.",
      owner: "Nnaemeka Ugwokegbe",
      status: "implemented",
    },
    {
      id: 2,
      control_id: "AST-2",
      title: "Data retention procedures established",
      description: "Formal retention and disposal procedures guide secure handling of company and customer data.",
      owner: "Nnaemeka Ugwokegbe",
      status: "implemented",
    },
    {
      id: 3,
      control_id: "BCD-1",
      title: "Business continuity plans established",
      description: "Continuity plans outline communication and recovery responsibilities during service interruptions.",
      owner: "Compliance Team",
      status: "attention",
    },
  ];
  const graphControls = controls.map((control, index) => ({
    object_type: "control",
    external_key: control.control_id,
    title: control.title,
    subtitle: control.control_id,
    description: control.description,
    owner: control.owner,
    status: control.status,
    metadata: {
      control_id: control.control_id,
      type1_ready: index < 2,
      type2_ready: index < 2,
      domain: index < 2 ? "Asset Management" : "Business Continuity",
      next_review_at: "2026-06-23",
    },
  }));
  const tests = [
    {
      object_type: "test",
      external_key: "TST-1",
      title: "Sample of remediated vulnerabilities",
      subtitle: "Engineering / Document",
      description: "Provide evidence of remediated high severity vulnerabilities.",
      owner: "Security Team",
      status: "overdue",
      metadata: { integration_name: "Document", sla_days: 30 },
    },
    {
      object_type: "test",
      external_key: "TST-2",
      title: "Password manager records tracked",
      subtitle: "Information technology / Automated",
      owner: "IT Team",
      status: "passing",
      metadata: { integration_name: "Microsoft Endpoint Manager", sla_days: 7 },
    },
  ];
  const audit = {
    object_type: "audit",
    external_key: "1",
    title: "Audit: SOC 2 Type II",
    subtitle: "SOC 2 Type II",
    description: "External audit workspace for SOC 2 Type II.",
    owner: "Prescient Assurance",
    status: "in audit",
    metadata: { audit_type: "External", firm_name: "Prescient Assurance", audit_period_id: "2026-Q2" },
    workspace: {
      summary: { controls_in_scope: 124, evidence_items: 94, open_findings: 22 },
      controls: controls.map((control, index) => ({
        control_id: control.control_id,
        title: control.title,
        audit_state: index < 2 ? "ready" : "not_ready",
        latest_evidence_status: index < 2 ? "ready" : "missing",
        issue: index < 2 ? "" : "Needs updated evidence",
      })),
      auditors: [
        {
          user_id: 7,
          name: "Nina Clark",
          email: "auditor@example.com",
          access_expires_at: "2026-06-23",
          scoped_token: "preview-token",
        },
      ],
    },
  };
  const evidence = [
    {
      id: 1,
      control_id: 1,
      control_ref: "AST-1",
      title: "Proof of media/device disposal",
      name: "Proof of media/device disposal",
      status: "ready",
      source_type: "manual",
      valid_from: "2026-04-15",
      file_name: "asset-disposal.pdf",
      description: "JEC-approved disposal certificate sample.",
    },
    {
      id: 2,
      control_id: 2,
      control_ref: "AST-2",
      title: "Retention policy approval",
      name: "Retention policy approval",
      status: "pending",
      source_type: "sharepoint",
      valid_from: "2026-04-10",
      file_name: "retention-policy.docx",
      description: "Policy owner review pending.",
    },
  ];
  const auditWorkspace = {
    audit: { id: 1, audit_firm: "Jean Edwards, SOC 2 Type II", framework: "SOC 2" },
    period: { name: "March 23, 2026 - June 23, 2026" },
    controls: controls.map((control, index) => ({
      control_id: control.id,
      control_ref: control.control_id,
      title: control.title,
      owner: control.owner,
      evidence_status: index < 2 ? "ready" : "missing",
      auditor_notes: index < 2 ? "Ready for audit" : "Needs update",
    })),
    evidence,
    requests: [
      {
        id: 12,
        title: "Upload updated vulnerability sample",
        description: "Auditor needs the latest remediation record.",
        status: "open",
        control_id: 1,
        due_date: "2026-04-24",
        evidence: [],
        comments: [{ body: "Please include the scan date.", is_internal: false, created_at: "2026-04-16" }],
      },
    ],
    findings: [{ title: "Evidence renewal overdue", severity: "medium", status: "open" }],
  };
  const fixtures = [
    ["**/auth/me", { id: 1, email: "designer@jec.local", name: "Nnaemeka Ugwokegbe", role: "compliance_manager" }],
    ["**/dashboard/overview", { soc2_progress_percent: 68, controls_passing: 54, controls_total: 80, policies_ok: 15, policies_total: 15, tests_ok: 45, tests_total: 57, vendors_ok: 5, vendors_total: 5 }],
    ["**/dashboard/gaps", [{ title: "Renew vulnerability sample" }, { title: "Confirm owners" }]],
    ["**/integrations/status", [{ configured: true }, { configured: false }]],
    ["**/integrations/runs", []],
    ["**/sharepoint/status", { ok: false }],
    ["**/controls", controls],
    ["**/evidence", evidence],
    ["**/graph/control", { items: graphControls }],
    ["**/graph/control/AST-1", { ...graphControls[0], evidence, mapped_elements: [{ section: "Tests", items: tests.slice(0, 1) }, { section: "Documents", items: [{ object_type: "document", external_key: "DOC-1", title: "Asset Management Policy", status: "approved" }] }] }],
    ["**/graph/test", { items: tests }],
    ["**/graph/test/TST-1", { ...tests[0], mapped_elements: [{ section: "Controls", items: graphControls.slice(0, 2) }] }],
    ["**/graph/audit", { items: [audit] }],
    ["**/graph/audit/1", { ...audit, mapped_elements: [{ section: "Controls", items: graphControls }, { section: "Evidence", items: evidence.map((item) => ({ object_type: "document", external_key: String(item.id), title: item.title, status: item.status })) }] }],
    ["**/workspaces/audits", { summary: { controls_in_scope: 124, evidence_items: 94, open_findings: 22 } }],
    ["**/api/v1/auditors", [{ id: 9, name: "Auditor User", email: "auditor@example.com" }]],
    ["**/api/v1/audits", [{ id: 1, audit_firm: "Prescient Assurance", framework: "SOC 2" }]],
    ["**/api/v1/audits/1", auditWorkspace],
    ["**/api/v1/audits/1/readiness/type2", { overall_score: 78, controls_ready: 94 }],
  ];
  await page.context().unroute("**/*").catch(() => {});
  for (const [pattern, body] of fixtures) {
    await page.context().route(pattern, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) }),
    );
  }
}

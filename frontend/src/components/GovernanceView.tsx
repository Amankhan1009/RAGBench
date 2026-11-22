"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  WorkspaceMember,
  AuditLogItem,
  AuditVerificationReport,
  AuditStats,
  fetchWorkspaceMembers,
  addWorkspaceMember,
  updateWorkspaceMemberRole,
  removeWorkspaceMember,
  fetchAuditLogs,
  verifyAuditIntegrity,
  fetchAuditStats,
  User,
} from "../lib/api";

interface GovernanceViewProps {
  showToast: (message: string, type: "loading" | "success" | "error") => void;
  currentUser?: User | null;
}

export default function GovernanceView({ showToast, currentUser }: GovernanceViewProps) {
  // Members state
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("evaluator");
  const [invitePassword, setInvitePassword] = useState("");
  const [inviting, setInviting] = useState(false);

  // Audit state
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [auditStats, setAuditStats] = useState<AuditStats | null>(null);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [filterAction, setFilterAction] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  // Verification state
  const [verifying, setVerifying] = useState(false);
  const [verificationReport, setVerificationReport] = useState<AuditVerificationReport | null>(null);

  // Active view section tab
  const [section, setSection] = useState<"members" | "audit">("members");

  const loadMembers = useCallback(async () => {
    setLoadingMembers(true);
    try {
      const data = await fetchWorkspaceMembers();
      setMembers(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load team members", "error");
    } finally {
      setLoadingMembers(false);
    }
  }, [showToast]);

  const loadAuditData = useCallback(async () => {
    setLoadingLogs(true);
    try {
      const [logsRes, statsRes] = await Promise.all([
        fetchAuditLogs({
          action: filterAction === "ALL" ? undefined : filterAction,
          user_email: searchQuery ? searchQuery : undefined,
          limit: 100,
        }),
        fetchAuditStats().catch(() => null),
      ]);
      setAuditLogs(logsRes.items);
      if (statsRes) setAuditStats(statsRes);
    } catch (err: any) {
      showToast(err.message || "Failed to load audit logs", "error");
    } finally {
      setLoadingLogs(false);
    }
  }, [filterAction, searchQuery, showToast]);

  useEffect(() => {
    loadMembers();
    loadAuditData();
  }, [loadMembers, loadAuditData]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) {
      showToast("Email address is required", "error");
      return;
    }
    setInviting(true);
    try {
      await addWorkspaceMember({
        email: inviteEmail.trim(),
        name: inviteName.trim() || undefined,
        role: inviteRole,
        password: invitePassword.trim() || undefined,
      });
      showToast(`Invited ${inviteEmail} as ${inviteRole.toUpperCase()}`, "success");
      setShowInviteModal(false);
      setInviteEmail("");
      setInviteName("");
      setInvitePassword("");
      await loadMembers();
      await loadAuditData();
    } catch (err: any) {
      showToast(err.message || "Failed to invite member", "error");
    } finally {
      setInviting(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await updateWorkspaceMemberRole(userId, newRole);
      showToast(`Updated role to ${newRole.toUpperCase()}`, "success");
      await loadMembers();
      await loadAuditData();
    } catch (err: any) {
      showToast(err.message || "Failed to update role", "error");
    }
  };

  const handleRemoveMember = async (userId: string, memberEmail: string) => {
    if (!confirm(`Are you sure you want to remove ${memberEmail} from this workspace?`)) {
      return;
    }
    try {
      await removeWorkspaceMember(userId);
      showToast(`Removed ${memberEmail} from workspace`, "success");
      await loadMembers();
      await loadAuditData();
    } catch (err: any) {
      showToast(err.message || "Failed to remove member", "error");
    }
  };

  const handleVerifyIntegrity = async () => {
    setVerifying(true);
    try {
      const report = await verifyAuditIntegrity();
      setVerificationReport(report);
      if (report.is_valid) {
        showToast("Audit chain verified: 0 tampered records detected (SECURE)", "success");
      } else {
        showToast(`CRITICAL: ${report.tampered_records.length} tampered records found!`, "error");
      }
    } catch (err: any) {
      showToast(err.message || "Failed to verify audit integrity", "error");
    } finally {
      setVerifying(false);
    }
  };

  const exportAuditLogsJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(auditLogs, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `ragbench_audit_trail_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Metrics
  const adminCount = members.filter((m) => m.role?.toLowerCase() === "admin").length;
  const evaluatorCount = members.filter((m) => m.role?.toLowerCase() === "evaluator").length;
  const viewerCount = members.filter((m) => m.role?.toLowerCase() === "viewer").length;

  const getActionBadgeColor = (action: string) => {
    if (action.includes("CREATED") || action.includes("REGISTERED") || action.includes("SET")) {
      return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
    }
    if (action.includes("DELETED") || action.includes("REMOVED")) {
      return "bg-rose-500/20 text-rose-300 border-rose-500/30";
    }
    if (action.includes("UPDATED") || action.includes("ROLE")) {
      return "bg-amber-500/20 text-amber-300 border-amber-500/30";
    }
    if (action.includes("BENCHMARK") || action.includes("REDTEAM")) {
      return "bg-purple-500/20 text-purple-300 border-purple-500/30";
    }
    return "bg-cyan-500/20 text-cyan-300 border-cyan-500/30";
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-3xl">🏛️</span>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Enterprise RBAC &amp; Tamper-Evident Audit Logging
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                v3.5 Enterprise
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-400 max-w-2xl leading-relaxed">
              Institutional governance with Role-Based Access Control (Admin, Evaluator, Viewer) and cryptographically chained SHA-256 HMAC audit logging for SOC2, HIPAA, and compliance verification.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleVerifyIntegrity}
              disabled={verifying}
              className="px-4 py-2.5 rounded-xl font-medium text-xs tracking-wide uppercase transition flex items-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-950/50 disabled:opacity-50"
            >
              {verifying ? (
                <>
                  <svg className="animate-spin w-4 h-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>Verifying Chain...</span>
                </>
              ) : (
                <>
                  <span>🛡️</span>
                  <span>Verify Audit Integrity</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Sub-navigation tabs */}
        <div className="mt-6 flex border-b border-slate-800 gap-6">
          <button
            onClick={() => setSection("members")}
            className={`pb-3 text-sm font-semibold transition flex items-center gap-2 ${
              section === "members"
                ? "text-indigo-400 border-b-2 border-indigo-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span>👥</span>
            <span>Workspace Team &amp; RBAC</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
              {members.length}
            </span>
          </button>

          <button
            onClick={() => setSection("audit")}
            className={`pb-3 text-sm font-semibold transition flex items-center gap-2 ${
              section === "audit"
                ? "text-indigo-400 border-b-2 border-indigo-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span>📜</span>
            <span>Tamper-Evident Audit Trail</span>
            {auditStats && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                {auditStats.total_events}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* SECTION 1: WORKSPACE TEAM & RBAC */}
      {section === "members" && (
        <div className="space-y-6">
          {/* Metrics summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Total Members</span>
              <p className="text-2xl font-bold text-white mt-1">{members.length}</p>
            </div>
            <div className="bg-slate-900/80 border border-purple-500/20 rounded-xl p-4">
              <span className="text-xs text-purple-300 font-medium uppercase tracking-wider">Admins</span>
              <p className="text-2xl font-bold text-purple-400 mt-1">{adminCount}</p>
              <span className="text-[10px] text-slate-400">Full platform control</span>
            </div>
            <div className="bg-slate-900/80 border border-blue-500/20 rounded-xl p-4">
              <span className="text-xs text-blue-300 font-medium uppercase tracking-wider">Evaluators</span>
              <p className="text-2xl font-bold text-blue-400 mt-1">{evaluatorCount}</p>
              <span className="text-[10px] text-slate-400">Datasets, runs &amp; rails</span>
            </div>
            <div className="bg-slate-900/80 border border-slate-700 rounded-xl p-4">
              <span className="text-xs text-slate-300 font-medium uppercase tracking-wider">Viewers / Auditors</span>
              <p className="text-2xl font-bold text-slate-300 mt-1">{viewerCount}</p>
              <span className="text-[10px] text-slate-400">Read-only audit access</span>
            </div>
          </div>

          {/* Members Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-semibold text-white">Active Workspace Members</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Manage member privileges, roles, and administrative security boundaries.
                </p>
              </div>

              <button
                onClick={() => setShowInviteModal(true)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center gap-2 self-start sm:self-auto"
              >
                <span>➕</span>
                <span>Invite Member</span>
              </button>
            </div>

            {loadingMembers ? (
              <div className="p-12 text-center text-slate-400 text-sm">
                <svg className="animate-spin w-6 h-6 mx-auto mb-2 text-indigo-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading team members...
              </div>
            ) : members.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-sm">
                No team members found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/70 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                    <tr>
                      <th className="py-3.5 px-4">Member</th>
                      <th className="py-3.5 px-4">Role</th>
                      <th className="py-3.5 px-4">Joined</th>
                      <th className="py-3.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium">
                    {members.map((m) => {
                      const isCurrent = currentUser?.id === m.id;
                      const role = m.role?.toLowerCase() || "admin";
                      return (
                        <tr key={m.id} className="hover:bg-slate-800/30 transition">
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white font-bold text-xs uppercase shadow-inner">
                                {m.name ? m.name.charAt(0) : m.email.charAt(0)}
                              </div>
                              <div>
                                <div className="text-slate-200 font-semibold flex items-center gap-2">
                                  <span>{m.name || "Anonymous Member"}</span>
                                  {isCurrent && (
                                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                      You
                                    </span>
                                  )}
                                </div>
                                <div className="text-slate-400 text-[11px] font-mono">{m.email}</div>
                              </div>
                            </div>
                          </td>

                          <td className="py-3.5 px-4">
                            {role === "admin" && (
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                <span>🛡️</span>
                                <span>Admin</span>
                              </span>
                            )}
                            {role === "evaluator" && (
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                                <span>⚙️</span>
                                <span>Evaluator</span>
                              </span>
                            )}
                            {role === "viewer" && (
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-slate-500/20 text-slate-300 border border-slate-500/30">
                                <span>👁️</span>
                                <span>Viewer</span>
                              </span>
                            )}
                          </td>

                          <td className="py-3.5 px-4 text-slate-400">
                            {m.created_at ? new Date(m.created_at).toLocaleDateString() : "—"}
                          </td>

                          <td className="py-3.5 px-4 text-right">
                            <div className="inline-flex items-center gap-2">
                              {/* Change role selector */}
                              <select
                                value={role}
                                onChange={(e) => handleRoleChange(m.id, e.target.value)}
                                className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-slate-300 text-xs outline-none focus:border-indigo-500"
                              >
                                <option value="admin">Admin</option>
                                <option value="evaluator">Evaluator</option>
                                <option value="viewer">Viewer</option>
                              </select>

                              {/* Remove button */}
                              {!isCurrent && (
                                <button
                                  onClick={() => handleRemoveMember(m.id, m.email)}
                                  className="text-slate-400 hover:text-rose-400 p-1.5 rounded transition"
                                  title="Remove member"
                                >
                                  🗑️
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* RBAC Permission Matrix Guide */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
            <h4 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
              <span>📋</span>
              <span>Enterprise Role Capability Matrix</span>
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2.5 px-3">Permission / Capability</th>
                    <th className="py-2.5 px-3 text-purple-300">Admin</th>
                    <th className="py-2.5 px-3 text-blue-300">Evaluator / Engineer</th>
                    <th className="py-2.5 px-3 text-slate-300">Viewer / Auditor</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 text-slate-300">
                  <tr>
                    <td className="py-2 px-3">View Dashboards, Analytics &amp; Reports</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Full</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Full</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Read-Only</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3">Create Datasets &amp; Run Benchmark Evaluations</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-rose-400">✕ Blocked (403)</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3">Set Production Baselines &amp; Update Guardrails</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-rose-400">✕ Blocked (403)</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3">Run AI Red-Teaming Adversarial Fuzzing</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-rose-400">✕ Blocked (403)</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3">Manage BYOK Provider API Keys</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-rose-400">✕ Blocked (403)</td>
                    <td className="py-2 px-3 text-rose-400">✕ Blocked (403)</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3">Invite Team Members &amp; Assign Roles</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-rose-400">✕ Blocked (403)</td>
                    <td className="py-2 px-3 text-rose-400">✕ Blocked (403)</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3">Verify Cryptographic Audit Log Integrity</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">✓ Yes</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: TAMPER-EVIDENT AUDIT TRAIL */}
      {section === "audit" && (
        <div className="space-y-6">
          {/* Integrity Banner */}
          {verificationReport && (
            <div
              className={`p-5 rounded-2xl border transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
                verificationReport.is_valid
                  ? "bg-emerald-950/30 border-emerald-500/40 text-emerald-200"
                  : "bg-rose-950/30 border-rose-500/40 text-rose-200"
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{verificationReport.is_valid ? "🛡️" : "⚠️"}</span>
                <div>
                  <h4 className="text-sm font-bold flex items-center gap-2">
                    <span>Audit Chain Status: {verificationReport.chain_status}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-900/60 font-mono">
                      {verificationReport.verified_records}/{verificationReport.total_records} Records Verified
                    </span>
                  </h4>
                  <p className="text-xs text-slate-300 mt-0.5">{verificationReport.message}</p>
                </div>
              </div>

              <div className="text-xs text-slate-400 font-mono">
                Verified at: {new Date(verificationReport.verified_at).toLocaleTimeString()}
              </div>
            </div>
          )}

          {/* Filter Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              {/* Action Filter */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400 font-medium">Action:</span>
                <select
                  value={filterAction}
                  onChange={(e) => setFilterAction(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Actions</option>
                  <option value="WORKSPACE_CREATED">WORKSPACE_CREATED</option>
                  <option value="USER_REGISTERED">USER_REGISTERED</option>
                  <option value="MEMBER_ADDED">MEMBER_ADDED</option>
                  <option value="MEMBER_ROLE_UPDATED">MEMBER_ROLE_UPDATED</option>
                  <option value="MEMBER_REMOVED">MEMBER_REMOVED</option>
                  <option value="API_KEY_REGISTERED">API_KEY_REGISTERED</option>
                  <option value="API_KEY_DELETED">API_KEY_DELETED</option>
                  <option value="BASELINE_SET">BASELINE_SET</option>
                  <option value="DATASET_CREATED">DATASET_CREATED</option>
                  <option value="DATASET_DELETED">DATASET_DELETED</option>
                  <option value="GUARDRAIL_POLICY_UPDATED">GUARDRAIL_POLICY_UPDATED</option>
                  <option value="REDTEAM_BENCHMARK_RUN">REDTEAM_BENCHMARK_RUN</option>
                </select>
              </div>

              {/* Search User Email */}
              <div className="flex items-center gap-2 text-xs">
                <input
                  type="text"
                  placeholder="Filter by user email..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 outline-none focus:border-indigo-500 w-48 sm:w-64 placeholder-slate-500"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={loadAuditData}
                disabled={loadingLogs}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition flex items-center gap-1.5"
              >
                <span>🔄</span>
                <span>Refresh</span>
              </button>

              <button
                onClick={exportAuditLogsJSON}
                disabled={auditLogs.length === 0}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center gap-1.5"
              >
                <span>💾</span>
                <span>Export JSON</span>
              </button>
            </div>
          </div>

          {/* Audit Log Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            {loadingLogs ? (
              <div className="p-12 text-center text-slate-400 text-sm">
                <svg className="animate-spin w-6 h-6 mx-auto mb-2 text-indigo-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading audit trail records...
              </div>
            ) : auditLogs.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-sm">
                No audit events matched the filter.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/70 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                    <tr>
                      <th className="py-3.5 px-4">Timestamp (UTC)</th>
                      <th className="py-3.5 px-4">Actor</th>
                      <th className="py-3.5 px-4">Action</th>
                      <th className="py-3.5 px-4">Resource</th>
                      <th className="py-3.5 px-4">Cryptographic Hash (SHA-256)</th>
                      <th className="py-3.5 px-4 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-4 text-slate-400 whitespace-nowrap font-mono text-[11px]">
                          {new Date(log.created_at).toLocaleString()}
                        </td>

                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="text-xs">👤</span>
                            <span className="text-slate-200 font-mono text-[11px]">
                              {log.user_email || "system@ragbench"}
                            </span>
                          </div>
                        </td>

                        <td className="py-3 px-4">
                          <span
                            className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${getActionBadgeColor(
                              log.action
                            )}`}
                          >
                            {log.action}
                          </span>
                        </td>

                        <td className="py-3 px-4">
                          <span className="text-slate-300 capitalize">{log.resource_type}</span>
                          {log.resource_id && (
                            <span className="text-slate-500 font-mono text-[10px] ml-1">
                              ({log.resource_id.slice(0, 8)}...)
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                          <span className="text-slate-500">sha256:</span>
                          <span className="text-indigo-300 ml-1">
                            {log.record_hash ? `${log.record_hash.slice(0, 12)}...${log.record_hash.slice(-8)}` : "—"}
                          </span>
                        </td>

                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => setSelectedLog(log)}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] transition font-semibold"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Invite Member Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-xl">➕</span>
                <h3 className="text-lg font-bold text-white">Invite Team Member</h3>
              </div>
              <button
                onClick={() => setShowInviteModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleInvite} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="colleague@enterprise.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Display Name (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Alice Walker"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Role &amp; Permissions *</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
                >
                  <option value="evaluator">Evaluator / Engineer (Create datasets, run evaluations, guardrails)</option>
                  <option value="admin">Admin (Full workspace control, members &amp; API keys)</option>
                  <option value="viewer">Viewer / Auditor (Read-only access to dashboards &amp; audit trail)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Initial Password (Optional)</label>
                <input
                  type="password"
                  placeholder="Leave empty for auto-generated secure key"
                  value={invitePassword}
                  onChange={(e) => setInvitePassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 rounded-xl text-slate-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviting}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition disabled:opacity-50"
                >
                  {inviting ? "Inviting..." : "Send Invite"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Inspect Log Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-xl">📜</span>
                <h3 className="text-base font-bold text-white">Audit Event Details</h3>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-500 block">Event ID:</span>
                  <span className="text-slate-300">{selectedLog.id}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Timestamp:</span>
                  <span className="text-slate-300">{new Date(selectedLog.created_at).toISOString()}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Actor:</span>
                  <span className="text-slate-300">{selectedLog.user_email || "System"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Client IP:</span>
                  <span className="text-slate-300">{selectedLog.ip_address || "127.0.0.1"}</span>
                </div>
              </div>

              <div>
                <span className="text-slate-400 block mb-1">Cryptographic Hash Linkage:</span>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                  <div>
                    <span className="text-slate-500 block text-[10px]">PREVIOUS RECORD HASH:</span>
                    <span className="text-indigo-400 break-all">{selectedLog.prev_hash || "GENESIS"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">RECORD HASH (SHA-256):</span>
                    <span className="text-emerald-400 break-all">{selectedLog.record_hash}</span>
                  </div>
                </div>
              </div>

              <div>
                <span className="text-slate-400 block mb-1">Payload Details:</span>
                <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-slate-200 overflow-x-auto max-h-48 text-[11px]">
                  {JSON.stringify(selectedLog.details || {}, null, 2)}
                </pre>
              </div>
            </div>

            <div className="mt-5 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

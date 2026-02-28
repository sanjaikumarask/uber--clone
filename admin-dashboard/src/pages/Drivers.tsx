import { useEffect, useState, useCallback } from "react";
import { api } from "../services/api";
import type { AdminDriver, LevelHistoryEntry } from "../types";

// ─── Constants ────────────────────────────────────────────────────────────────
const LEVELS = ["NORMAL", "ACTIVE", "CONSISTENT", "PRO"] as const;
type Level = typeof LEVELS[number];

const STATUS_TABS = ["ALL", "ONLINE", "BUSY", "OFFLINE", "BLOCKED"] as const;
type StatusTab = typeof STATUS_TABS[number];

const LEVEL_COLORS: Record<Level, { bg: string; color: string }> = {
  NORMAL: { bg: "rgba(142,142,147,0.15)", color: "#8E8E93" },
  ACTIVE: { bg: "rgba(0,122,255,0.15)", color: "#007AFF" },
  CONSISTENT: { bg: "rgba(255,159,10,0.15)", color: "#FF9F0A" },
  PRO: { bg: "rgba(191,90,242,0.15)", color: "#BF5AF2" },
};

const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
  ONLINE: { bg: "rgba(52,199,89,0.15)", color: "#34C759" },
  BUSY: { bg: "rgba(255,159,10,0.15)", color: "#FF9F0A" },
  OFFLINE: { bg: "rgba(142,142,147,0.15)", color: "#8E8E93" },
  BLOCKED: { bg: "rgba(255,59,48,0.15)", color: "#FF3B30" },
};

// ─── Helper Components ────────────────────────────────────────────────────────
function Badge({ label, colors }: { label: string; colors: { bg: string; color: string } }) {
  return (
    <span style={{
      padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700,
      background: colors.bg, color: colors.color, letterSpacing: 0.4,
    }}>{label}</span>
  );
}

function MetricBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div style={{ background: "rgba(255,255,255,0.07)", borderRadius: 4, height: 4, overflow: "hidden", marginTop: 4 }}>
      <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4, transition: "width 0.4s" }} />
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="glass-card" style={{ padding: "14px 16px", minWidth: 0 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 900, color: color || "var(--text-1)" }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Drivers() {
  const [drivers, setDrivers] = useState<AdminDriver[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<StatusTab>("ALL");
  const [levelFilter, setLevelFilter] = useState<Level | "ALL">("ALL");
  const [selectedDriver, setSelectedDriver] = useState<AdminDriver | null>(null);
  const [levelHistory, setLevelHistory] = useState<LevelHistoryEntry[]>([]);
  const [driverRides, setDriverRides] = useState<any[]>([]);
  const [detailTab, setDetailTab] = useState<"profile" | "history" | "level" | "trips">("profile");
  const [ridesLoading, setRidesLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  // Level-change form
  const [newLevel, setNewLevel] = useState<Level>("NORMAL");
  const [levelReason, setLevelReason] = useState("");
  const [durationDays, setDurationDays] = useState(7);

  // ─── Fetch all drivers ───────────────────────────────────────────────────
  const fetchDrivers = useCallback(() => {
    setLoading(true);
    const params: string[] = [];
    if (activeTab !== "ALL") params.push(`status=${activeTab}`);
    if (levelFilter !== "ALL") params.push(`level=${levelFilter}`);
    const qs = params.length ? `?${params.join("&")}` : "";

    api.get(`/drivers/admin/drivers/${qs}`)
      .then(res => setDrivers(Array.isArray(res.data) ? res.data : res.data.results ?? []))
      .catch(() => setDrivers([]))
      .finally(() => setLoading(false));
  }, [activeTab, levelFilter]);

  useEffect(() => { fetchDrivers(); }, [fetchDrivers]);

  // ─── Fetch level history ──────────────────────────────────────────────────
  const fetchLevelHistory = useCallback(async (driverId: number) => {
    try {
      const res = await api.get(`/drivers/admin/drivers/${driverId}/level-history/`);
      setLevelHistory(res.data);
    } catch { setLevelHistory([]); }
  }, []);

  // ─── Fetch driver rides ──────────────────────────────────────────────────
  const fetchDriverRides = useCallback(async (driverId: number) => {
    setRidesLoading(true);
    try {
      const res = await api.get(`/drivers/admin/drivers/${driverId}/history/`);
      setDriverRides(res.data);
    } catch { setDriverRides([]); }
    finally { setRidesLoading(false); }
  }, []);

  useEffect(() => {
    if (selectedDriver && detailTab === "trips") {
      fetchDriverRides(selectedDriver.driver_id);
    }
  }, [selectedDriver, detailTab, fetchDriverRides]);

  const openPanel = (driver: AdminDriver) => {
    setSelectedDriver(driver);
    setDetailTab("profile");
    setNewLevel(driver.level as Level);
    setDriverRides([]);
    fetchLevelHistory(driver.driver_id);
  };

  // ─── Driver Actions ───────────────────────────────────────────────────────
  const handleAction = async (driverId: number, action: string) => {
    if (!confirm(`Perform action "${action}" on Driver #${driverId}?`)) return;
    setActionLoading(true);
    try {
      await api.post("/drivers/admin/drivers/actions/", { driver_id: driverId, action });
      fetchDrivers();
      setSelectedDriver(null);
    } catch (err: any) {
      alert(err.response?.data?.error || "Action failed");
    } finally { setActionLoading(false); }
  };

  // ─── Level Update ─────────────────────────────────────────────────────────
  const handleLevelUpdate = async () => {
    if (!selectedDriver) return;
    if (!levelReason.trim()) { alert("Please enter a reason."); return; }
    setActionLoading(true);
    try {
      await api.post(`/drivers/admin/drivers/${selectedDriver.driver_id}/level/`, {
        level: newLevel,
        reason: levelReason,
        duration_days: durationDays,
      });
      alert(`Level updated to ${newLevel}`);
      setLevelReason("");
      fetchDrivers();
      fetchLevelHistory(selectedDriver.driver_id);
      setSelectedDriver(prev => prev ? { ...prev, level: newLevel } : null);
    } catch (err: any) {
      alert(err.response?.data?.error || "Level update failed");
    } finally { setActionLoading(false); }
  };

  // ─── Derived Stats ────────────────────────────────────────────────────────
  const stats = {
    total: drivers.length,
    online: drivers.filter(d => d.status === "ONLINE").length,
    busy: drivers.filter(d => d.status === "BUSY").length,
    blocked: drivers.filter(d => d.status === "BLOCKED").length,
    pro: drivers.filter(d => d.level === "PRO").length,
    avgScore: drivers.length
      ? (drivers.reduce((s, d) => s + (d.score || 0), 0) / drivers.length).toFixed(1)
      : "—",
  };

  return (
    <div style={{ padding: "40px", position: "relative", minHeight: "100vh" }}>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header style={{ marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ marginBottom: 6, fontSize: "1.9rem" }}>Fleet Management</h1>
          <p style={{ color: "var(--text-dim)", margin: 0 }}>Driver performance, levels & trust system.</p>
        </div>
        <button className="btn-secondary" onClick={fetchDrivers} disabled={loading}>
          {loading ? "Refreshing…" : "↻ Refresh"}
        </button>
      </header>

      {/* ── KPI Cards ───────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12, marginBottom: 28 }}>
        <StatCard label="Total Drivers" value={stats.total} />
        <StatCard label="Online" value={stats.online} color="var(--green)" />
        <StatCard label="Busy" value={stats.busy} color="#FF9F0A" />
        <StatCard label="Blocked" value={stats.blocked} color="var(--red)" />
        <StatCard label="PRO Drivers" value={stats.pro} color="#BF5AF2" />
        <StatCard label="Avg Score" value={stats.avgScore} color="var(--accent)" />
      </div>

      {/* ── Filters ─────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        {/* Status tabs */}
        <div style={{ display: "flex", background: "rgba(255,255,255,0.04)", borderRadius: 10, padding: 3 }}>
          {STATUS_TABS.map(t => (
            <button key={t} onClick={() => setActiveTab(t)} style={{
              padding: "7px 14px", borderRadius: 8, border: "none",
              background: activeTab === t ? "var(--accent)" : "transparent",
              color: activeTab === t ? "#fff" : "var(--text-dim)",
              fontWeight: activeTab === t ? 700 : 400, fontSize: 12, cursor: "pointer", transition: "all 0.2s",
            }}>{t}</button>
          ))}
        </div>
        {/* Level filter */}
        <div style={{ display: "flex", background: "rgba(255,255,255,0.04)", borderRadius: 10, padding: 3 }}>
          {(["ALL", ...LEVELS] as const).map(l => (
            <button key={l} onClick={() => setLevelFilter(l)} style={{
              padding: "7px 14px", borderRadius: 8, border: "none",
              background: levelFilter === l ? "rgba(191,90,242,0.25)" : "transparent",
              color: levelFilter === l ? "#BF5AF2" : "var(--text-dim)",
              fontWeight: levelFilter === l ? 700 : 400, fontSize: 12, cursor: "pointer", transition: "all 0.2s",
            }}>{l}</button>
          ))}
        </div>
      </div>

      {/* ── Table ───────────────────────────────────────────────────────── */}
      <div className="glass-card" style={{ overflowX: "auto" }}>
        <table style={{ minWidth: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Driver", "Status", "Level", "Score", "Acceptance", "Cancellation", "Weekly", "Rating", "Trust", ""].map(h => (
                <th key={h} style={{
                  textAlign: "left", padding: "14px 16px",
                  borderBottom: "1px solid var(--border)",
                  fontSize: 11, fontWeight: 700, color: "var(--text-dim)",
                  textTransform: "uppercase", letterSpacing: 0.8,
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={10} style={{ padding: 48, textAlign: "center", color: "var(--text-dim)" }}>Loading fleet data…</td></tr>
            ) : drivers.length === 0 ? (
              <tr><td colSpan={10} style={{ padding: 48, textAlign: "center", color: "var(--text-dim)" }}>No drivers found.</td></tr>
            ) : drivers.map(d => {
              const sc = STATUS_COLORS[d.status] || STATUS_COLORS.OFFLINE;
              const lc = LEVEL_COLORS[d.level as Level] || LEVEL_COLORS.NORMAL;
              return (
                <tr
                  key={d.driver_id}
                  onClick={() => openPanel(d)}
                  onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.025)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  style={{ cursor: "pointer", borderBottom: "1px solid rgba(255,255,255,0.04)", transition: "background 0.15s" }}
                >
                  {/* Driver */}
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{
                        width: 36, height: 36, borderRadius: "50%",
                        background: `linear-gradient(135deg, ${lc.color}aa, ${lc.color}44)`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontWeight: 900, fontSize: 14, color: "#fff",
                      }}>
                        {(d.name || "D")[0].toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
                          {d.name || `Driver #${d.driver_id}`}
                          {d.is_suspended && (
                            <span title={`Suspended until ${d.suspended_until}`} style={{ color: "#FF3B30", fontSize: 14 }}>🚫</span>
                          )}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-dim)" }}>{d.phone}</div>
                      </div>
                    </div>
                  </td>
                  {/* Status */}
                  <td style={{ padding: "14px 16px" }}>
                    <Badge label={d.status} colors={sc} />
                  </td>
                  {/* Level */}
                  <td style={{ padding: "14px 16px" }}>
                    <Badge label={d.level} colors={lc} />
                  </td>
                  {/* Score */}
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: d.score >= 70 ? "#34C759" : d.score >= 40 ? "#FF9F0A" : "#FF3B30" }}>
                      {d.score?.toFixed(1) ?? "—"}
                    </div>
                    <MetricBar value={d.score || 0} max={100} color={d.score >= 70 ? "#34C759" : d.score >= 40 ? "#FF9F0A" : "#FF3B30"} />
                  </td>
                  {/* Acceptance */}
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: d.acceptance_rate >= 80 ? "#34C759" : d.acceptance_rate >= 60 ? "#FF9F0A" : "#FF3B30" }}>
                      {d.acceptance_rate?.toFixed(1)}%
                    </div>
                    <MetricBar value={d.acceptance_rate || 0} max={100} color={d.acceptance_rate >= 80 ? "#34C759" : "#FF9F0A"} />
                  </td>
                  {/* Cancellation */}
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: d.cancellation_rate <= 10 ? "#34C759" : d.cancellation_rate <= 25 ? "#FF9F0A" : "#FF3B30" }}>
                      {d.cancellation_rate?.toFixed(1)}%
                    </div>
                    <MetricBar value={d.cancellation_rate || 0} max={50} color={d.cancellation_rate <= 10 ? "#34C759" : "#FF3B30"} />
                  </td>
                  {/* Weekly */}
                  <td style={{ padding: "14px 16px", fontSize: 13, fontWeight: 600 }}>{d.weekly_rides}</td>
                  {/* Rating */}
                  <td style={{ padding: "14px 16px" }}>
                    <span style={{ color: "#FF9F0A", fontWeight: 700 }}>{d.avg_rating?.toFixed(1)} ★</span>
                  </td>
                  {/* Trust */}
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: d.trust_score >= 70 ? "#34C759" : d.trust_score >= 40 ? "#FF9F0A" : "#FF3B30" }}>
                      {d.trust_score?.toFixed(0)}
                    </div>
                    <MetricBar value={d.trust_score || 0} max={100} color={d.trust_score >= 70 ? "#34C759" : "#FF3B30"} />
                  </td>
                  {/* Action */}
                  <td style={{ padding: "14px 16px" }} onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => openPanel(d)}
                      style={{
                        padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)",
                        background: "rgba(255,255,255,0.05)", color: "var(--text-1)", fontSize: 12, cursor: "pointer",
                      }}
                    >Details →</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Detail Side Panel ────────────────────────────────────────────── */}
      {selectedDriver && (
        <>
          {/* Backdrop */}
          <div
            onClick={() => setSelectedDriver(null)}
            style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 999, backdropFilter: "blur(2px)" }}
          />

          <div style={{
            position: "fixed", top: 0, right: 0, width: 480, height: "100vh",
            background: "var(--bg-card)", borderLeft: "1px solid var(--border)",
            boxShadow: "-20px 0 50px rgba(0,0,0,0.6)",
            zIndex: 1000, display: "flex", flexDirection: "column", overflow: "hidden",
          }}>

            {/* Panel Header */}
            <div style={{ padding: "24px 28px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{
                width: 48, height: 48, borderRadius: "50%",
                background: `linear-gradient(135deg, ${LEVEL_COLORS[selectedDriver.level as Level]?.color ?? "#666"}aa, #222)`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontWeight: 900, fontSize: 18, color: "#fff", flexShrink: 0,
              }}>
                {(selectedDriver.name || "D")[0].toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 2 }}>{selectedDriver.name || `Driver #${selectedDriver.driver_id}`}</div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <Badge label={selectedDriver.status} colors={STATUS_COLORS[selectedDriver.status] || STATUS_COLORS.OFFLINE} />
                  <Badge label={selectedDriver.level} colors={LEVEL_COLORS[selectedDriver.level as Level] || LEVEL_COLORS.NORMAL} />
                </div>
              </div>
              <button onClick={() => setSelectedDriver(null)} style={{ background: "none", border: "none", color: "var(--text-dim)", fontSize: 22, cursor: "pointer" }}>×</button>
            </div>

            {/* Inner Tabs */}
            <div style={{ display: "flex", borderBottom: "1px solid var(--border)", padding: "0 28px" }}>
              {(["profile", "level", "history", "trips"] as const).map(t => (
                <button key={t} onClick={() => setDetailTab(t)} style={{
                  padding: "12px 16px", background: "none", border: "none",
                  borderBottom: detailTab === t ? "2px solid var(--accent)" : "2px solid transparent",
                  color: detailTab === t ? "var(--accent)" : "var(--text-dim)",
                  fontWeight: detailTab === t ? 700 : 400, fontSize: 13, cursor: "pointer", textTransform: "capitalize",
                }}>{t}</button>
              ))}
            </div>

            <div style={{ flex: 1, overflowY: "auto", padding: "24px 28px", display: "flex", flexDirection: "column", gap: 20 }}>

              {/* ── Profile Tab ──────────────────────────────────────── */}
              {detailTab === "profile" && (
                <>
                  {/* Metrics grid */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                    <StatCard label="Score" value={selectedDriver.score?.toFixed(1) ?? "—"} color="var(--accent)" />
                    <StatCard label="Trust Score" value={selectedDriver.trust_score?.toFixed(0) ?? "—"} color={selectedDriver.trust_score >= 70 ? "#34C759" : "#FF3B30"} />
                    <StatCard label="Acceptance" value={`${selectedDriver.acceptance_rate?.toFixed(1)}%`} color="#34C759" />
                    <StatCard label="Cancellation" value={`${selectedDriver.cancellation_rate?.toFixed(1)}%`} color={selectedDriver.cancellation_rate > 25 ? "#FF3B30" : "#FF9F0A"} />
                    <StatCard label="Completed" value={selectedDriver.completed_rides} />
                    <StatCard label="Cancelled" value={selectedDriver.cancelled_rides} color={selectedDriver.cancelled_rides > 5 ? "#FF9F0A" : undefined} />
                    <StatCard label="Weekly Rides" value={selectedDriver.weekly_rides} />
                    <StatCard label="Peak Rides" value={selectedDriver.peak_hour_rides} />
                    <StatCard label="Offered" value={selectedDriver.offered_rides} />
                    <StatCard label="Accepted" value={selectedDriver.accepted_rides} />
                    <StatCard label="Rating" value={`${selectedDriver.avg_rating?.toFixed(1)} ★`} color="#FF9F0A" />
                    <StatCard label="Fraud Flags" value={selectedDriver.fraud_flags} color={selectedDriver.fraud_flags > 0 ? "#FF3B30" : undefined} />
                  </div>

                  {selectedDriver.is_suspended && selectedDriver.suspended_until && (
                    <div style={{
                      padding: "12px 16px", borderRadius: 10,
                      background: "rgba(255,59,48,0.1)", border: "1px solid rgba(255,59,48,0.3)",
                      color: "#FF3B30", fontSize: 13,
                    }}>
                      🚫 Suspended until {new Date(selectedDriver.suspended_until).toLocaleString()}
                    </div>
                  )}

                  {/* Admin Actions */}
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 12 }}>Admin Controls</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                      {selectedDriver.is_suspended ? (
                        <button
                          className="btn-primary"
                          style={{ background: "#34C759", gridColumn: "1 / -1" }}
                          onClick={() => handleAction(selectedDriver.driver_id, "unsuspend")}
                          disabled={actionLoading}
                        >✓ Unsuspend Driver</button>
                      ) : (
                        <button
                          className="btn-primary"
                          style={{ background: "#FF3B30" }}
                          onClick={() => handleAction(selectedDriver.driver_id, "suspend")}
                          disabled={actionLoading}
                        >🚫 Suspend (24h)</button>
                      )}
                      {selectedDriver.status === "BLOCKED" ? (
                        <button className="btn-secondary" onClick={() => handleAction(selectedDriver.driver_id, "unblock")} disabled={actionLoading}>
                          Unblock
                        </button>
                      ) : (
                        <button className="btn-secondary" style={{ color: "var(--danger)", borderColor: "var(--danger)" }}
                          onClick={() => handleAction(selectedDriver.driver_id, "block")} disabled={actionLoading}>
                          Block
                        </button>
                      )}
                      {selectedDriver.status !== "OFFLINE" && (
                        <button className="btn-secondary" style={{ color: "#FF9F0A", borderColor: "#FF9F0A" }}
                          onClick={() => handleAction(selectedDriver.driver_id, "force_offline")} disabled={actionLoading}>
                          Force Offline
                        </button>
                      )}
                      <button className="btn-secondary"
                        onClick={() => handleAction(selectedDriver.driver_id, "recalculate_score")} disabled={actionLoading}>
                        ⟳ Recalc Score
                      </button>
                    </div>
                  </div>
                </>
              )}

              {/* ── Level Tab ─────────────────────────────────────────── */}
              {detailTab === "level" && (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <div style={{ fontSize: 13, color: "var(--text-2)" }}>
                    Current level: <Badge label={selectedDriver.level} colors={LEVEL_COLORS[selectedDriver.level as Level] || LEVEL_COLORS.NORMAL} />
                  </div>

                  {/* Level selector */}
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 10 }}>Set New Level</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                      {LEVELS.map(l => {
                        const lc = LEVEL_COLORS[l];
                        const active = newLevel === l;
                        return (
                          <button key={l} onClick={() => setNewLevel(l)} style={{
                            padding: "12px 16px", borderRadius: 10, border: `2px solid ${active ? lc.color : "var(--border)"}`,
                            background: active ? lc.bg : "transparent",
                            color: active ? lc.color : "var(--text-2)",
                            fontWeight: active ? 700 : 500, fontSize: 13, cursor: "pointer", transition: "all 0.2s", textAlign: "left",
                          }}>
                            <div style={{ fontWeight: 800 }}>{l}</div>
                            <div style={{ fontSize: 10, opacity: 0.7 }}>
                              {l === "NORMAL" ? "Default tier" : l === "ACTIVE" ? "Acc ≥70%, 10+ rides/wk" : l === "CONSISTENT" ? "Acc ≥80%, 25+ rides/wk" : "Acc ≥90%, 40+ rides/wk"}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Reason */}
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>Reason *</div>
                    <textarea
                      value={levelReason}
                      onChange={e => setLevelReason(e.target.value)}
                      placeholder="e.g. Exceptional performance during surge period"
                      rows={3}
                      style={{
                        width: "100%", padding: "10px 12px", borderRadius: 8,
                        background: "var(--bg-3)", border: "1px solid var(--border)",
                        color: "var(--text-1)", fontSize: 13, resize: "vertical", boxSizing: "border-box",
                      }}
                    />
                  </div>

                  {/* Duration */}
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>Override Duration (Days)</div>
                    <input
                      type="number"
                      value={durationDays}
                      onChange={e => setDurationDays(parseInt(e.target.value) || 1)}
                      min={1}
                      max={365}
                      style={{
                        width: "100%", padding: "10px 12px", borderRadius: 8,
                        background: "var(--bg-3)", border: "1px solid var(--border)",
                        color: "var(--text-1)", fontSize: 13, boxSizing: "border-box",
                      }}
                    />
                    <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 4 }}>
                      The system will not auto-evaluate levels until this period expires.
                    </div>
                  </div>

                  <button
                    className="btn-primary"
                    onClick={handleLevelUpdate}
                    disabled={actionLoading || newLevel === selectedDriver.level || !levelReason.trim()}
                  >
                    {actionLoading ? "Saving…" : `Set Level → ${newLevel}`}
                  </button>
                </div>
              )}

              {/* ── History Tab ───────────────────────────────────────── */}
              {detailTab === "history" && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 14 }}>Level Change History</div>
                  {levelHistory.length === 0 ? (
                    <div style={{ color: "var(--text-dim)", fontSize: 13 }}>No level changes recorded.</div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {levelHistory.map((h, i) => (
                        <div key={i} style={{
                          padding: "12px 14px", borderRadius: 10,
                          background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)",
                        }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                            <Badge label={h.old_level} colors={LEVEL_COLORS[h.old_level as Level] || LEVEL_COLORS.NORMAL} />
                            <span style={{ color: "var(--text-dim)", fontSize: 14 }}>→</span>
                            <Badge label={h.new_level} colors={LEVEL_COLORS[h.new_level as Level] || LEVEL_COLORS.NORMAL} />
                          </div>
                          <div style={{ fontSize: 12, color: "var(--text-2)", marginBottom: 4 }}>{h.reason}</div>
                          <div style={{ fontSize: 11, color: "var(--text-dim)", display: "flex", justifyContent: "space-between" }}>
                            <span>by {h.changed_by}</span>
                            <span>{new Date(h.timestamp).toLocaleString()}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ── Trips Tab ─────────────────────────────────────────── */}
              {detailTab === "trips" && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 14 }}>Recent Trips</div>
                  {ridesLoading ? (
                    <div style={{ color: "var(--text-dim)", fontSize: 13, textAlign: "center", padding: 20 }}>Loading trips…</div>
                  ) : driverRides.length === 0 ? (
                    <div style={{ color: "var(--text-dim)", fontSize: 13 }}>No recent trips found for this driver.</div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {driverRides.map((r) => {
                        const isCompleted = r.status === "COMPLETED";
                        const isCancelled = r.status === "CANCELLED" || r.status === "DRIVER_CANCELLED";
                        return (
                          <div key={r.id} style={{
                            padding: "14px", borderRadius: 10,
                            background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)",
                            display: "flex", justifyContent: "space-between", alignItems: "center",
                          }}>
                            <div>
                              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 2 }}>#{r.id} • ₹{r.final_fare || r.base_fare}</div>
                              <div style={{ fontSize: 12, color: "var(--text-dim)" }}>
                                {new Date(r.created_at).toLocaleDateString()} • {new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </div>
                            </div>
                            <div style={{ textAlign: "right" }}>
                              <Badge
                                label={r.status}
                                colors={{
                                  bg: isCompleted ? "rgba(52,199,89,0.15)" : isCancelled ? "rgba(255,59,48,0.15)" : "rgba(255,159,10,0.15)",
                                  color: isCompleted ? "#34C759" : isCancelled ? "#FF3B30" : "#FF9F0A"
                                }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

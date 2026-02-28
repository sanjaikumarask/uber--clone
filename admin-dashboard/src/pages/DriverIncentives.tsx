import { useState, useEffect } from "react";
import {
    getIncentives, createIncentive, deleteIncentive,
    activateIncentive, deactivateIncentive, getIncentiveAnalytics
} from "../services/driverIncentives";
import type { DriverIncentive, IncentiveAnalytics } from "../services/driverIncentives";

const INPUT: React.CSSProperties = {
    padding: "10px 14px", background: "var(--bg-2)", border: "1px solid var(--border-2)",
    borderRadius: "var(--r-sm)", color: "var(--text-1)", outline: "none", width: "100%",
    fontFamily: "var(--font)", fontSize: "0.875rem",
};

const TYPE_CONFIG: Record<string, { label: string; badge: string; icon: string }> = {
    STREAK: { label: "Ride Streak", badge: "badge-green", icon: "🔥" },
    PEAK: { label: "Peak Hours", badge: "badge-yellow", icon: "⚡" },
    ZONE: { label: "Geo-Zone", badge: "badge-purple", icon: "📍" },
};

export default function DriverIncentivesPage() {
    const [incentives, setIncentives] = useState<DriverIncentive[]>([]);
    const [analytics, setAnalytics] = useState<IncentiveAnalytics | null>(null);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [tab, setTab] = useState<"list" | "analytics">("list");

    const [form, setForm] = useState({
        type: "STREAK" as "STREAK" | "PEAK" | "ZONE",
        title: "", description: "",
        reward_amount: 0, max_per_day: 1,
        valid_from: new Date().toISOString().slice(0, 16),
        valid_to: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 16),
        city: "",
        // Condition fields (dynamic by type)
        rides_required: 3,
        start_hour: 17, end_hour: 20,
        zone_city: "",
    });

    useEffect(() => { fetchAll(); }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [incRes, anaRes] = await Promise.all([getIncentives(), getIncentiveAnalytics()]);
            setIncentives(incRes.data);
            setAnalytics(anaRes.data);
        } catch (err) { console.error(err); }
        setLoading(false);
    };

    const buildCondition = () => {
        switch (form.type) {
            case "STREAK": return { rides_required: form.rides_required };
            case "PEAK": return { start_hour: form.start_hour, end_hour: form.end_hour };
            case "ZONE": return { city: form.zone_city };
            default: return {};
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await createIncentive({
                type: form.type,
                title: form.title,
                description: form.description,
                reward_amount: form.reward_amount,
                max_per_day: form.max_per_day,
                valid_from: new Date(form.valid_from).toISOString(),
                valid_to: new Date(form.valid_to).toISOString(),
                city: form.city,
                condition: buildCondition(),
                is_active: true,
            });
            setShowModal(false);
            fetchAll();
        } catch (err: any) {
            alert(err?.response?.data ? JSON.stringify(err.response.data) : "Failed to create incentive");
        }
    };

    const toggleActive = async (inc: DriverIncentive) => {
        try {
            if (inc.is_active) await deactivateIncentive(inc.id!);
            else await activateIncentive(inc.id!);
            fetchAll();
        } catch (err) { console.error(err); }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this incentive permanently?")) return;
        try { await deleteIncentive(id); fetchAll(); } catch (err) { console.error(err); }
    };

    const conditionSummary = (inc: DriverIncentive) => {
        const c = inc.condition;
        if (inc.type === "STREAK") return `${c.rides_required || "?"} rides`;
        if (inc.type === "PEAK") return `${c.start_hour || "?"}:00 – ${c.end_hour || "?"}:00`;
        if (inc.type === "ZONE") return c.city || "Geo area";
        return "—";
    };

    return (
        <div className="page animate-fade">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">Driver Incentives</h1>
                    <p className="page-sub">Performance rewards, streak bonuses, and geo-zone programs.</p>
                </div>
                <button className="btn-primary" onClick={() => setShowModal(true)}>+ New Incentive</button>
            </div>

            {/* Stats Row */}
            {analytics && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 28 }}>
                    <StatBox label="Total Paid Out" value={`₹${analytics.total_incentives_paid.toLocaleString()}`} color="var(--green)" />
                    <StatBox label="Active Programs" value={String(incentives.filter(i => i.is_active).length)} color="var(--accent)" />
                    <StatBox label="Total Redemptions" value={String(analytics.per_incentive_breakdown.reduce((a, b) => a + b.redemption_count, 0))} color="var(--purple)" />
                    <StatBox label="Programs Total" value={String(incentives.length)} color="var(--cyan)" />
                </div>
            )}

            {/* Tabs */}
            <div style={{ display: "flex", gap: 4, marginBottom: 24 }}>
                {(["list", "analytics"] as const).map(t => (
                    <button key={t} onClick={() => setTab(t)}
                        style={{
                            padding: "8px 18px", fontSize: "0.8rem", fontWeight: 600,
                            background: tab === t ? "var(--accent)" : "transparent",
                            color: tab === t ? "#fff" : "var(--text-2)",
                            border: tab === t ? "none" : "1px solid var(--border)",
                            borderRadius: "var(--r-sm)", cursor: "pointer",
                        }}>
                        {t === "list" ? "All Incentives" : "Analytics"}
                    </button>
                ))}
            </div>

            {loading ? <LoadingSkeleton /> : tab === "list" ? (
                /* ─── INCENTIVES TABLE ─── */
                <div style={{ overflowX: "auto" }}>
                    <table>
                        <thead><tr>
                            <th>Type</th><th>Title</th><th>Condition</th><th>Reward</th>
                            <th>Max/Day</th><th>City</th><th>Valid</th><th>Status</th><th>Actions</th>
                        </tr></thead>
                        <tbody>
                            {incentives.length === 0 && <tr><td colSpan={9} style={{ textAlign: "center", color: "var(--text-3)", padding: 40 }}>No incentives created yet.</td></tr>}
                            {incentives.map(inc => {
                                const cfg = TYPE_CONFIG[inc.type] || { label: inc.type, badge: "badge-gray", icon: "📋" };
                                return (
                                    <tr key={inc.id}>
                                        <td>
                                            <span className={`badge ${cfg.badge}`}>
                                                {cfg.icon} {cfg.label}
                                            </span>
                                        </td>
                                        <td style={{ fontWeight: 500 }}>{inc.title}</td>
                                        <td style={{ color: "var(--text-2)", fontSize: "0.85rem" }}>{conditionSummary(inc)}</td>
                                        <td style={{ fontWeight: 700, color: "var(--green)" }}>₹{inc.reward_amount}</td>
                                        <td style={{ color: "var(--text-2)" }}>{inc.max_per_day}</td>
                                        <td style={{ color: "var(--text-2)" }}>{inc.city || "Global"}</td>
                                        <td style={{ fontSize: "0.75rem", color: "var(--text-3)" }}>
                                            {fmt(inc.valid_from)} →<br />{fmt(inc.valid_to)}
                                        </td>
                                        <td>
                                            <button onClick={() => toggleActive(inc)}
                                                className={inc.is_active ? "badge badge-green" : "badge badge-gray"}
                                                style={{ cursor: "pointer", border: "none" }}>
                                                {inc.is_active ? "Active" : "Inactive"}
                                            </button>
                                        </td>
                                        <td>
                                            <button className="btn-danger" style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                                                onClick={() => handleDelete(inc.id!)}>Delete</button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            ) : (
                <AnalyticsPanel analytics={analytics} />
            )}

            {/* ─── CREATE MODAL ─── */}
            {showModal && (
                <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000 }}>
                    <div className="card animate-fade" style={{ width: 520, maxHeight: "90vh", overflow: "auto" }}>
                        <h2 style={{ marginBottom: 24 }}>Create New Incentive</h2>
                        <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: 16 }}>

                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                                <Field label="Incentive Type">
                                    <select style={INPUT} value={form.type}
                                        onChange={e => setForm({ ...form, type: e.target.value as any })}>
                                        <option value="STREAK">🔥 Streak (N rides)</option>
                                        <option value="PEAK">⚡ Peak Hours</option>
                                        <option value="ZONE">📍 Geo-Zone</option>
                                    </select>
                                </Field>
                                <Field label="Title">
                                    <input style={INPUT} required placeholder="5-Ride Streak Bonus"
                                        value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
                                </Field>
                            </div>

                            <Field label="Description">
                                <input style={INPUT} placeholder="Optional details for drivers..."
                                    value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                            </Field>

                            {/* Dynamic condition fields */}
                            <div className="card" style={{ padding: 16, background: "var(--bg-2)" }}>
                                <div style={{ fontSize: "0.7rem", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "1px", fontWeight: 600, marginBottom: 12 }}>
                                    Condition Config — {TYPE_CONFIG[form.type]?.label}
                                </div>
                                {form.type === "STREAK" && (
                                    <Field label="Rides Required">
                                        <input type="number" style={INPUT} min={1} value={form.rides_required}
                                            onChange={e => setForm({ ...form, rides_required: +e.target.value })} />
                                    </Field>
                                )}
                                {form.type === "PEAK" && (
                                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                                        <Field label="Start Hour (0–23)">
                                            <input type="number" style={INPUT} min={0} max={23} value={form.start_hour}
                                                onChange={e => setForm({ ...form, start_hour: +e.target.value })} />
                                        </Field>
                                        <Field label="End Hour (0–23)">
                                            <input type="number" style={INPUT} min={0} max={23} value={form.end_hour}
                                                onChange={e => setForm({ ...form, end_hour: +e.target.value })} />
                                        </Field>
                                    </div>
                                )}
                                {form.type === "ZONE" && (
                                    <Field label="Target City">
                                        <input style={INPUT} placeholder="e.g. Chennai"
                                            value={form.zone_city} onChange={e => setForm({ ...form, zone_city: e.target.value })} />
                                    </Field>
                                )}
                            </div>

                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                                <Field label="Reward Amount (₹)">
                                    <input type="number" style={INPUT} required min={0} value={form.reward_amount}
                                        onChange={e => setForm({ ...form, reward_amount: +e.target.value })} />
                                </Field>
                                <Field label="Max Per Day">
                                    <input type="number" style={INPUT} min={1} value={form.max_per_day}
                                        onChange={e => setForm({ ...form, max_per_day: +e.target.value })} />
                                </Field>
                            </div>

                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                                <Field label="Valid From">
                                    <input type="datetime-local" style={INPUT} value={form.valid_from}
                                        onChange={e => setForm({ ...form, valid_from: e.target.value })} />
                                </Field>
                                <Field label="Valid To">
                                    <input type="datetime-local" style={INPUT} value={form.valid_to}
                                        onChange={e => setForm({ ...form, valid_to: e.target.value })} />
                                </Field>
                            </div>

                            <Field label="City (empty = global)">
                                <input style={INPUT} placeholder="e.g. Chennai"
                                    value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} />
                            </Field>

                            <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
                                <button type="button" className="btn-ghost" style={{ flex: 1 }} onClick={() => setShowModal(false)}>Cancel</button>
                                <button type="submit" className="btn-primary" style={{ flex: 1 }}>Create Incentive</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Helpers ──────────────────────────────────────────────────────── */
function fmt(iso: string) {
    try { return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "2-digit" }); }
    catch { return iso; }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: "0.75rem", color: "var(--text-3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>{label}</label>
            {children}
        </div>
    );
}

function StatBox({ label, value, color }: { label: string; value: string; color: string }) {
    return (
        <div className="stat-card">
            <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: color }} />
            <div style={{ fontSize: "0.7rem", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "1px", fontWeight: 600, marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 800, color }}>{value}</div>
        </div>
    );
}

function LoadingSkeleton() {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 48, borderRadius: "var(--r-sm)" }} />)}
        </div>
    );
}

function AnalyticsPanel({ analytics }: { analytics: IncentiveAnalytics | null }) {
    if (!analytics) return <p style={{ color: "var(--text-3)" }}>No analytics data available.</p>;

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Per-incentive breakdown */}
            <div className="card">
                <h3 style={{ fontSize: "1rem", marginBottom: 16, color: "var(--text-2)" }}>Per-Incentive Breakdown</h3>
                <table>
                    <thead><tr>
                        <th>Type</th><th>Title</th><th>Redemptions</th><th>Total Paid</th>
                    </tr></thead>
                    <tbody>
                        {analytics.per_incentive_breakdown.length === 0 && (
                            <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--text-3)", padding: 32 }}>No payouts yet.</td></tr>
                        )}
                        {analytics.per_incentive_breakdown.map((b, i) => {
                            const cfg = TYPE_CONFIG[b.incentive__type] || { label: b.incentive__type, badge: "badge-gray", icon: "📋" };
                            return (
                                <tr key={i}>
                                    <td><span className={`badge ${cfg.badge}`}>{cfg.icon} {cfg.label}</span></td>
                                    <td>{b.incentive__title}</td>
                                    <td style={{ fontWeight: 600 }}>{b.redemption_count}</td>
                                    <td style={{ fontWeight: 600, color: "var(--green)" }}>₹{b.total_paid?.toLocaleString()}</td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {/* Daily trend */}
            <div className="card">
                <h3 style={{ fontSize: "1rem", marginBottom: 16, color: "var(--text-2)" }}>Daily Payout Trend (Last 7 Days)</h3>
                {analytics.daily_last_7_days.length === 0 ? (
                    <p style={{ color: "var(--text-3)" }}>No data for the last 7 days.</p>
                ) : (
                    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 160 }}>
                        {analytics.daily_last_7_days.map((d, i) => {
                            const max = Math.max(...analytics.daily_last_7_days.map(x => x.total));
                            const h = max > 0 ? (d.total / max) * 140 : 4;
                            return (
                                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                                    <span style={{ fontSize: "0.65rem", color: "var(--text-2)", fontWeight: 600 }}>₹{d.total}</span>
                                    <div style={{
                                        width: "100%", height: h, borderRadius: "4px 4px 0 0",
                                        background: "linear-gradient(180deg, var(--green), var(--cyan))",
                                        transition: "height 0.4s ease",
                                    }} />
                                    <span style={{ fontSize: "0.6rem", color: "var(--text-3)" }}>
                                        {new Date(d.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}

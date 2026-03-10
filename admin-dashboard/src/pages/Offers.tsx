import { useState, useEffect } from "react";
import {
    getOffers, createOffer, deleteOffer, activateOffer, deactivateOffer, getOfferAnalytics
} from "../services/offers";
import type { OfferData, OfferAnalytics } from "../services/offers";

const INPUT: React.CSSProperties = {
    padding: "10px 14px", background: "var(--bg-2)", border: "1px solid var(--border-2)",
    borderRadius: "var(--r-sm)", color: "var(--text-1)", outline: "none", width: "100%",
    fontFamily: "var(--font)", fontSize: "0.875rem",
};

export default function Offers() {
    const [offers, setOffers] = useState<OfferData[]>([]);
    const [analytics, setAnalytics] = useState<OfferAnalytics | null>(null);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [tab, setTab] = useState<"list" | "analytics">("list");

    const [form, setForm] = useState({
        code: "", title: "", description: "", discount_type: "FLAT" as "FLAT" | "PERCENTAGE",
        value: 0, max_discount: null as number | null, min_ride_value: 0,
        usage_limit: null as number | null, per_user_limit: 1,
        valid_from: new Date().toISOString().slice(0, 16),
        valid_to: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 16),
        city: "",
    });

    useEffect(() => { fetchAll(); }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [offerRes, analyticsRes] = await Promise.all([getOffers(), getOfferAnalytics()]);
            setOffers(offerRes.data);
            setAnalytics(analyticsRes.data);
        } catch (err) { console.error(err); }
        setLoading(false);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await createOffer({
                ...form,
                valid_from: new Date(form.valid_from).toISOString(),
                valid_to: new Date(form.valid_to).toISOString(),
                is_active: true,
            });
            setShowModal(false);
            fetchAll();
        } catch (err: any) {
            alert(err?.response?.data ? JSON.stringify(err.response.data) : "Failed to create offer");
        }
    };

    const toggleActive = async (offer: OfferData) => {
        try {
            if (offer.is_active) await deactivateOffer(offer.id!);
            else await activateOffer(offer.id!);
            fetchAll();
        } catch (err) { console.error(err); }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this offer permanently?")) return;
        try { await deleteOffer(id); fetchAll(); } catch (err) { console.error(err); }
    };

    return (
        <div className="page animate-fade">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">Promotions & Offers</h1>
                    <p className="page-sub">Create, manage, and monitor rider discount campaigns.</p>
                </div>
                <button className="btn-primary" onClick={() => setShowModal(true)}>+ New Offer</button>
            </div>

            {/* Stats Row */}
            {analytics && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 28 }}>
                    <StatBox label="Total Discounts Given" value={`₹${analytics.total_discounts_given.toLocaleString()}`} color="var(--green)" />
                    <StatBox label="Active Offers" value={String(offers.filter(o => o.is_active).length)} color="var(--accent)" />
                    <StatBox label="Total Offers" value={String(offers.length)} color="var(--cyan)" />
                    <StatBox label="Total Redemptions" value={String(analytics.per_offer_breakdown.reduce((a, b) => a + b.usage_count, 0))} color="var(--purple)" />
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
                        {t === "list" ? "All Offers" : "Analytics"}
                    </button>
                ))}
            </div>

            <OfferContent
                loading={loading}
                tab={tab}
                offers={offers}
                toggleActive={toggleActive}
                handleDelete={handleDelete}
                analytics={analytics}
            />

            {/* ─── CREATE MODAL ─── */}
            {showModal && (
                <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000 }}>
                    <div className="card animate-fade" style={{ width: 520, maxHeight: "90vh", overflow: "auto" }}>
                        <h2 style={{ marginBottom: 24 }}>Create New Offer</h2>
                        <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: 16 }}>

                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                                <Field label="Code">
                                    <input style={INPUT} required placeholder="SUMMER50"
                                        value={form.code} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} />
                                </Field>
                                <Field label="Title">
                                    <input style={INPUT} required placeholder="Summer Sale"
                                        value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
                                </Field>
                            </div>

                            <Field label="Description">
                                <input style={INPUT} placeholder="Optional description..."
                                    value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                            </Field>

                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
                                <Field label="Discount Type">
                                    <select style={INPUT} value={form.discount_type}
                                        onChange={e => setForm({ ...form, discount_type: e.target.value as any })}>
                                        <option value="FLAT">Flat (₹)</option>
                                        <option value="PERCENTAGE">Percent (%)</option>
                                    </select>
                                </Field>
                                <Field label="Value">
                                    <input type="number" style={INPUT} required min={0}
                                        value={form.value} onChange={e => setForm({ ...form, value: +e.target.value })} />
                                </Field>
                                <Field label="Max Discount (₹)">
                                    <input type="number" style={INPUT} placeholder="No cap"
                                        value={form.max_discount ?? ""} onChange={e => setForm({ ...form, max_discount: e.target.value ? +e.target.value : null })} />
                                </Field>
                            </div>

                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
                                <Field label="Min Ride Value (₹)">
                                    <input type="number" style={INPUT} value={form.min_ride_value}
                                        onChange={e => setForm({ ...form, min_ride_value: +e.target.value })} />
                                </Field>
                                <Field label="Usage Limit">
                                    <input type="number" style={INPUT} placeholder="Unlimited"
                                        value={form.usage_limit ?? ""} onChange={e => setForm({ ...form, usage_limit: e.target.value ? +e.target.value : null })} />
                                </Field>
                                <Field label="Per User Limit">
                                    <input type="number" style={INPUT} value={form.per_user_limit} min={1}
                                        onChange={e => setForm({ ...form, per_user_limit: +e.target.value })} />
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

                            <Field label="City (leave empty for global)">
                                <input style={INPUT} placeholder="e.g. Chennai"
                                    value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} />
                            </Field>

                            <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
                                <button type="button" className="btn-ghost" style={{ flex: 1 }} onClick={() => setShowModal(false)}>Cancel</button>
                                <button type="submit" className="btn-primary" style={{ flex: 1 }}>Create Offer</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

function OfferContent({ loading, tab, offers, toggleActive, handleDelete, analytics }: any) {
    if (loading) return <LoadingSkeleton />;
    if (tab === "analytics") return <AnalyticsPanel analytics={analytics} />;

    return (
        <div style={{ overflowX: "auto" }}>
            <table>
                <thead>
                    <tr>
                        <th>Code</th><th>Title</th><th>Type</th><th>Value</th>
                        <th>Max Disc.</th><th>Usage</th><th>City</th>
                        <th>Valid</th><th>Status</th><th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {offers.length === 0 && (
                        <tr><td colSpan={10} style={{ textAlign: "center", color: "var(--text-3)", padding: 40 }}>No offers created yet.</td></tr>
                    )}
                    {offers.map((o: any) => (
                        <tr key={o.id}>
                            <td><span className="badge badge-blue">{o.code}</span></td>
                            <td style={{ fontWeight: 500 }}>{o.title}</td>
                            <td><span className="badge badge-purple">{o.discount_type}</span></td>
                            <td style={{ fontWeight: 600 }}>
                                {o.discount_type === "FLAT" ? `₹${o.value}` : `${o.value}%`}
                            </td>
                            <td style={{ color: "var(--text-2)" }}>{o.max_discount ? `₹${o.max_discount}` : "—"}</td>
                            <td style={{ color: "var(--text-2)" }}>
                                {o.total_usage_count}{o.usage_limit ? `/${o.usage_limit}` : ""}
                            </td>
                            <td style={{ color: "var(--text-2)" }}>{o.city || "Global"}</td>
                            <td style={{ fontSize: "0.75rem", color: "var(--text-3)" }}>
                                {fmt(o.valid_from)} →<br />{fmt(o.valid_to)}
                            </td>
                            <td>
                                <button onClick={() => toggleActive(o)}
                                    className={o.is_active ? "badge badge-green" : "badge badge-gray"}
                                    style={{ cursor: "pointer", border: "none" }}>
                                    {o.is_active ? "Active" : "Inactive"}
                                </button>
                            </td>
                            <td>
                                <button className="btn-danger" style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                                    onClick={() => handleDelete(o.id!)}>Delete</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
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

function AnalyticsPanel({ analytics }: { analytics: OfferAnalytics | null }) {
    if (!analytics) return <p style={{ color: "var(--text-3)" }}>No analytics data available.</p>;

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Per-offer breakdown */}
            <div className="card">
                <h3 style={{ fontSize: "1rem", marginBottom: 16, color: "var(--text-2)" }}>Per-Offer Breakdown</h3>
                <table>
                    <thead><tr>
                        <th>Code</th><th>Title</th><th>Redemptions</th><th>Total Discount</th>
                    </tr></thead>
                    <tbody>
                        {analytics.per_offer_breakdown.length === 0 && (
                            <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--text-3)", padding: 32 }}>No usage data yet.</td></tr>
                        )}
                        {analytics.per_offer_breakdown.map((b) => (
                            <tr key={b.offer__code}>
                                <td><span className="badge badge-blue">{b.offer__code}</span></td>
                                <td>{b.offer__title}</td>
                                <td style={{ fontWeight: 600 }}>{b.usage_count}</td>
                                <td style={{ fontWeight: 600, color: "var(--green)" }}>₹{b.total_discount?.toLocaleString()}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Daily trend (last 7 days) */}
            <div className="card">
                <h3 style={{ fontSize: "1rem", marginBottom: 16, color: "var(--text-2)" }}>Daily Discount Trend (Last 7 Days)</h3>
                {analytics.daily_last_7_days.length === 0 ? (
                    <p style={{ color: "var(--text-3)" }}>No data for the last 7 days.</p>
                ) : (
                    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 160 }}>
                        {analytics.daily_last_7_days.map((d) => {
                            const max = Math.max(...analytics.daily_last_7_days.map(x => x.total));
                            const h = max > 0 ? (d.total / max) * 140 : 4;
                            return (
                                <div key={d.date} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                                    <span style={{ fontSize: "0.65rem", color: "var(--text-2)", fontWeight: 600 }}>₹{d.total}</span>
                                    <div style={{
                                        width: "100%", height: h, borderRadius: "4px 4px 0 0",
                                        background: `linear-gradient(180deg, var(--accent), var(--purple))`,
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

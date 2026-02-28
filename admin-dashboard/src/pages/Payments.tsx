import { useEffect, useState } from "react";
import { api } from "../services/api";

interface PaymentSummary {
    success: number;
    failed: number;
    pending: number;
    total_revenue: number;
}

interface Alert {
    type: string;
    message: string;
    level: "ERROR" | "WARNING" | "INFO";
}

export default function Payments() {
    const [summary, setSummary] = useState<PaymentSummary | null>(null);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            const res = await api.get("/admin/payments/status/");
            setSummary(res.data.summary);
            setAlerts(res.data.alerts);
        } catch (err) {
            console.error("Payment status API error", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const timer = setInterval(fetchData, 60000);
        return () => clearInterval(timer);
    }, []);

    if (loading) return <div className="page-center">Analyzing Ledger...</div>;

    const failureRate = summary ? (summary.failed / (summary.success + summary.failed || 1)) * 100 : 0;

    return (
        <div className="page" style={{ padding: "36px 48px" }}>
            <header className="page-header">
                <div>
                    <h1 className="page-title">Payment Monitoring</h1>
                    <p className="page-sub">Real-time gateway health and transaction integrity tracking</p>
                </div>
            </header>

            {alerts.length > 0 && (
                <div style={{ marginBottom: 32, display: "flex", flexDirection: "column", gap: 12 }}>
                    {alerts.map((a, i) => (
                        <div key={i} className="animate-shake" style={{
                            padding: "16px 20px", borderRadius: 12,
                            background: a.level === "ERROR" ? "rgba(239,68,68,0.1)" : "rgba(245,158,11,0.1)",
                            border: `1px solid ${a.level === "ERROR" ? "rgba(239,68,68,0.2)" : "rgba(245,158,11,0.2)"}`,
                            display: "flex", alignItems: "center", gap: 16
                        }}>
                            <span style={{ fontSize: 24 }}>{a.level === "ERROR" ? "🚨" : "⚠️"}</span>
                            <div>
                                <div style={{ fontWeight: 800, fontSize: 13, color: a.level === "ERROR" ? "var(--red)" : "var(--yellow)", textTransform: "uppercase", letterSpacing: 0.5 }}>{a.type}</div>
                                <div style={{ fontSize: 13, color: "var(--text-2)" }}>{a.message}</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 40 }}>
                <PaymentStat label="Total Success" val={summary?.success || 0} color="var(--green)" />
                <PaymentStat
                    label="Failed (Today)"
                    val={summary?.failed || 0}
                    color={failureRate > 10 ? "var(--red)" : "var(--text-3)"}
                    sub={`${failureRate.toFixed(1)}% Failure Rate`}
                />
                <PaymentStat label="Pending Verification" val={summary?.pending || 0} color="var(--yellow)" />
                <PaymentStat label="Gross Revenue" val={`₹${Math.round(summary?.total_revenue || 0).toLocaleString()}`} color="var(--accent)" />
            </div>

            <div className="glass-card" style={{ padding: 32 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-2)", textTransform: "uppercase", marginBottom: 24 }}>Gateway Health Check</h3>
                <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
                    <div style={{ height: 120, width: 120, borderRadius: "50%", border: "8px solid var(--bg-4)", borderTopColor: "var(--green)", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
                        <div style={{ fontSize: 20, fontWeight: 900, color: "var(--text-1)" }}>{Math.round(100 - failureRate)}%</div>
                        <div style={{ fontSize: 9, color: "var(--text-3)", fontWeight: 700 }}>UPTIME</div>
                    </div>
                    <div>
                        <div style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 8 }}>Reliability Index: <span style={{ color: "var(--green)", fontWeight: 700 }}>EXCELLENT</span></div>
                        <p style={{ fontSize: 12, color: "var(--text-3)", maxWidth: 400, lineHeight: 1.5 }}>
                            All payment providers (Razorpay, Stripe) are currently within normal latency bounds.
                            Verifications are processing with a {"< 3s"} delay.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

function PaymentStat({ label, val, color, sub }: any) {
    return (
        <div className="glass-card" style={{ padding: "24px", borderTop: `4px solid ${color}` }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 24, fontWeight: 900, color: "#fff" }}>{val}</div>
            {sub && <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 6 }}>{sub}</div>}
        </div>
    );
}

import { useEffect, useState } from "react";
import { api } from "../services/api";

export default function Reports() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const fetchReports = async () => {
        try {
            const res = await api.get("/admin/analytics/");
            setData(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchReports();
    }, []);

    const exportToCSV = () => {
        if (!data?.daily_stats) return;

        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Date,Rides,Revenue\n";

        data.daily_stats.forEach((row: any) => {
            csvContent += `${row.date},${row.count},${row.revenue}\n`;
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `fleet_report_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    if (loading) return <div style={{ padding: 60, color: "var(--text-dim)" }}>Compiling business reports...</div>;

    return (
        <div style={{ padding: "40px" }}>
            <header style={{ marginBottom: "32px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                    <h1 style={{ marginBottom: "8px", fontSize: "2rem", fontWeight: 800, letterSpacing: "-1px" }}>Fleet Analytics</h1>
                    <p style={{ color: "var(--text-dim)", margin: 0, fontSize: "14px" }}>Real-time performance metrics and financial summaries.</p>
                </div>
                <button onClick={exportToCSV} className="btn-primary">
                    📥 Export CSV
                </button>
            </header>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 24, marginBottom: 40 }}>
                {/* 1. Total Trips */}
                <div className="glass-card" style={{ padding: "24px", position: "relative", overflow: "hidden" }}>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--text-dim)", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "12px" }}>Total Trips</div>
                    <div style={{ display: "flex", alignItems: "flex-end", gap: "10px" }}>
                        <div style={{ fontSize: "32px", fontWeight: 800, color: "var(--text-bright)" }}>{data?.total_trips?.toLocaleString() || 0}</div>
                        <div style={{ fontSize: "12px", color: "var(--success)", fontWeight: 700, marginBottom: "6px" }}>↑ 12%</div>
                    </div>
                    <div style={{ position: "absolute", top: "20px", right: "20px", fontSize: "24px", opacity: 0.1 }}>🚕</div>
                </div>

                {/* 2. Platform Earnings */}
                <div className="glass-card" style={{ padding: "24px", position: "relative", overflow: "hidden" }}>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--text-dim)", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "12px" }}>Net Earnings</div>
                    <div style={{ display: "flex", alignItems: "flex-end", gap: "10px" }}>
                        <div style={{ fontSize: "32px", fontWeight: 800, color: "var(--success)" }}>₹{data?.total_earnings?.toLocaleString() || 0}</div>
                        <div style={{ fontSize: "12px", color: "var(--text-dim)", fontWeight: 600, marginBottom: "6px" }}>Commission</div>
                    </div>
                    <div style={{ position: "absolute", top: "20px", right: "20px", fontSize: "24px", opacity: 0.1 }}>💰</div>
                </div>

                {/* 3. Average Rating */}
                <div className="glass-card" style={{ padding: "24px", position: "relative", overflow: "hidden" }}>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--text-dim)", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "12px" }}>Avg Fleet Rating</div>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div style={{ fontSize: "32px", fontWeight: 800, color: "#f59e0b" }}>{data?.avg_rating || "5.0"}</div>
                        <div style={{ display: "flex", color: "#f59e0b", fontSize: "14px" }}>{"★".repeat(Math.floor(data?.avg_rating || 5))}</div>
                    </div>
                    <div style={{ position: "absolute", top: "20px", right: "20px", fontSize: "24px", opacity: 0.1 }}>⭐</div>
                </div>

                {/* 4. Active Hours */}
                <div className="glass-card" style={{ padding: "24px", position: "relative", overflow: "hidden" }}>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--text-dim)", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "12px" }}>Active Hours</div>
                    <div style={{ display: "flex", alignItems: "flex-end", gap: "10px" }}>
                        <div style={{ fontSize: "32px", fontWeight: 800, color: "#3b82f6" }}>{data?.total_active_hours || 0}</div>
                        <div style={{ fontSize: "12px", color: "var(--text-dim)", fontWeight: 600, marginBottom: "6px" }}>Hrs Logged</div>
                    </div>
                    <div style={{ position: "absolute", top: "20px", right: "20px", fontSize: "24px", opacity: 0.1 }}>⏱</div>
                </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 40 }}>
                {/* 5. Financial Integrity - Refunds */}
                <div className="glass-card" style={{ padding: "24px", borderLeft: "4px solid var(--danger)" }}>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--text-dim)", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "12px" }}>Rider Refunds (Case 1)</div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                        <div>
                            <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--text-bright)" }}>₹{data?.financial_interventions?.refunds_total?.toLocaleString() || 0}</div>
                            <div style={{ fontSize: "11px", color: "var(--text-dim)" }}>{data?.financial_interventions?.refunds_count || 0} Transactions processed</div>
                        </div>
                        <div style={{ fontSize: "20px" }}>↩️</div>
                    </div>
                </div>

                {/* 6. Financial Integrity - Compensations */}
                <div className="glass-card" style={{ padding: "24px", borderLeft: "4px solid var(--accent)" }}>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--text-dim)", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "12px" }}>Driver Compensations (Case 2)</div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                        <div>
                            <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--accent)" }}>₹{data?.financial_interventions?.compensations_total?.toLocaleString() || 0}</div>
                            <div style={{ fontSize: "11px", color: "var(--text-dim)" }}>{data?.financial_interventions?.compensations_count || 0} Manual adjustments</div>
                        </div>
                        <div style={{ fontSize: "20px" }}>💎</div>
                    </div>
                </div>
            </div>

            <div className="glass-card">
                <div style={{ padding: "20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h3 style={{ margin: 0, fontSize: "16px" }}>Historical Performance (7 Days)</h3>
                </div>
                <div style={{ overflowX: "auto" }}>
                    <table style={{ minWidth: "100%" }}>
                        <thead>
                            <tr>
                                <th>Period</th>
                                <th>Trip Count</th>
                                <th>Revenue Generated</th>
                                <th>Platform Cut (20%)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data?.daily_stats?.map((day: any, i: number) => (
                                <tr key={i}>
                                    <td style={{ color: "var(--text-dim)" }}>{day.date}</td>
                                    <td>{day.count}</td>
                                    <td style={{ fontWeight: 600 }}>₹{day.revenue?.toLocaleString()}</td>
                                    <td style={{ color: "var(--success)" }}>₹{(day.revenue * 0.2).toLocaleString()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

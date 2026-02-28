import { useEffect, useState } from "react";
import { api } from "../services/api";

interface LedgerRow {
    id: number;
    user_phone: string;
    ride_id: number | null;
    amount: string;
    type: string;
    reason: string;
    reference: string | null;
    created_at: string;
}

export default function Ledger() {
    const [rows, setRows] = useState<LedgerRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("ALL");

    useEffect(() => {
        api.get("/admin/payments/")
            .then(res => {
                setRows(res.data);
            })
            .catch(err => {
                console.error("Ledger API error", err);
            })
            .finally(() => setLoading(false));
    }, []);

    const filteredRows = rows.filter(r => {
        const reason = (r.reason || "").toUpperCase();
        if (filter === "ALL") return true;
        if (filter === "REFUND") {
            return reason === "REFUND" || reason.includes("REFUND") || reason.includes("CREDIT") || reason.includes("REVERSAL");
        }
        if (filter === "EARNINGS") {
            return reason === "DRIVER_EARNING" || reason.includes("COMPENSATION") || reason.includes("BONUS") || reason.includes("EARNING");
        }
        if (filter === "COMMISSION") {
            return reason === "PLATFORM_COMMISSION" || reason.includes("COMMISSION") || reason.includes("WAIVE");
        }
        return true;
    });

    if (loading) return <div style={{ padding: 60, color: "var(--text-dim)" }}>Loading transactions...</div>;

    return (
        <div style={{ padding: "40px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "32px" }}>
                <div>
                    <h1 style={{ marginBottom: "8px", fontSize: "2rem" }}>Earnings</h1>
                    <p style={{ color: "var(--text-dim)" }}>Financial adjustments and transaction history.</p>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                    {["ALL", "REFUND", "EARNINGS", "COMMISSION"].map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            style={{
                                padding: "6px 14px",
                                borderRadius: "6px",
                                border: "1px solid var(--border)",
                                background: filter === f ? "var(--accent)" : "var(--bg-card)",
                                color: filter === f ? "#fff" : "var(--text-2)",
                                fontSize: "11px",
                                fontWeight: 700,
                                cursor: "pointer",
                                transition: "all 0.2s"
                            }}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </div>

            <div className="glass-card" style={{ overflowX: "auto" }}>
                <table style={{ minWidth: "100%" }}>
                    <thead>
                        <tr>
                            <th style={{ width: "80px" }}>ID</th>
                            <th>Account</th>
                            <th>Amount</th>
                            <th>Type</th>
                            <th>Reason</th>
                            <th>Date</th>
                        </tr>
                    </thead>

                    <tbody>
                        {filteredRows.length === 0 ? (
                            <tr><td colSpan={6} style={{ padding: 48, textAlign: "center", color: "var(--text-dim)" }}>No transactions found.</td></tr>
                        ) : (
                            filteredRows.map(r => (
                                <tr key={r.id}>
                                    <td style={{ color: "var(--text-dim)" }}>#{r.id}</td>
                                    <td style={{ fontWeight: 500 }}>{r.user_phone}</td>
                                    <td style={{
                                        color: r.type === "CREDIT" ? "var(--success)" : "var(--text-bright)",
                                        fontWeight: 500,
                                        fontSize: '1rem'
                                    }}>
                                        {r.type === "CREDIT" ? "+" : "-"}₹{parseFloat(r.amount).toFixed(2)}
                                    </td>
                                    <td>
                                        <span className="badge" style={{
                                            background: r.type === "CREDIT" ? "rgba(39, 110, 241, 0.1)" : "rgba(255, 255, 255, 0.1)",
                                            color: r.type === "CREDIT" ? "var(--success)" : "var(--text-dim)",
                                            border: "none"
                                        }}>
                                            {r.type}
                                        </span>
                                    </td>
                                    <td style={{ color: "var(--text-main)" }}>{r.reason}</td>
                                    <td style={{ color: "var(--text-dim)", fontSize: '0.85rem' }}>{new Date(r.created_at).toLocaleString()}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

import { useEffect, useState } from "react";
import { api } from "../services/api";

interface AdminPayout {
    id: number;
    driver_phone: string;
    amount: string;
    status: string;
    failure_reason: string | null;
    reference: string | null;
    created_at: string;
}

export default function Payouts() {
    const [payouts, setPayouts] = useState<AdminPayout[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = () => {
        setLoading(true);
        api.get("/admin/payouts/")
            .then(res => setPayouts(res.data))
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleAction = async (id: number, action: "approve" | "reject" | "resolve") => {
        try {
            await api.post(`/admin/payout/${action}/${id}/`);
            fetchData();
        } catch (err: any) {
            alert(err.response?.data?.error || `Failed to ${action} payout`);
        }
    };

    if (loading) return <div style={{ padding: 60, color: "var(--text-dim)" }}>Loading payouts...</div>;

    const getStatusStyle = (status: string) => {
        switch (status) {
            case "PAID":
                return { bg: "#064E3B", text: "#34D399" };
            case "REQUESTED":
                return { bg: "#374151", text: "#E5E7EB" };
            case "FAILED":
            default:
                return { bg: "#7F1D1D", text: "#F87171" };
        }
    };


    return (
        <div style={{ padding: "40px" }}>
            <h1 style={{ marginBottom: "8px", fontSize: "2rem" }}>Payouts</h1>
            <p style={{ color: "var(--text-dim)", marginBottom: "32px" }}>Manage driver withdrawal requests.</p>

            <div className="glass-card" style={{ overflowX: "auto" }}>
                <table style={{ minWidth: "100%" }}>
                    <thead>
                        <tr>
                            <th style={{ width: "80px" }}>ID</th>
                            <th>Driver</th>
                            <th>Amount</th>
                            <th>Status</th>
                            <th>Requested</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {payouts.length === 0 ? (
                            <tr><td colSpan={6} style={{ padding: 48, textAlign: "center", color: "var(--text-dim)" }}>No active payouts found.</td></tr>
                        ) : (
                            payouts.map(p => (
                                <tr key={p.id}>
                                    <td style={{ color: "var(--text-dim)" }}>#{p.id}</td>
                                    <td style={{ fontWeight: 500 }}>
                                        {p.driver_phone}
                                        {p.failure_reason && (
                                            <div style={{ fontSize: '0.7rem', color: '#F87171', marginTop: 4 }}>
                                                Error: {p.failure_reason}
                                            </div>
                                        )}
                                    </td>
                                    <td style={{ fontWeight: 500 }}>₹{p.amount}</td>
                                    <td>
                                        <span className="badge" style={{
                                            background: getStatusStyle(p.status).bg,
                                            color: getStatusStyle(p.status).text,
                                            border: "none",
                                            fontWeight: 500,
                                            fontSize: "0.75rem",
                                            padding: "4px 8px",
                                            borderRadius: "4px"
                                        }}>
                                            {p.status}
                                        </span>
                                    </td>
                                    <td style={{ color: "var(--text-dim)", fontSize: '0.85rem' }}>{new Date(p.created_at).toLocaleString()}</td>
                                    <td>
                                        <div style={{ display: "flex", gap: "8px" }}>
                                            {p.status === "REQUESTED" && (
                                                <>
                                                    <button
                                                        onClick={() => handleAction(p.id, "approve")}
                                                        style={{ background: "#065F46", color: "#34D399", border: "none", padding: "6px 12px", fontSize: "0.8rem", borderRadius: "4px", cursor: "pointer" }}
                                                    >
                                                        Approve
                                                    </button>
                                                    <button
                                                        onClick={() => handleAction(p.id, "reject")}
                                                        style={{ background: "#7F1D1D", color: "#F87171", border: "none", padding: "6px 12px", fontSize: "0.8rem", borderRadius: "4px", cursor: "pointer" }}
                                                    >
                                                        Reject
                                                    </button>
                                                </>
                                            )}
                                            {p.status === "FAILED" && (
                                                <>
                                                    <button
                                                        onClick={() => handleAction(p.id, "approve")}
                                                        style={{ background: "#272e3a", color: "#60a5fa", border: "1px solid #3b82f6", padding: "6px 12px", fontSize: "0.8rem", borderRadius: "4px", cursor: "pointer" }}
                                                    >
                                                        Retry
                                                    </button>
                                                    <button
                                                        onClick={() => handleAction(p.id, "resolve")}
                                                        style={{ background: "#374151", color: "#E5E7EB", border: "none", padding: "6px 12px", fontSize: "0.8rem", borderRadius: "4px", cursor: "pointer" }}
                                                    >
                                                        Force Mark Paid
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}


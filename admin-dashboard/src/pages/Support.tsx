import { useEffect, useState } from "react";
import { api } from "../services/api";

interface Ticket {
    id: number;
    ride_id: number;
    user_name: string;
    reason: string;
    description: string;
    created_at: string;
}

interface Emergency {
    id: number;
    ride_id: number;
    user_name: string;
    lat: number;
    lng: number;
    created_at: string;
}

export default function Support() {
    const [tickets, setTickets] = useState<Ticket[]>([]);
    const [emergencies, setEmergencies] = useState<Emergency[]>([]);
    const [loading, setLoading] = useState(true);
    const [processingId, setProcessingId] = useState<number | null>(null);

    const fetchSupport = async () => {
        try {
            const res = await api.get("/admin/tickets/");
            setTickets(res.data.tickets);
            setEmergencies(res.data.emergencies);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSupport();
        const interval = setInterval(fetchSupport, 10000);
        return () => clearInterval(interval);
    }, []);

    const handleResolveTicket = async (ticketId: number) => {
        const note = prompt("Enter resolution notes:", "Problem resolved with user.");
        if (note === null) return;

        const refund = prompt("Enter refund amount (optional):", "0");
        const refundAmount = refund ? parseFloat(refund) : 0;

        setProcessingId(ticketId);
        try {
            await api.post(`/supports/tickets/${ticketId}/resolve/`, {
                note,
                refund_amount: refundAmount > 0 ? refundAmount : undefined
            });
            alert("Ticket resolved successfully.");
            fetchSupport();
        } catch (err: any) {
            alert(err.response?.data?.error || "Resolution failed.");
        } finally {
            setProcessingId(null);
        }
    };

    const handleResolveEmergency = async (emergencyId: number) => {
        const note = prompt("Enter dispatch resolution notes:", "Emergency team dispatched and situation controlled.");
        if (note === null) return;

        setProcessingId(emergencyId);
        try {
            await api.post(`/supports/emergencies/${emergencyId}/resolve/`, {
                note,
                status: "RESOLVED"
            });
            alert("Emergency resolved and closed.");
            fetchSupport();
        } catch (err: any) {
            alert(err.response?.data?.error || "Failed to resolve emergency.");
        } finally {
            setProcessingId(null);
        }
    };

    if (loading) return <div style={{ padding: 60, color: "var(--text-dim)" }}>Connecting to support lines...</div>;

    return (
        <div style={{ padding: "40px" }}>
            <header style={{ marginBottom: "32px" }}>
                <h1 style={{ marginBottom: "8px", fontSize: "2rem" }}>Support & Safety</h1>
                <p style={{ color: "var(--text-dim)", margin: 0 }}>Monitor active emergencies and resolve rider/driver tickets.</p>
            </header>

            {/* Emergencies - HIGHEST PRIORITY */}
            <section style={{ marginBottom: "48px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
                    <div className="live-dot" style={{ background: "var(--danger)" }} />
                    <h2 style={{ fontSize: "1.25rem", color: "var(--danger)", margin: 0 }}>Active Emergencies</h2>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))", gap: 24 }}>
                    {emergencies.length === 0 ? (
                        <div className="glass-card" style={{ padding: "40px", color: "var(--text-dim)", gridColumn: "1 / -1" }}>
                            No active emergency signals reported.
                        </div>
                    ) : (
                        emergencies.map(e => (
                            <div key={e.id} className="glass-card" style={{ borderColor: e.id === processingId ? "var(--accent)" : "rgba(239, 68, 68, 0.3)", background: "rgba(239, 68, 68, 0.02)" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                                    <span style={{ fontWeight: 700, color: "var(--text-bright)" }}>S.O.S • Ride #{e.ride_id}</span>
                                    <span style={{ fontSize: "11px", color: "var(--danger)" }}>{new Date(e.created_at).toLocaleTimeString()}</span>
                                </div>
                                <div style={{ fontSize: "14px", color: "var(--text-2)", marginBottom: 16 }}>
                                    Reported by: <strong>{e.user_name}</strong>
                                </div>
                                <div style={{ padding: "12px", background: "var(--bg-3)", borderRadius: 8, fontSize: "12px", color: "var(--text-dim)", fontFamily: "monospace" }}>
                                    Location: {e.lat.toFixed(5)}, {e.lng.toFixed(5)}
                                </div>
                                <button
                                    className="btn-primary"
                                    style={{ width: "100%", marginTop: 16, background: "var(--danger)" }}
                                    onClick={() => handleResolveEmergency(e.id)}
                                    disabled={processingId === e.id}
                                >
                                    {processingId === e.id ? "Processing..." : "Dispatch Response & Close"}
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </section>

            {/* Tickets */}
            <section>
                <h2 style={{ fontSize: "1.25rem", color: "var(--text-bright)", marginBottom: 20 }}>Open Support Tickets</h2>
                <div className="glass-card" style={{ overflowX: "auto" }}>
                    <table style={{ minWidth: "100%" }}>
                        <thead>
                            <tr>
                                <th>Ride</th>
                                <th>User</th>
                                <th>Reason</th>
                                <th>Reported</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tickets.length === 0 ? (
                                <tr><td colSpan={5} style={{ padding: 40, textAlign: "center", color: "var(--text-dim)" }}>All tickets resolved.</td></tr>
                            ) : (
                                tickets.map(t => (
                                    <tr key={t.id}>
                                        <td style={{ fontWeight: 600 }}>#{t.ride_id}</td>
                                        <td>{t.user_name}</td>
                                        <td>
                                            <div style={{ fontSize: "14px", fontWeight: 600 }}>{t.reason}</div>
                                            <div style={{ fontSize: "12px", color: "var(--text-dim)" }}>{t.description}</div>
                                        </td>
                                        <td style={{ fontSize: "12px", color: "var(--text-dim)" }}>{new Date(t.created_at).toLocaleString()}</td>
                                        <td>
                                            <button
                                                className="btn-ghost"
                                                style={{ fontSize: "12px", color: "var(--success)" }}
                                                onClick={() => handleResolveTicket(t.id)}
                                                disabled={processingId === t.id}
                                            >
                                                {processingId === t.id ? "..." : "Resolve"}
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
}

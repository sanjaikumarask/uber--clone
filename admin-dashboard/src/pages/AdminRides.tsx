import { useEffect, useState } from "react";
import { api } from "../services/api";

interface AdminRide {
    id: number;
    rider: string;
    driver: string | null;
    status: string;
    created_at: string;
    fare: string | null;
}

export default function AdminRides() {
    const [rides, setRides] = useState<AdminRide[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchRides = () => {
        setLoading(true);
        api.get("/rides/admin/rides/")
            .then(res => {
                const data = Array.isArray(res.data) ? res.data : res.data.results || [];
                setRides(data);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchRides();
    }, []);

    const handleCancel = async (rideId: number) => {
        if (!confirm(`Are you sure you want to cancel Ride #${rideId}?`)) return;
        try {
            await api.post("/rides/admin/rides/actions/", {
                ride_id: rideId,
                action: "cancel"
            });
            alert("Ride cancelled");
            fetchRides(); // Refresh list
        } catch (err) {
            alert("Failed to cancel ride");
        }
    };

    if (loading) return <div style={{ padding: 40, color: "#888" }}>Loading rides…</div>;

    return (
        <div style={{ padding: "40px 60px" }}>
            <h1 style={{ marginBottom: "30px", fontSize: "2rem" }}>Rides</h1>

            <div style={{ overflowX: "auto", borderRadius: "8px", border: "1px solid #333" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", background: "#1e1e1e" }}>
                    <thead>
                        <tr style={{ background: "#000", textAlign: "left" }}>
                            <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>ID</th>
                            <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Rider</th>
                            <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Driver</th>
                            <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Status</th>
                            <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Fare</th>
                            <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Date</th>
                            <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rides.length === 0 ? (
                            <tr><td colSpan={7} style={{ padding: 24, textAlign: "center", color: "#666" }}>No rides found</td></tr>
                        ) : (
                            rides.map(r => (
                                <tr key={r.id} style={{ borderBottom: "1px solid #333" }}>
                                    <td style={{ padding: "16px", color: "#fff" }}>{r.id}</td>
                                    <td style={{ padding: "16px", color: "#fff" }}>{r.rider}</td>
                                    <td style={{ padding: "16px", color: "#fff" }}>{r.driver || "-"}</td>
                                    <td style={{ padding: "16px" }}>
                                        <span style={{
                                            padding: "4px 8px", borderRadius: "4px", fontSize: "0.75rem",
                                            background: r.status === "COMPLETED" ? "#2ecc7120" : "#333",
                                            color: r.status === "COMPLETED" ? "#2ecc71" : "#ccc"
                                        }}>
                                            {r.status}
                                        </span>
                                    </td>
                                    <td style={{ padding: "16px", color: "#fff" }}>{r.fare ? `₹${r.fare}` : "-"}</td>
                                    <td style={{ padding: "16px", color: "#aaa" }}>{new Date(r.created_at).toLocaleString()}</td>
                                    <td style={{ padding: "16px" }}>
                                        {["SEARCHING", "OFFERED", "ASSIGNED", "ARRIVED", "ONGOING"].includes(r.status) && (
                                            <button
                                                onClick={() => handleCancel(r.id)}
                                                style={{
                                                    background: "transparent", color: "#e74c3c", border: "1px solid #e74c3c",
                                                    padding: "6px 12px", borderRadius: "4px", cursor: "pointer"
                                                }}
                                            >
                                                Cancel
                                            </button>
                                        )}
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

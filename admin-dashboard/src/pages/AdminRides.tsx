import { useEffect, useState } from "react";
import { api } from "../services/api";
import RideDetailPanel from "../components/RideDetailPanel";
import ResolutionModal from "../components/ResolutionModal";

interface AdminRide {
    id: number;
    rider_phone: string;
    rider_name: string;
    driver_phone: string | null;
    status: string;
    payment_status: string | null;
    base_fare: string;
    final_fare: string | null;
    created_at: string;
}

export default function AdminRides() {
    const [rides, setRides] = useState<AdminRide[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedRideId, setSelectedRideId] = useState<number | null>(null);
    const [resolutionRide, setResolutionRide] = useState<any | null>(null);

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

    const handleResolutionSubmit = async (data: any) => {
        try {
            await api.post("/admin/resolve-ride/", data);
            alert("Ride resolved successfully.");
            setResolutionRide(null);
            fetchRides();
        } catch (err: any) {
            alert(err.response?.data?.error || "Resolution failed");
        }
    };

    if (loading) return <div style={{ padding: 60, color: "var(--text-dim)" }}>Loading trip data...</div>;

    return (
        <div style={{ padding: "40px" }}>
            <h1 style={{ marginBottom: "8px", fontSize: "2rem" }}>Trips</h1>
            <p style={{ color: "var(--text-dim)", marginBottom: "32px" }}>Monitor real-time and past trip activity.</p>

            <div className="glass-card" style={{ overflowX: "auto" }}>
                <table style={{ minWidth: "100%" }}>
                    <thead>
                        <tr>
                            <th style={{ width: "80px" }}>ID</th>
                            <th>Rider</th>
                            <th>Driver</th>
                            <th>Status</th>
                            <th>Fare</th>
                            <th>Requested</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rides.length === 0 ? (
                            <tr><td colSpan={7} style={{ padding: 48, textAlign: "center", color: "var(--text-dim)" }}>No active trips found.</td></tr>
                        ) : (
                            rides.map(r => (
                                <tr
                                    key={r.id}
                                    onClick={() => setSelectedRideId(r.id)}
                                    style={{ cursor: "pointer" }}
                                >
                                    <td style={{ color: "var(--text-bright)", fontWeight: 500 }}>#{r.id}</td>
                                    <td>{r.rider_name || r.rider_phone}</td>
                                    <td>
                                        {r.driver_phone ? (
                                            <span style={{ fontWeight: 500 }}>{r.driver_phone}</span>
                                        ) : (
                                            <span style={{ color: "var(--text-dim)", fontStyle: "italic" }}>Searching...</span>
                                        )}
                                    </td>
                                    <td>
                                        <span className="badge" style={{
                                            background: r.status === "COMPLETED" ? "#1F2937" : "#374151",
                                            color: r.status === "COMPLETED" ? "var(--success)" : "var(--text-bright)",
                                            border: "none"
                                        }}>
                                            {r.status}
                                        </span>
                                    </td>
                                    <td style={{ fontWeight: 500 }}>{r.final_fare ? `₹${r.final_fare}` : r.base_fare ? `₹${r.base_fare}` : "—"}</td>
                                    <td style={{ color: "var(--text-dim)", fontSize: '0.85rem' }}>{new Date(r.created_at).toLocaleString()}</td>
                                    <td>
                                        {["SEARCHING", "OFFERED", "ASSIGNED", "ARRIVED", "ONGOING", "COMPLETED"].includes(r.status) && (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setResolutionRide(r);
                                                }}
                                                style={{
                                                    background: "transparent",
                                                    color: "var(--accent)",
                                                    border: "1px solid var(--border)",
                                                    padding: "6px 12px",
                                                    fontSize: "0.8rem",
                                                    cursor: "pointer"
                                                }}
                                            >
                                                ⚠️ Resolve
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Ride Detail Panel */}
            {selectedRideId && (
                <RideDetailPanel
                    rideId={selectedRideId}
                    onClose={() => setSelectedRideId(null)}
                />
            )}

            {/* Resolution Modal */}
            {resolutionRide && (
                <ResolutionModal
                    ride={resolutionRide}
                    onClose={() => setResolutionRide(null)}
                    onSubmit={handleResolutionSubmit}
                />
            )}
        </div>
    );
}

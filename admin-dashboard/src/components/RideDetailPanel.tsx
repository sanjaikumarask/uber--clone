/// <reference types="vite/client" />
import React, { useState, useMemo, useEffect } from "react";
import { api } from "../services/api";
import { GoogleMap, useJsApiLoader, Polyline, Marker } from "@react-google-maps/api";
import ResolutionModal from "./ResolutionModal";

interface RideDetail {
    id: number;
    rider: {
        phone: string;
        name?: string;
    };
    driver: {
        phone: string;
        name?: string;
        vehicle_model?: string;
        vehicle_number?: string;
    } | null;
    status: string;
    pickup_address: string;
    drop_address: string;
    pickup_lat: number;
    pickup_lng: number;
    drop_lat: number;
    drop_lng: number;
    planned_distance_km: number;
    actual_distance_km: number;
    base_fare: string;
    final_fare: string | null;
    otp_code: string | null;
    created_at: string;
    updated_at: string;
    otp_verified_at: string | null;
    arrived_at: string | null;
    completed_at: string | null;
    cancelled_at: string | null;
    actual_route_polyline: string | null;
    planned_route_polyline: string | null;
    payment_status?: string | null;
}

interface Props {
    rideId: number;
    onClose: () => void;
}

const LIBRARIES: ("geometry" | "marker")[] = ["geometry", "marker"];

export default function RideDetailPanel({ rideId, onClose }: Props) {
    const [ride, setRide] = useState<RideDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [showResolution, setShowResolution] = useState(false);
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;

    const { isLoaded } = useJsApiLoader({
        googleMapsApiKey: apiKey,
        libraries: LIBRARIES
    });

    useEffect(() => {
        api.get(`/rides/${rideId}/`)
            .then(res => setRide(res.data))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [rideId]);

    const plannedPath = useMemo(() => {
        if (!isLoaded || !ride?.planned_route_polyline) return [];
        try {
            return window.google.maps.geometry.encoding.decodePath(ride.planned_route_polyline!);
        } catch (e) {
            return [];
        }
    }, [isLoaded, ride]);

    const actualPath = useMemo(() => {
        if (!isLoaded || !ride?.actual_route_polyline) return [];
        try {
            return window.google.maps.geometry.encoding.decodePath(ride.actual_route_polyline!);
        } catch (e) {
            return [];
        }
    }, [isLoaded, ride]);

    if (loading) {
        return (
            <div style={styles.overlay}>
                <div style={styles.panel}>
                    <div style={{ padding: 60, textAlign: "center", color: "#94a3b8" }}>
                        <div className="ds-spin" style={{ fontSize: 32, marginBottom: 16 }}>🌀</div>
                        <p style={{ fontWeight: 600 }}>Deciphering Trip Data...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!ride) {
        return (
            <div style={styles.overlay}>
                <div style={styles.panel}>
                    <div style={{ padding: 60, textAlign: "center" }}>
                        <p style={{ color: "#ef4444", fontWeight: 700 }}>Record not found for Trip #{rideId}</p>
                        <button onClick={onClose} style={{ ...styles.primaryButton, marginTop: 20 }}>Close</button>
                    </div>
                </div>
            </div>
        );
    }

    const getStatusColor = (status: string) => {
        const colors: Record<string, string> = {
            SEARCHING: "#f59e0b",
            OFFERED: "#3b82f6",
            ASSIGNED: "#8b5cf6",
            ARRIVED: "#10b981",
            ONGOING: "#06b6d4",
            COMPLETED: "#22c55e",
            CANCELLED: "#ef4444",
        };
        return colors[status] || "#6b7280";
    };

    const handleAction = async (action: "reassign" | "refund" | "cancel" | "compensate_driver", extraData: any = {}) => {
        try {
            const res = await api.post("/rides/admin/rides/actions/", {
                ride_id: rideId,
                action,
                ...extraData
            });
            if (res.data.success) {
                alert(`${action.replace("_", " ").toUpperCase()} successful`);
                const updated = await api.get(`/rides/${rideId}/`);
                setRide(updated.data);
                if (action === "cancel") {
                    onClose(); // Close on cancellation
                }
            }
        } catch (err: any) {
            alert(err.response?.data?.error || `Failed to ${action}`);
        }
    };

    const handleResolutionSubmit = async (data: any) => {
        try {
            const res = await api.post("/admin/resolve-ride/", data);
            if (res.data.success) {
                alert("Ride resolved successfully. Audit logs updated.");
                setShowResolution(false);
                const updated = await api.get(`/rides/${rideId}/`);
                setRide(updated.data);
                if (data.action === "CANCEL") {
                    onClose();
                }
            }
        } catch (err: any) {
            alert(err.response?.data?.error || "Resolution failed");
        }
    };

    const handleCompensateOnly = async () => {
        if (!ride?.driver) return;
        const amount = prompt("Enter amount to PAY the driver directly:", "100");
        if (!amount || isNaN(parseFloat(amount))) return;

        const reason = prompt("Reason for payment:", "Manual adjustment / Compensation");
        if (!reason) return;

        await handleAction("compensate_driver", {
            amount: parseFloat(amount),
            reason
        });
    };

    // Timeline events
    const rawEvents = [
        { label: "Request Placed", time: ride.created_at, icon: "📩", color: "#3b82f6" },
        { label: "Driver Arrived", time: ride.arrived_at, icon: "📍", color: "#10b981" },
        { label: "Ride Started", time: ride.otp_verified_at, icon: "🚀", color: "#06b6d4" },
        { label: "Ride Finished", time: ride.completed_at, icon: "✅", color: "#22c55e" },
        { label: "Cancelled", time: ride.cancelled_at, icon: "🚫", color: "#ef4444" },
    ];

    const events = rawEvents
        .filter((e): e is { label: string; time: string; icon: string; color: string } => !!e.time)
        .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

    return (
        <div style={{ position: "fixed", inset: 0, zIndex: 1000, display: "flex", justifyContent: "flex-end" }}>
            <button
                style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.4)", backdropFilter: "blur(4px)", border: "none", cursor: "default", padding: 0, width: "100%", height: "100%" }}
                onClick={onClose}
                aria-label="Close panel"
            />
            <div
                role="dialog"
                aria-modal="true"
                style={{ ...styles.panel, position: "relative" }}
            >
                {/* Header */}
                <div style={styles.header}>
                    <div>
                        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
                            <h2 style={styles.title}>Trip #{ride.id}</h2>
                            <span
                                style={{
                                    ...styles.statusBadge,
                                    background: `${getStatusColor(ride.status)}15`,
                                    color: getStatusColor(ride.status),
                                    border: `1px solid ${getStatusColor(ride.status)}33`,
                                }}
                            >
                                {ride.status}
                            </span>
                        </div>
                        <div style={{ color: "#475569", fontSize: 11, fontWeight: 700, letterSpacing: 0.5 }}>
                            {new Date(ride.created_at).toLocaleDateString()} • {new Date(ride.created_at).toLocaleTimeString()}
                        </div>
                    </div>
                    <button onClick={onClose} style={styles.closeButton}>✕</button>
                </div>

                <div style={styles.content}>
                    <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 32 }}>
                        {/* LEFT COLUMN: Map & Participants */}
                        <div>
                            {/* Visual Route */}
                            <div style={{ ...styles.glassContainer, height: 360, padding: 0, overflow: "hidden", marginBottom: 24, background: "#000" }}>
                                {isLoaded ? (
                                    <GoogleMap
                                        mapContainerStyle={{ width: "100%", height: "100%" }}
                                        center={{ lat: ride.pickup_lat, lng: ride.pickup_lng }}
                                        zoom={14}
                                        options={{
                                            styles: [
                                                { elementType: "geometry", stylers: [{ color: "#212121" }] },
                                                { elementType: "labels.icon", stylers: [{ visibility: "off" }] },
                                                { elementType: "labels.text.fill", stylers: [{ color: "#757575" }] },
                                                { elementType: "labels.text.stroke", stylers: [{ color: "#212121" }] },
                                                { featureType: "administrative", elementType: "geometry", stylers: [{ color: "#757575" }] },
                                                { featureType: "poi", elementType: "geometry", stylers: [{ color: "#181818" }] },
                                                { featureType: "road", elementType: "geometry.fill", stylers: [{ color: "#2c2c2c" }] },
                                                { featureType: "road", elementType: "labels.text.fill", stylers: [{ color: "#8a8a8a" }] },
                                                { featureType: "water", elementType: "geometry", stylers: [{ color: "#000000" }] }
                                            ],
                                            disableDefaultUI: true,
                                            zoomControl: true,
                                        }}
                                    >
                                        <Marker
                                            position={{ lat: ride.pickup_lat, lng: ride.pickup_lng }}
                                            icon={{
                                                url: "https://maps.google.com/mapfiles/ms/icons/green-dot.png",
                                                scaledSize: { width: 40, height: 40 } as any
                                            }}
                                        />
                                        <Marker
                                            position={{ lat: ride.drop_lat, lng: ride.drop_lng }}
                                            icon={{
                                                url: "https://maps.google.com/mapfiles/ms/icons/red-dot.png",
                                                scaledSize: { width: 40, height: 40 } as any
                                            }}
                                        />

                                        {/* Planned Route (Dashed or Dim) */}
                                        {plannedPath.length > 0 && (
                                            <Polyline
                                                path={plannedPath}
                                                options={{ strokeColor: "#ffffff", strokeOpacity: 0.2, strokeWeight: 4 }}
                                            />
                                        )}

                                        {/* Actual Route (Solid Blue) */}
                                        {actualPath.length > 0 && (
                                            <Polyline
                                                path={actualPath}
                                                options={{ strokeColor: "#3b82f6", strokeOpacity: 1, strokeWeight: 5 }}
                                            />
                                        )}
                                    </GoogleMap>
                                ) : (
                                    <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "#000", color: "#334155" }}>
                                        Loading Satellite Engine...
                                    </div>
                                )}
                            </div>

                            {/* Participants */}
                            <div style={styles.infoGrid}>
                                <div style={styles.infoCard}>
                                    <div style={styles.infoLabel}>👤 RIDER</div>
                                    <div style={styles.infoValue}>{ride.rider.name || "Customer"}</div>
                                    <div style={styles.infoSubtext}>📞 {ride.rider.phone}</div>
                                </div>
                                <div style={styles.infoCard}>
                                    <div style={styles.infoLabel}>🚗 DRIVER</div>
                                    {ride.driver ? (
                                        <>
                                            <div style={styles.infoValue}>{ride.driver.name}</div>
                                            <div style={styles.infoSubtext}>
                                                {ride.driver.vehicle_model} • {ride.driver.vehicle_number}
                                            </div>
                                        </>
                                    ) : (
                                        <div style={{ ...styles.infoValue, color: "#475569", fontStyle: "italic" }}>Awaiting Assignment</div>
                                    )}
                                </div>
                            </div>

                            {/* Addresses */}
                            <div style={{ marginTop: 24 }}>
                                <div style={styles.addressLine}>
                                    <div style={{ color: "#22c55e", fontSize: 16 }}>●</div>
                                    <div>
                                        <div style={{ fontSize: 10, fontWeight: 800, color: "#475569", textTransform: "uppercase" }}>PICKUP</div>
                                        <div style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9" }}>{ride.pickup_address}</div>
                                    </div>
                                </div>
                                <div style={{ height: 24, borderLeft: "2px solid #1a1a1a", marginLeft: 6, margin: "4px 0 4px 6px" }} />
                                <div style={styles.addressLine}>
                                    <div style={{ color: "#ef4444", fontSize: 16 }}>●</div>
                                    <div>
                                        <div style={{ fontSize: 10, fontWeight: 800, color: "#475569", textTransform: "uppercase" }}>DROPOFF</div>
                                        <div style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9" }}>{ride.drop_address}</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* RIGHT COLUMN: Timeline & Metrics */}
                        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
                            {/* Combined Metrics & Info */}
                            <div style={styles.glassContainer}>
                                <div style={{ fontSize: 10, fontWeight: 800, color: "#475569", marginBottom: 20, letterSpacing: 1 }}>TRIP OVERVIEW</div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
                                    <div>
                                        <div style={{ fontSize: 9, color: "#475569", fontWeight: 800, marginBottom: 4 }}>TOTAL DISTANCE</div>
                                        <div style={{ fontSize: 24, fontWeight: 800, color: "#f1f5f9" }}>{ride.actual_distance_km || ride.planned_distance_km} <span style={{ fontSize: 12, color: "#475569" }}>km</span></div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: 9, color: "#475569", fontWeight: 800, marginBottom: 4 }}>TOTAL FARE</div>
                                        <div style={{ fontSize: 24, fontWeight: 800, color: "#22c55e" }}>₹{ride.final_fare || ride.base_fare}</div>
                                    </div>
                                </div>

                                <div style={{ marginTop: 20, paddingTop: 20, borderTop: "1px solid #1a1a1a" }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                                        <span style={{ fontSize: 11, color: "#475569", fontWeight: 600 }}>PAYMENT</span>
                                        <span style={{ fontSize: 11, color: ride.payment_status === "CAPTURED" ? "#22c55e" : "#f59e0b", fontWeight: 800 }}>{ride.payment_status || "PENDING"}</span>
                                    </div>
                                    {ride.otp_code && (
                                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                                            <span style={{ fontSize: 11, color: "#475569", fontWeight: 600 }}>VERIFICATION OTP</span>
                                            <span style={{ fontSize: 11, color: "#fff", fontWeight: 800, fontFamily: "monospace", letterSpacing: 1 }}>{ride.otp_code}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Timeline */}
                            <div style={styles.glassContainer}>
                                <div style={{ fontSize: 10, fontWeight: 800, color: "#475569", marginBottom: 20, letterSpacing: 1 }}>AUDIT TRAIL</div>
                                <div style={{ display: "flex", flexDirection: "column" }}>
                                    {events.map((ev, i) => (
                                        <div key={ev.label} style={{ display: "flex", gap: 20, position: "relative" }}>
                                            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                                                <div style={{
                                                    width: 8,
                                                    height: 8,
                                                    borderRadius: "50%",
                                                    background: ev.color,
                                                    boxShadow: `0 0 10px ${ev.color}`,
                                                    marginTop: 10,
                                                    zIndex: 2
                                                }} />
                                                {i < events.length - 1 && <div style={{ width: 1, flex: 1, background: "#1a1a1a" }} />}
                                            </div>
                                            <div style={{ paddingBottom: 24 }}>
                                                <div style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9", marginBottom: 2 }}>{ev.label}</div>
                                                <div style={{ fontSize: 10, color: "#475569", fontWeight: 600 }}>
                                                    {new Date(ev.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Actions */}
                            <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 12 }}>
                                {["ASSIGNED", "ARRIVED", "OFFERED"].includes(ride.status) && (
                                    <button
                                        onClick={() => handleAction("reassign")}
                                        style={{ width: "100%", padding: "14px", borderRadius: 12, background: "rgba(139,92,246,0.1)", border: "1px solid rgba(139,92,246,0.3)", color: "#8b5cf6", fontSize: 11, fontWeight: 800, cursor: "pointer", transition: "all 0.2s" }}
                                    >
                                        🔄 REASSIGN DRIVER
                                    </button>
                                )}

                                {["ASSIGNED", "ARRIVED", "ONGOING", "OFFERED", "SEARCHING"].includes(ride.status) && (
                                    <button
                                        onClick={() => setShowResolution(true)}
                                        style={{ width: "100%", padding: "14px", borderRadius: 12, background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#ef4444", fontSize: 11, fontWeight: 800, cursor: "pointer", transition: "all 0.2s" }}
                                    >
                                        ⚠️ RESOLVE ISSUE (SYSTEM)
                                    </button>
                                )}

                                {ride.driver && ride.status !== "CANCELLED" && (
                                    <button
                                        onClick={handleCompensateOnly}
                                        style={{ width: "100%", padding: "14px", borderRadius: 12, background: "rgba(59, 130, 246, 0.1)", border: "1px solid rgba(59, 130, 246, 0.3)", color: "#3b82f6", fontSize: 11, fontWeight: 800, cursor: "pointer", transition: "all 0.2s" }}
                                    >
                                        💰 COMPENSATE DRIVER (CASE 2)
                                    </button>
                                )}

                                {ride.payment_status === "CAPTURED" && (
                                    <button
                                        onClick={() => handleAction("refund")}
                                        style={{ width: "100%", padding: "14px", borderRadius: 12, background: "rgba(34, 197, 94, 0.1)", border: "1px solid rgba(34, 197, 94, 0.3)", color: "#22c55e", fontSize: 11, fontWeight: 800, cursor: "pointer", transition: "all 0.2s" }}
                                    >
                                        💸 ISSUE FULL REFUND (CASE 1)
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div style={styles.footer}>
                    <button onClick={onClose} style={styles.primaryButton}>CLOSE CASE</button>
                </div>
            </div>

            {showResolution && (
                <ResolutionModal
                    ride={ride}
                    onClose={() => setShowResolution(false)}
                    onSubmit={handleResolutionSubmit}
                />
            )}
        </div>
    );
}

const styles: Record<string, React.CSSProperties> = {
    overlay: {
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.9)",
        backdropFilter: "blur(10px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 5000,
    },
    panel: {
        background: "#050505",
        border: "1px solid #111",
        borderRadius: "28px",
        width: "95%",
        maxWidth: "1000px",
        maxHeight: "92vh",
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 0 100px rgba(0,0,0,1)",
        overflow: "hidden",
    },
    header: {
        padding: "32px 40px",
        borderBottom: "1px solid #111",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
    },
    title: {
        margin: 0,
        fontSize: "26px",
        fontWeight: "900",
        color: "#fff",
        letterSpacing: "-1px",
    },
    statusBadge: {
        padding: "4px 14px",
        borderRadius: "30px",
        fontSize: "10px",
        fontWeight: "900",
        textTransform: "uppercase",
        letterSpacing: "0.5px",
    },
    closeButton: {
        background: "#111",
        border: "none",
        color: "#555",
        width: "40px",
        height: "40px",
        borderRadius: "14px",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "18px",
        transition: "all 0.2s",
    },
    content: {
        flex: 1,
        overflowY: "auto",
        padding: "40px",
    },
    glassContainer: {
        background: "#080808",
        border: "1px solid #111",
        borderRadius: "20px",
        padding: "24px",
    },
    infoGrid: {
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "20px",
    },
    infoCard: {
        background: "#080808",
        padding: "20px",
        borderRadius: "18px",
        border: "1px solid #111",
    },
    infoLabel: {
        fontSize: "9px",
        color: "#444",
        fontWeight: "900",
        letterSpacing: "1px",
        marginBottom: "10px",
    },
    infoValue: {
        fontSize: "16px",
        fontWeight: "800",
        color: "#fff",
    },
    infoSubtext: {
        fontSize: "12px",
        color: "#666",
        marginTop: "6px",
        fontWeight: "500",
    },
    addressLine: {
        display: "flex",
        gap: "14px",
        alignItems: "center",
    },
    footer: {
        padding: "24px 40px",
        borderTop: "1px solid #111",
        display: "flex",
        justifyContent: "flex-end",
    },
    primaryButton: {
        background: "#fff",
        color: "#000",
        border: "none",
        padding: "14px 32px",
        borderRadius: "14px",
        fontSize: "13px",
        fontWeight: "900",
        cursor: "pointer",
        transition: "all 0.2s",
    },
};

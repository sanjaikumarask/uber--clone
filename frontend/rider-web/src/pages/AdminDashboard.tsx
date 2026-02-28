import React, { useEffect, useState, type CSSProperties } from "react";
import { GoogleMap, useJsApiLoader, Polyline } from "@react-google-maps/api";
import { useNavigate } from "react-router-dom";
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer
} from 'recharts';

const LIBRARIES: ("marker" | "geometry" | "places")[] = ["marker", "geometry", "places"];

type DashboardView = "overview" | "live-map" | "fare-config" | "payments" | "analytics" | "alerts" | "drivers" | "tickets";

interface DriverMapData {
    driver_id: number;
    name: string;
    lat: number;
    lng: number;
    status: string;
    ride?: any;
    ts: number;
}

interface RiderMapData {
    rider_id: number;
    ride_id: number;
    rider_name: string;
    lat: number;
    lng: number;
    status: string;
    ride?: any;
    ts: number;
}

export default function AdminDashboard() {
    const navigate = useNavigate();
    const apiKey = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string) || "";
    const { isLoaded, loadError } = useJsApiLoader({
        googleMapsApiKey: apiKey,
        libraries: LIBRARIES,
        version: "beta",
    });

    const [view, setView] = useState<DashboardView>("overview");
    const [overview, setOverview] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const apiFetch = async (path: string, options: any = {}) => {
        const token = localStorage.getItem("access");
        if (!token) { navigate("/"); throw new Error("No token"); }

        const res = await fetch(`${window.location.protocol}//${window.location.host}/api${path}`, {
            ...options,
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json",
                ...(options.headers || {})
            }
        });
        if (res.status === 401) { navigate("/"); return; }
        return res.json();
    };

    useEffect(() => {
        const load = async () => {
            try {
                const data = await apiFetch("/admin/overview/");
                setOverview(data);
                setLoading(false);
            } catch (e) {
                console.error("Overview error", e);
            }
        };
        load();
        const interval = setInterval(load, 30000);
        return () => clearInterval(interval);
    }, []);

    const sidebarItems = [
        { id: "overview", label: "Overview", icon: "📊" },
        { id: "live-map", label: "Live Map", icon: "🗺️" },
        { id: "drivers", label: "Drivers", icon: "👨‍✈️" },
        { id: "analytics", label: "Analytics", icon: "📈" },
        { id: "payments", label: "Payments", icon: "💳" },
        { id: "fare-config", label: "Fare Config", icon: "⚙️" },
        { id: "alerts", label: "Alerts", icon: "⚠️" },
        { id: "tickets", label: "Tickets", icon: "🆘" },
    ];

    if (loadError) return <div style={styles.centerLoading}>Map Load Error: {loadError.message}</div>;

    return (
        <div style={styles.container}>
            <div style={styles.sidebar}>
                <div style={styles.sidebarHeader}>
                    <div style={styles.logo}>UBER ADMIN <span style={{ color: "#276EF1" }}>PRO</span></div>
                </div>

                <div style={styles.navMenu}>
                    {sidebarItems.map(item => (
                        <div
                            key={item.id}
                            style={{
                                ...styles.navItem,
                                ...(view === item.id ? styles.navItemActive : {})
                            }}
                            onClick={() => setView(item.id as DashboardView)}
                        >
                            <span>{item.icon}</span>
                            <span style={{ marginLeft: "12px" }}>{item.label}</span>
                        </div>
                    ))}
                </div>

                <div style={styles.sidebarFooter}>
                    <button style={styles.signOutBtn} onClick={() => { localStorage.clear(); navigate("/"); }}>
                        Log Out
                    </button>
                </div>
            </div>

            <div style={styles.mainContent}>
                {loading ? (
                    <div style={styles.centerLoading}>Loading Dashboard...</div>
                ) : (
                    <div style={styles.viewWrapper}>
                        {view === "overview" && <OverviewTab overview={overview} setView={setView} />}
                        {view === "live-map" && <LiveMapTab isLoaded={isLoaded} apiFetch={apiFetch} />}
                        {view === "fare-config" && <FareConfigTab apiFetch={apiFetch} />}
                        {view === "drivers" && <DriverManagerTab apiFetch={apiFetch} />}
                        {view === "analytics" && <AnalyticsTab apiFetch={apiFetch} />}
                        {view === "payments" && <PaymentMonitorTab apiFetch={apiFetch} />}
                        {view === "alerts" && <AlertsTab apiFetch={apiFetch} />}
                        {view === "tickets" && <TicketsTab apiFetch={apiFetch} />}
                    </div>
                )}
            </div>
        </div>
    );
}

// ── OVERVIEW ────────────────────────────────────────────────────────────
function OverviewTab({ overview, setView }: any) {
    const cards = [
        { label: "Online Drivers", val: overview.online_drivers, color: "#22c55e", id: "drivers" },
        { label: "Active rides", val: overview.active_rides, color: "#276EF1", id: "live-map" },
        { label: "Completed (Today)", val: overview.completed_today, color: "#fff", id: "analytics" },
        { label: "Revenue (Today)", val: `₹${Math.round(overview.revenue_today)}`, color: "#10b981", id: "analytics" },
    ];

    return (
        <div style={styles.tabContent}>
            <h1 style={styles.tabTitle}>Dashboard Overview</h1>
            <div style={styles.statGrid}>
                {cards.map(c => (
                    <div key={c.label} style={styles.statCard} onClick={() => setView(c.id)}>
                        <div style={styles.cardLabel}>{c.label}</div>
                        <div style={{ ...styles.cardVal, color: c.color }}>{c.val}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── LIVE MAP (WS + STATE) ────────────────────────────────────────────────
function LiveMapTab({ isLoaded }: any) {
    const [drivers, setDrivers] = useState<Record<number, DriverMapData>>({});
    const [riders, setRiders] = useState<Record<number, RiderMapData>>({});
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [selectedType, setSelectedType] = useState<"driver" | "rider" | null>(null);
    const [map, setMap] = useState<google.maps.Map | null>(null);

    useEffect(() => {
        const token = localStorage.getItem("access");
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const wsUrl = `${protocol}://${window.location.host}/ws/admin/live-map/?token=${token}`;
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === "DRIVER_LOCATION_UPDATED") {
                    setDrivers(prev => ({ ...prev, [msg.data.driver_id]: msg.data }));
                } else if (msg.type === "RIDER_LOCATION_UPDATED") {
                    setRiders(prev => ({ ...prev, [msg.data.rider_id]: msg.data }));
                }
            } catch (e) { console.error("WS Parse Error", e); }
        };

        return () => ws.close();
    }, []);

    const activeDrivers = Object.values(drivers);
    const activeRiders = Object.values(riders);

    const selectedData = selectedType === "driver" ? drivers[selectedId!] : (selectedType === "rider" ? riders[selectedId!] : null);

    return (
        <div style={styles.liveMapTab}>
            <div style={styles.mapSidePanel}>
                <div style={styles.panelHeader}>Live Fleet ({activeDrivers.length + activeRiders.length})</div>
                <div style={styles.rideList}>
                    {activeDrivers.map(d => (
                        <div
                            key={`d-${d.driver_id}`}
                            style={{
                                ...styles.rideItem,
                                background: (selectedType === "driver" && selectedId === d.driver_id) ? "#1a1a1a" : "transparent"
                            }}
                            onClick={() => { setSelectedId(d.driver_id); setSelectedType("driver"); }}
                        >
                            <div style={styles.rideId}>DRIVER #{d.driver_id}</div>
                            <div style={styles.rideStatusText}>{d.status}</div>
                            <div style={styles.rideUser}>{d.name}</div>
                        </div>
                    ))}
                    {activeRiders.map(r => (
                        <div
                            key={`r-${r.rider_id}`}
                            style={{
                                ...styles.rideItem,
                                background: (selectedType === "rider" && selectedId === r.rider_id) ? "#1a1a1a" : "transparent"
                            }}
                            onClick={() => { setSelectedId(r.rider_id); setSelectedType("rider"); }}
                        >
                            <div style={styles.rideId}>RIDER #{r.rider_id}</div>
                            <div style={styles.rideStatusText}>{r.status}</div>
                            <div style={styles.rideUser}>{r.rider_name}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div style={styles.mapFrame}>
                {isLoaded ? (
                    <GoogleMap
                        mapContainerStyle={{ width: "100%", height: "100%" }}
                        center={{ lat: 12.9716, lng: 77.5946 }}
                        zoom={13}
                        options={{ disableDefaultUI: true, zoomControl: true, mapId: "ac584fdc61f9c23a0aecc050" }}
                        onLoad={setMap}
                    >
                        {activeDrivers.map(d => (
                            <AdminMarker key={`d-${d.driver_id}`} map={map} position={{ lat: d.lat, lng: d.lng }} type="driver" status={d.status} />
                        ))}
                        {activeRiders.map(r => (
                            <AdminMarker key={`r-${r.rider_id}`} map={map} position={{ lat: r.lat, lng: r.lng }} type="rider" />
                        ))}

                        {selectedData?.ride?.polyline && (
                            <Polyline
                                path={google.maps.geometry.encoding.decodePath(selectedData.ride.polyline)}
                                options={{ strokeColor: "#276EF1", strokeWeight: 5, strokeOpacity: 0.8 }}
                            />
                        )}
                    </GoogleMap>
                ) : <div style={styles.centerLoading}>Loading Map...</div>}
            </div>
        </div>
    );
}

// ── FARE CONFIG ──────────────────────────────────────────────────────────
function FareConfigTab({ apiFetch }: any) {
    const [configs, setConfigs] = useState<any[]>([]);
    const [selectedConfig, setSelectedConfig] = useState<any>(null);
    const [submitting, setSubmitting] = useState(false);

    const load = async () => {
        const data = await apiFetch("/admin/fare-config/");
        setConfigs(data || []);
        if (data && data.length > 0) setSelectedConfig(data[0]);
    };

    useEffect(() => { load(); }, []);

    const handleUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await apiFetch(`/admin/fare-config/${selectedConfig.id}/`, {
                method: "PATCH",
                body: JSON.stringify(selectedConfig)
            });
            alert("Pricing updated successfully!");
        } catch (e) { alert("Update failed."); }
        finally { setSubmitting(false); }
    };

    if (!selectedConfig) return <div style={styles.centerLoading}>Loading Configs...</div>;

    return (
        <div style={styles.tabContent}>
            <h1 style={styles.tabTitle}>Fare Settings</h1>
            <div style={{ display: "flex", gap: "10px", marginBottom: "30px" }}>
                {configs.map(c => (
                    <button
                        key={c.id}
                        style={{ ...styles.tabBtn, background: selectedConfig.id === c.id ? "#276EF1" : "#1a1a1a" }}
                        onClick={() => setSelectedConfig(c)}
                    >
                        {c.vehicle_type.toUpperCase()}
                    </button>
                ))}
            </div>
            <form style={styles.configForm} onSubmit={handleUpdate}>
                <div style={styles.formGrid}>
                    <div style={styles.formGroup}>
                        <label style={styles.label}>Base Fare (₹)</label>
                        <input className="admin-input" style={styles.input} type="number" step="0.01" value={selectedConfig.base_fare} onChange={e => setSelectedConfig({ ...selectedConfig, base_fare: e.target.value })} />
                    </div>
                    <div style={styles.formGroup}>
                        <label style={styles.label}>Per KM Rate (₹)</label>
                        <input className="admin-input" style={styles.input} type="number" step="0.01" value={selectedConfig.per_km_rate} onChange={e => setSelectedConfig({ ...selectedConfig, per_km_rate: e.target.value })} />
                    </div>
                    <div style={styles.formGroup}>
                        <label style={styles.label}>Waiting (₹/min)</label>
                        <input className="admin-input" style={styles.input} type="number" step="0.01" value={selectedConfig.waiting_per_minute} onChange={e => setSelectedConfig({ ...selectedConfig, waiting_per_minute: e.target.value })} />
                    </div>
                    <div style={styles.formGroup}>
                        <label style={styles.label}>Surge</label>
                        <input className="admin-input" style={styles.input} type="number" step="0.01" value={selectedConfig.surge_multiplier} onChange={e => setSelectedConfig({ ...selectedConfig, surge_multiplier: e.target.value })} />
                    </div>
                </div>
                <button type="submit" style={styles.submitBtn} disabled={submitting}>{submitting ? "Saving..." : "Apply Price Changes"}</button>
            </form>
        </div>
    );
}

// ── ANALYTICS ────────────────────────────────────────────────────────────
function AnalyticsTab({ apiFetch }: any) {
    const [data, setData] = useState<any>(null);

    useEffect(() => {
        apiFetch("/admin/analytics/").then(setData);
    }, []);

    if (!data) return <div style={styles.centerLoading}>Calculating Analytics...</div>;

    const chartData = data.daily_stats.map((s: any) => ({
        name: new Date(s.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }),
        revenue: Math.round(Number(s.revenue || 0)),
        rides: s.total_count,
    }));

    return (
        <div style={styles.tabContent}>
            <h1 style={styles.tabTitle}>Analytics Dashboard</h1>
            <div style={styles.statGrid}>
                <div style={styles.statCard}>
                    <div style={styles.cardLabel}>Rev (30D)</div>
                    <div style={styles.cardVal}>₹{Math.round(data.lifetime.total_revenue).toLocaleString()}</div>
                </div>
                <div style={styles.statCard}>
                    <div style={styles.cardLabel}>Cancel Rate</div>
                    <div style={styles.cardVal}>{data.lifetime.cancellation_rate}%</div>
                </div>
            </div>
            <div style={{ marginTop: "40px", height: "400px", background: "#0c0c0c", borderRadius: "16px", padding: "20px" }}>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                        <XAxis dataKey="name" stroke="#555" fontSize={12} />
                        <YAxis stroke="#555" fontSize={12} />
                        <Tooltip contentStyle={{ background: "#000", border: "1px solid #333" }} />
                        <Area type="monotone" dataKey="revenue" stroke="#276EF1" fill="rgba(39,110,241,0.2)" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

// ── DRIVERS ──────────────────────────────────────────────────────────────
function DriverManagerTab({ apiFetch }: any) {
    const [drivers, setDrivers] = useState<any[]>([]);

    const load = () => apiFetch("/admin/drivers/").then((res: any) => setDrivers(Array.isArray(res) ? res : []));
    useEffect(() => { load(); }, []);

    const handleAction = async (id: number, action: string) => {
        await apiFetch(`/admin/drivers/${id}/action/`, {
            method: "POST",
            body: JSON.stringify({ action })
        });
        load();
    };

    return (
        <div style={styles.tabContent}>
            <h1 style={styles.tabTitle}>Driver Fleet</h1>
            <table style={styles.table}>
                <thead>
                    <tr>
                        <th style={styles.th}>Driver</th>
                        <th style={styles.th}>Vehicle</th>
                        <th style={styles.th}>Status</th>
                        <th style={styles.th}>Verified</th>
                        <th style={styles.th}>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {drivers.map(d => (
                        <tr key={d.id} style={styles.tr}>
                            <td style={styles.td}>{d.full_name}<br /><small style={{ color: "#666" }}>{d.phone}</small></td>
                            <td style={styles.td}>{d.vehicle_model}</td>
                            <td style={styles.td}>{d.status}</td>
                            <td style={styles.td}>{d.is_verified ? "✅" : "❌"}</td>
                            <td style={styles.td}>
                                {!d.is_verified ?
                                    <button style={styles.approveBtn} onClick={() => handleAction(d.id, "approve")}>Verify</button> :
                                    <button style={styles.dangerBtn} onClick={() => handleAction(d.id, "block")}>Block</button>
                                }
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// ── PAYMENTS ─────────────────────────────────────────────────────────────
function PaymentMonitorTab({ apiFetch }: any) {
    const [data, setData] = useState<any>(null);
    useEffect(() => { apiFetch("/admin/payments/status/").then(setData); }, []);

    if (!data) return <div style={styles.centerLoading}>Fetching Payments...</div>;

    return (
        <div style={styles.tabContent}>
            <h1 style={styles.tabTitle}>Payment Health</h1>
            <div style={styles.statGrid}>
                <div style={styles.statCard}><div style={styles.cardLabel}>Success</div><div style={styles.cardVal}>{data.summary.success}</div></div>
                <div style={styles.statCard}><div style={styles.cardLabel}>Failures</div><div style={{ ...styles.cardVal, color: "#ef4444" }}>{data.summary.failed}</div></div>
            </div>
            {data.alerts?.map((a: any, i: number) => (
                <div key={i} style={{ ...styles.systemAlert, marginTop: "20px" }}>⚠️ {a.message}</div>
            ))}
        </div>
    );
}

// ── ALERTS ───────────────────────────────────────────────────────────────
function AlertsTab({ apiFetch }: any) {
    const [logs, setLogs] = useState<any[]>([]);
    useEffect(() => { apiFetch("/admin/alerts/").then(setLogs); }, []);

    return (
        <div style={styles.tabContent}>
            <h1 style={styles.tabTitle}>System Logs</h1>
            <div style={styles.logList}>
                {logs.map(l => (
                    <div key={l.id} style={styles.logItem}>
                        <div style={styles.logHeader}><strong>{l.type}</strong> <span>{new Date(l.created_at).toLocaleString()}</span></div>
                        <div>{l.message}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── TICKETS ──────────────────────────────────────────────────────────────
function TicketsTab({ apiFetch }: any) {
    const [tickets, setTickets] = useState<any[]>([]);
    useEffect(() => { apiFetch("/admin/tickets/").then((d: any) => setTickets(d.tickets || [])); }, []);

    return (
        <div style={styles.tabContent}>
            <h1 style={styles.tabTitle}>Support Queue</h1>
            <div style={styles.ticketsGrid}>
                {tickets.map(t => (
                    <div key={t.id} style={styles.ticketCard}>
                        <div style={styles.ticketReason}>{t.reason}</div>
                        <p>{t.description}</p>
                        <div style={styles.ticketMeta}>By {t.user_name} · Ride #{t.ride_id}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── MARKER ───────────────────────────────────────────────────────────────
function AdminMarker({ map, position, type, status }: any) {
    useEffect(() => {
        if (!map || !window.google || !google.maps.marker?.AdvancedMarkerElement || !position.lat) return;
        const el = document.createElement("div");
        const isDriver = type === "driver";
        el.style.cssText = `
            width: ${isDriver ? "34px" : "12px"}; height: ${isDriver ? "34px" : "12px"};
            background: ${isDriver ? (status === "ONLINE" ? "#22c55e" : "#000") : "#276EF1"};
            border: 2px solid white; border-radius: ${isDriver ? "8px" : "50%"};
            display: flex; align-items: center; justify-content: center; font-size: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        `;
        el.innerText = isDriver ? "🚗" : "";

        const marker = new google.maps.marker.AdvancedMarkerElement({ map, position, content: el });
        return () => { marker.map = null; };
    }, [map, position.lat, position.lng, type, status]);
    return null;
}

const styles: Record<string, CSSProperties> = {
    container: { display: "flex", height: "100vh", background: "#000", color: "#fff", fontFamily: "sans-serif" },
    sidebar: { width: "240px", borderRight: "1px solid #1a1a1a", display: "flex", flexDirection: "column" },
    sidebarHeader: { padding: "30px 24px" },
    logo: { fontSize: "16px", fontWeight: "900" },
    navMenu: { flex: 1 },
    navItem: { padding: "14px 24px", fontSize: "14px", color: "#666", cursor: "pointer", display: "flex", alignItems: "center" },
    navItemActive: { color: "#fff", background: "#111", borderLeft: "4px solid #fff" },
    sidebarFooter: { padding: "20px" },
    signOutBtn: { width: "100%", background: "#111", color: "#fff", border: "none", padding: "12px", borderRadius: "8px", cursor: "pointer" },
    mainContent: { flex: 1, backgroundColor: "#060606", overflow: "hidden" },
    centerLoading: { display: "flex", height: "100%", alignItems: "center", justifyContent: "center", color: "#666" },
    viewWrapper: { padding: "40px", height: "100%", overflowY: "auto" },
    tabContent: { maxWidth: "1200px", margin: "0 auto" },
    tabTitle: { fontSize: "28px", fontWeight: "800", marginBottom: "32px" },
    statGrid: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "20px" },
    statCard: { background: "#0c0c0c", padding: "24px", borderRadius: "16px", border: "1px solid #161616", cursor: "pointer" },
    cardLabel: { fontSize: "12px", color: "#666", textTransform: "uppercase", marginBottom: "8px" },
    cardVal: { fontSize: "24px", fontWeight: "800" },
    liveMapTab: { display: "flex", height: "calc(100vh - 80px)", margin: "-40px" },
    mapSidePanel: { width: "320px", borderRight: "1px solid #1a1a1a", background: "#080808", overflowY: "auto" },
    panelHeader: { padding: "24px", fontSize: "14px", fontWeight: "700", borderBottom: "1px solid #111" },
    rideList: { padding: "0" },
    rideItem: { padding: "16px 24px", borderBottom: "1px solid #111", cursor: "pointer" },
    rideId: { fontSize: "11px", color: "#666" },
    rideStatusText: { fontSize: "14px", fontWeight: "700", color: "#276EF1" },
    rideUser: { fontSize: "13px", color: "#aaa" },
    mapFrame: { flex: 1, position: "relative" },
    tabBtn: { border: "none", color: "#fff", padding: "8px 16px", borderRadius: "8px", cursor: "pointer" },
    configForm: { maxWidth: "600px" },
    formGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "32px" },
    formGroup: { display: "flex", flexDirection: "column", gap: "8px" },
    label: { fontSize: "12px", color: "#666" },
    input: { background: "#111", border: "1px solid #222", color: "#fff", padding: "12px", borderRadius: "8px" },
    submitBtn: { background: "#fff", color: "#000", border: "none", width: "100%", padding: "16px", borderRadius: "12px", fontWeight: "800" },
    table: { width: "100%", borderCollapse: "collapse", textAlign: "left" },
    th: { padding: "16px", borderBottom: "1px solid #111", color: "#555", fontSize: "12px" },
    td: { padding: "16px", borderBottom: "1px solid #111", fontSize: "14px" },
    approveBtn: { background: "#22c55e", color: "#fff", border: "none", padding: "6px 12px", borderRadius: "4px" },
    dangerBtn: { background: "#ef4444", color: "#fff", border: "none", padding: "6px 12px", borderRadius: "4px" },
    systemAlert: { background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", padding: "16px", borderRadius: "12px" },
    logList: { background: "#080808", borderRadius: "16px", border: "1px solid #111" },
    logItem: { padding: "16px 24px", borderBottom: "1px solid #111" },
    logHeader: { display: "flex", justifyContent: "space-between", marginBottom: "8px" },
    ticketsGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" },
    ticketCard: { background: "#0c0c0c", padding: "24px", borderRadius: "16px" },
    ticketReason: { color: "#276EF1", fontWeight: "800", fontSize: "11px", marginBottom: "8px" },
    ticketMeta: { fontSize: "12px", color: "#555", marginTop: "12px" }
};

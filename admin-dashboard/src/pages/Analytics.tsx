import { useEffect, useState } from "react";
import { api } from "../services/api";
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer, BarChart, Bar
} from 'recharts';

export default function Analytics() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const fetchAnalytics = async () => {
        try {
            const res = await api.get("/admin/analytics/");
            setData(res.data);
        } catch (err) {
            console.error("Analytics API error:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAnalytics();
    }, []);

    if (loading) return <div className="page-center">Loading Data...</div>;

    const chartData = data?.daily_stats?.map((day: any) => ({
        name: new Date(day.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }),
        revenue: Math.round(Number(day.revenue || 0)),
        rides: day.total_count,
        cancelled: day.cancelled_count
    }));

    return (
        <div className="page" style={{ padding: "36px 48px" }}>
            <header className="page-header">
                <div>
                    <h1 className="page-title">Fleet Analytics</h1>
                    <p className="page-sub">Comprehensive performance monitoring and revenue growth trends</p>
                </div>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
                <StatCard label="LifeTime Revenue" val={`₹${Math.round(data?.lifetime?.total_revenue || 0).toLocaleString()}`} color="var(--accent)" />
                <StatCard label="Avg Ride Distance" val={`${data?.lifetime?.avg_distance?.toFixed(1) || 0} km`} color="var(--yellow)" />
                <StatCard label="Cancellation Rate" val={`${data?.lifetime?.cancellation_rate || 0}%`} color="var(--red)" />
                <StatCard label="Active Drivers" val={data?.online_drivers || 0} color="var(--green)" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
                {/* Revenue Trend */}
                <div className="glass-card" style={{ padding: 28, height: 400 }}>
                    <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-3)", textTransform: "uppercase", marginBottom: 24, letterSpacing: 1 }}>Revenue Stream (Last 30 Days)</h3>
                    <ResponsiveContainer width="100%" height="85%">
                        <AreaChart data={chartData}>
                            <defs>
                                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                            <XAxis dataKey="name" stroke="var(--text-3)" fontSize={11} tickLine={false} axisLine={false} />
                            <YAxis stroke="var(--text-3)" fontSize={11} tickLine={false} axisLine={false} />
                            <Tooltip contentStyle={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 12 }} />
                            <Area type="monotone" dataKey="revenue" stroke="var(--accent)" fillOpacity={1} fill="url(#colorRevenue)" strokeWidth={3} />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* Ride Volume */}
                <div className="glass-card" style={{ padding: 28, height: 400 }}>
                    <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-3)", textTransform: "uppercase", marginBottom: 24, letterSpacing: 1 }}>Ride Allocation & Cancellations</h3>
                    <ResponsiveContainer width="100%" height="85%">
                        <BarChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                            <XAxis dataKey="name" stroke="var(--text-3)" fontSize={11} tickLine={false} />
                            <YAxis stroke="var(--text-3)" fontSize={11} tickLine={false} />
                            <Tooltip contentStyle={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 12 }} />
                            <Legend wrapperStyle={{ fontSize: 11, fontWeight: 600 }} iconType="circle" />
                            <Bar dataKey="rides" name="Completed" fill="var(--green)" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="cancelled" name="Cancelled" fill="var(--red)" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}

function StatCard({ label, val, color }: any) {
    return (
        <div className="glass-card animate-fade" style={{ padding: "20px 24px", borderLeft: `4px solid ${color}` }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 24, fontWeight: 900, color: "#fff", letterSpacing: -0.5 }}>{val}</div>
        </div>
    );
}

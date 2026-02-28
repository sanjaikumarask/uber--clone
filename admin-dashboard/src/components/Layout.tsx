import { useState, useEffect } from "react";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { api } from "../services/api";

const NAV = [
    { path: "/", label: "Overview", icon: "⬡" },
    { path: "/drivers", label: "Drivers", icon: "🚗" },
    { path: "/verification", label: "Verification", icon: "🛡️" },
    { path: "/support", label: "Support", icon: "🎧" },
    { path: "/reports", label: "Reports", icon: "📑" },
    { path: "/rides", label: "Trips", icon: "🗺" },
    { path: "/ledger", label: "Earnings", icon: "₹" },
    { path: "/payouts", label: "Payouts", icon: "💳" },
    { path: "/payments", label: "Monitoring", icon: "💎" },
    { path: "/offers", label: "Promotions", icon: "🏷" },
    { path: "/incentives", label: "Incentives", icon: "⭐" },
    { path: "/analytics", label: "Analytics", icon: "📊" },
    { path: "/fare-config", label: "Fare Config", icon: "⚙️" },
    { path: "/alerts", label: "Alerts", icon: "🚨" },
    { path: "/live-map", label: "Live Map", icon: "📡" },
];

export default function Layout() {
    const navigate = useNavigate();
    const location = useLocation();
    const [user, setUser] = useState<any>(null);
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        api.get("/users/me/").then(res => setUser(res.data)).catch(() => { });
        const t = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(t);
    }, []);

    const handleLogout = () => {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        navigate("/login");
    };

    const isActive = (path: string) =>
        path === "/" ? location.pathname === "/" : location.pathname.startsWith(path);

    return (
        <div style={{ display: "flex", minHeight: "100vh", width: "100%", background: "var(--bg)" }}>
            {/* ── SIDEBAR ──────────────────────────────────────────────────── */}
            <aside style={{
                width: 240, flexShrink: 0,
                background: "var(--bg-2)",
                borderRight: "1px solid var(--border)",
                display: "flex", flexDirection: "column",
                position: "sticky", top: 0, height: "100vh",
                overflowY: "auto",
            }}>
                {/* Logo */}
                <div style={{ padding: "28px 20px 20px", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                        <div style={{
                            width: 32, height: 32, borderRadius: 8,
                            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 16, boxShadow: "0 0 16px rgba(59,130,246,0.4)"
                        }}>⚡</div>
                        <div>
                            <div style={{ fontWeight: 800, fontSize: 15, color: "var(--text-1)", letterSpacing: -0.3 }}>FleetOps</div>
                            <div style={{ fontSize: 10, color: "var(--text-3)", fontWeight: 500, letterSpacing: 0.5 }}>ADMIN CONSOLE</div>
                        </div>
                    </div>
                    {/* Live clock */}
                    <div style={{
                        marginTop: 14, padding: "8px 12px",
                        background: "rgba(34,197,94,0.05)",
                        border: "1px solid rgba(34,197,94,0.15)",
                        borderRadius: 8,
                        display: "flex", alignItems: "center", gap: 8
                    }}>
                        <div className="live-dot" />
                        <span style={{ fontSize: 11, color: "var(--green)", fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
                            {time.toLocaleTimeString()}
                        </span>
                    </div>
                </div>

                {/* Nav */}
                <nav style={{ flex: 1, padding: "12px 10px", display: "flex", flexDirection: "column", gap: 2 }}>
                    <div style={{ fontSize: 9, color: "var(--text-3)", fontWeight: 700, letterSpacing: 1.5, padding: "8px 10px 4px", textTransform: "uppercase" }}>
                        Navigation
                    </div>
                    {NAV.map(item => {
                        const active = isActive(item.path);
                        return (
                            <Link key={item.path} to={item.path} style={{
                                display: "flex", alignItems: "center", gap: 10,
                                padding: "9px 12px",
                                borderRadius: 8,
                                textDecoration: "none",
                                color: active ? "#fff" : "var(--text-2)",
                                background: active ? "var(--accent)" : "transparent",
                                fontWeight: active ? 600 : 400,
                                fontSize: 13,
                                transition: "all 0.15s",
                                boxShadow: active ? "0 2px 12px var(--accent-glow)" : "none",
                                position: "relative",
                            }}
                                onMouseEnter={e => { if (!active) { e.currentTarget.style.background = "var(--bg-4)"; e.currentTarget.style.color = "var(--text-1)"; } }}
                                onMouseLeave={e => { if (!active) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--text-2)"; } }}
                            >
                                <span style={{ fontSize: 15, width: 20, textAlign: "center", opacity: active ? 1 : 0.7 }}>{item.icon}</span>
                                {item.label}
                                {item.path === "/live-map" && (
                                    <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4, fontSize: 9, color: "var(--green)", fontWeight: 700, background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.2)", padding: "2px 6px", borderRadius: 99 }}>
                                        <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--green)", display: "inline-block" }} />
                                        LIVE
                                    </span>
                                )}
                            </Link>
                        );
                    })}
                </nav>

                {/* User card */}
                <div style={{ padding: "12px 10px", borderTop: "1px solid var(--border)" }}>
                    <div style={{
                        background: "var(--bg-3)", border: "1px solid var(--border)",
                        borderRadius: 10, padding: "14px"
                    }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                            <div style={{
                                width: 34, height: 34, borderRadius: "50%",
                                background: "linear-gradient(135deg, var(--accent), var(--purple))",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontWeight: 800, fontSize: 13, color: "#fff", flexShrink: 0
                            }}>
                                {(user?.username?.[0] || "A").toUpperCase()}
                            </div>
                            <div style={{ minWidth: 0 }}>
                                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-1)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                    {user?.phone || user?.username || "Admin"}
                                </div>
                                <div style={{ fontSize: 10, color: "var(--accent)", fontWeight: 600, letterSpacing: 0.5 }}>OPERATOR</div>
                            </div>
                        </div>
                        <button onClick={handleLogout} className="btn-ghost" style={{ width: "100%", fontSize: 12, padding: "7px 12px" }}>
                            Sign Out
                        </button>
                    </div>
                </div>
            </aside>

            {/* ── MAIN CONTENT ─────────────────────────────────────────────── */}
            <main style={{ flex: 1, overflowY: "auto", minWidth: 0 }}>
                <Outlet />
            </main>
        </div>
    );
}

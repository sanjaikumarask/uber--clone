import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export default function Login() {
    const [identifier, setIdentifier] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        const isEmail = identifier.includes("@");
        const payload = isEmail
            ? { email: identifier, password }
            : { username: identifier, password };

        try {
            const response = await api.post("/users/admin-login/", payload);
            localStorage.setItem("access", response.data.access);
            localStorage.setItem("refresh", response.data.refresh);
            navigate("/");
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.response?.data?.error || "Invalid credentials";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const inputStyle: React.CSSProperties = {
        width: "100%", padding: "12px 16px",
        background: "rgba(255,255,255,0.04)",
        border: "1px solid var(--border-2)",
        borderRadius: 10, color: "var(--text-1)",
        fontFamily: "var(--font)", fontSize: 14,
        outline: "none", transition: "border-color 0.15s, box-shadow 0.15s",
    };

    return (
        <div style={{
            minHeight: "100vh",
            display: "flex",
            background: "var(--bg)",
            position: "relative",
            overflow: "hidden",
        }}>
            {/* Background gradient orbs */}
            <div style={{ position: "fixed", top: "20%", left: "15%", width: 500, height: 500, borderRadius: "50%", background: "radial-gradient(circle, rgba(59,130,246,0.07) 0%, transparent 70%)", pointerEvents: "none" }} />
            <div style={{ position: "fixed", bottom: "15%", right: "10%", width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)", pointerEvents: "none" }} />

            {/* Left panel — branding */}
            <div style={{
                flex: 1, display: "flex", flexDirection: "column",
                justifyContent: "center", padding: "80px",
                borderRight: "1px solid var(--border)",
            }}>
                <div style={{ maxWidth: 460 }}>
                    {/* Logo */}
                    <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 56 }}>
                        <div style={{
                            width: 48, height: 48, borderRadius: 14,
                            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 24, boxShadow: "0 4px 24px rgba(59,130,246,0.4)"
                        }}>⚡</div>
                        <div>
                            <div style={{ fontWeight: 800, fontSize: 22, letterSpacing: -0.5 }}>FleetOps</div>
                            <div style={{ fontSize: 11, color: "var(--text-3)", letterSpacing: 1.5, fontWeight: 600, textTransform: "uppercase" }}>Admin Console</div>
                        </div>
                    </div>

                    <h1 style={{ fontSize: "3rem", fontWeight: 900, marginBottom: 16, letterSpacing: -1.5, lineHeight: 1.1 }}>
                        Command your<br />
                        <span style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                            entire fleet
                        </span>
                    </h1>
                    <p style={{ color: "var(--text-2)", fontSize: 16, lineHeight: 1.7, marginBottom: 48, maxWidth: 380 }}>
                        Real-time driver tracking, earnings analytics, ride management — all in one production-grade control center.
                    </p>

                    {/* Feature pills */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                        {[
                            { icon: "📡", label: "Live GPS Tracking" },
                            { icon: "📊", label: "Analytics" },
                            { icon: "💳", label: "Payouts" },
                            { icon: "🚨", label: "Route Alerts" },
                        ].map(f => (
                            <div key={f.label} style={{
                                display: "flex", alignItems: "center", gap: 8,
                                background: "var(--bg-3)", border: "1px solid var(--border)",
                                borderRadius: 99, padding: "7px 14px",
                                fontSize: 12, color: "var(--text-2)", fontWeight: 500,
                            }}>
                                <span style={{ fontSize: 13 }}>{f.icon}</span>
                                {f.label}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Right panel — login form */}
            <div style={{
                width: 480, flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                padding: 40,
            }}>
                <div style={{
                    width: "100%", maxWidth: 400,
                    background: "var(--bg-2)",
                    border: "1px solid var(--border)",
                    borderRadius: 20,
                    padding: "40px",
                    boxShadow: "0 24px 80px rgba(0,0,0,0.5)",
                    animation: "fadeIn 0.4s ease-out",
                }}>
                    <div style={{ marginBottom: 32, textAlign: "center" }}>
                        <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 6, letterSpacing: -0.5 }}>Welcome back</h2>
                        <p style={{ color: "var(--text-3)", fontSize: 13, margin: 0 }}>Sign in to your admin account</p>
                    </div>

                    <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                        <div>
                            <label htmlFor="identifier" style={{ fontSize: 11, fontWeight: 700, color: "var(--text-3)", letterSpacing: 0.8, textTransform: "uppercase", display: "block", marginBottom: 8 }}>
                                Email or Username
                            </label>
                            <input
                                id="identifier"
                                value={identifier}
                                onChange={e => setIdentifier(e.target.value)}
                                placeholder="admin@example.com or admin"
                                autoComplete="username"
                                required
                                style={inputStyle}
                                onFocus={e => { e.target.style.borderColor = "var(--accent)"; e.target.style.boxShadow = "0 0 0 3px var(--accent-dim)"; }}
                                onBlur={e => { e.target.style.borderColor = "var(--border-2)"; e.target.style.boxShadow = "none"; }}
                            />
                        </div>

                        <div>
                            <label htmlFor="password" style={{ fontSize: 11, fontWeight: 700, color: "var(--text-3)", letterSpacing: 0.8, textTransform: "uppercase", display: "block", marginBottom: 8 }}>
                                Password
                            </label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="••••••••"
                                autoComplete="current-password"
                                required
                                style={inputStyle}
                                onFocus={e => { e.target.style.borderColor = "var(--accent)"; e.target.style.boxShadow = "0 0 0 3px var(--accent-dim)"; }}
                                onBlur={e => { e.target.style.borderColor = "var(--border-2)"; e.target.style.boxShadow = "none"; }}
                            />
                        </div>

                        {error && (
                            <div style={{
                                background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)",
                                borderRadius: 8, padding: "10px 14px",
                                display: "flex", alignItems: "center", gap: 8,
                            }}>
                                <span style={{ fontSize: 14 }}>⚠️</span>
                                <span style={{ color: "var(--red)", fontSize: 13, fontWeight: 500 }}>{error}</span>
                            </div>
                        )}

                        <button type="submit" className="btn-primary" disabled={loading} style={{
                            width: "100%", padding: "13px", fontSize: 14, marginTop: 4,
                            borderRadius: 10, opacity: loading ? 0.7 : 1,
                        }}>
                            {loading ? "Signing in..." : "Sign In →"}
                        </button>
                    </form>

                    <div style={{ marginTop: 24, padding: "14px", background: "rgba(59,130,246,0.05)", border: "1px solid rgba(59,130,246,0.1)", borderRadius: 8, textAlign: "center" }}>
                        <p style={{ margin: 0, fontSize: 11, color: "var(--text-3)" }}>
                            🔒 Admin access only — unauthorized access will be logged
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

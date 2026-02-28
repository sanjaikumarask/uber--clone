import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Link } from "react-router-dom";

const REFRESH_INTERVAL = 30_000;

const STAT_CARDS = (d: any) => [
  { label: "Online Drivers", value: d?.online_drivers ?? 0, icon: "🟢", color: "var(--green)", accent: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.2)" },
  { label: "Busy Drivers", value: d?.busy_drivers ?? 0, icon: "🔵", color: "var(--accent)", accent: "rgba(59,130,246,0.1)", border: "rgba(59,130,246,0.2)" },
  { label: "Active Trips", value: d?.active_rides ?? 0, icon: "🚗", color: "var(--yellow)", accent: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.2)" },
  { label: "Completed Today", value: d?.completed_today ?? 0, icon: "✅", color: "var(--green)", accent: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.2)" },
  { label: "Cancellations", value: d?.cancelled_today ?? 0, icon: "❌", color: "var(--red)", accent: "rgba(239,68,68,0.1)", border: "rgba(239,68,68,0.2)" },
];

const QUICK_LINKS = [
  { path: "/live-map", icon: "📡", label: "Live Map", desc: "Real-time driver tracking" },
  { path: "/drivers", icon: "🚗", label: "Drivers", desc: "Manage driver fleet" },
  { path: "/rides", icon: "🗺", label: "Trips", desc: "Browse all trips" },
  { path: "/analytics", icon: "📊", label: "Analytics", desc: "Performance metrics" },
];

const STATUS_SERVICES = [
  { name: "WebSocket Gateway", ok: true, latency: "4ms" },
  { name: "API Server", ok: true, latency: "12ms" },
  { name: "Location Tracking", ok: true, latency: "8ms" },
  { name: "Notification Service", ok: true, latency: "21ms" },
];

export default function Overview() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [time, setTime] = useState(new Date());

  const fetchData = async () => {
    try {
      const res = await api.get("/admin/overview/");
      setData(res.data);
    } catch (err) {
      console.error("Overview API error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const dataTimer = setInterval(fetchData, REFRESH_INTERVAL);
    const clockTimer = setInterval(() => setTime(new Date()), 1000);
    return () => { clearInterval(dataTimer); clearInterval(clockTimer); };
  }, []);

  const stats = STAT_CARDS(data);

  return (
    <div className="page" style={{ padding: "36px 48px" }}>
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="page-header">
        <div>
          <h1 className="page-title">Operations Overview</h1>
          <p className="page-sub">Fleet performance at a glance · Auto-refreshes every 30s</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.15)",
            borderRadius: 99, padding: "6px 14px"
          }}>
            <div className="live-dot" />
            <span style={{ fontSize: 11, color: "var(--green)", fontWeight: 700 }}>SYSTEM OPERATIONAL</span>
          </div>
          <span style={{ fontSize: 11, color: "var(--text-3)", fontVariantNumeric: "tabular-nums" }}>
            {time.toLocaleString()}
          </span>
        </div>
      </header>

      {/* ── Stat cards ─────────────────────────────────────────── */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 32 }}>
        {stats.map((s, i) => (
          <div key={i} className="stat-card animate-fade" style={{
            animationDelay: `${i * 0.05}s`,
            borderColor: loading ? "var(--border)" : s.border,
            background: loading ? "var(--bg-3)" : s.accent,
          }}>
            {loading ? (
              <>
                <div className="skeleton" style={{ width: "60%", height: 12, marginBottom: 16 }} />
                <div className="skeleton" style={{ width: "40%", height: 32 }} />
              </>
            ) : (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: s.color, letterSpacing: 1, textTransform: "uppercase" }}>
                    {s.label}
                  </span>
                  <span style={{ fontSize: 20 }}>{s.icon}</span>
                </div>
                <div style={{ fontSize: 36, fontWeight: 900, color: "var(--text-1)", letterSpacing: -1, lineHeight: 1 }}>
                  {s.value.toLocaleString()}
                </div>
              </>
            )}
          </div>
        ))}
      </section>

      {/* ── Two-column bottom ───────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20 }}>
        {/* Quick links */}
        <div className="glass-card" style={{ padding: 28 }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-2)", letterSpacing: 0.8, textTransform: "uppercase", marginBottom: 20 }}>
            Quick Access
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {QUICK_LINKS.map(l => (
              <Link key={l.path} to={l.path} style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "16px", borderRadius: 10,
                background: "var(--bg-4)", border: "1px solid var(--border)",
                textDecoration: "none", transition: "all 0.15s",
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--accent)"; e.currentTarget.style.background = "var(--accent-dim)"; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.background = "var(--bg-4)"; }}
              >
                <span style={{ fontSize: 24 }}>{l.icon}</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13, color: "var(--text-1)", marginBottom: 2 }}>{l.label}</div>
                  <div style={{ fontSize: 11, color: "var(--text-3)" }}>{l.desc}</div>
                </div>
              </Link>
            ))}
          </div>

          <div className="divider" />

          {/* Platform status */}
          <h2 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-2)", letterSpacing: 0.8, textTransform: "uppercase", marginBottom: 16 }}>
            Platform Status
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
            {[
              { label: "API Uptime", value: "99.99%", color: "var(--green)" },
              { label: "Throughput", value: "4.2k req/s", color: "var(--text-1)" },
              { label: "Error Rate", value: "0.01%", color: "var(--text-2)" },
            ].map(m => (
              <div key={m.label}>
                <div style={{ fontSize: 9, color: "var(--text-3)", fontWeight: 700, letterSpacing: 1.2, textTransform: "uppercase", marginBottom: 6 }}>{m.label}</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: m.color }}>{m.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Service health */}
        <div className="glass-card" style={{ padding: 28 }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-2)", letterSpacing: 0.8, textTransform: "uppercase", marginBottom: 20 }}>
            Service Health
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {STATUS_SERVICES.map(svc => (
              <div key={svc.name} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "12px 14px", background: "var(--bg-4)",
                borderRadius: 8, border: "1px solid var(--border)"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: svc.ok ? "var(--green)" : "var(--red)", boxShadow: svc.ok ? "0 0 6px var(--green)" : "none" }} />
                  <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-1)" }}>{svc.name}</span>
                </div>
                <span style={{ fontSize: 11, color: "var(--text-3)", fontVariantNumeric: "tabular-nums" }}>{svc.latency}</span>
              </div>
            ))}
          </div>

          <div className="divider" />

          <button className="btn-primary" style={{ width: "100%", fontSize: 12, padding: 10 }}>
            Run Diagnostics
          </button>
        </div>
      </div>
    </div>
  );
}

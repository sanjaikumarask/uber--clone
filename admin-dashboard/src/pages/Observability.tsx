import { useState, useEffect, useRef } from "react";
import { api } from "../services/api";

export default function Observability() {
    const [logs, setLogs] = useState<any[]>([]);
    const [autoScroll, setAutoScroll] = useState(true);
    const logsEndRef = useRef<HTMLDivElement>(null);

    // Fetch logs every 2 seconds
    useEffect(() => {
        const fetchLogs = () => {
            api.get("/admin/logs/").then(res => {
                if (Array.isArray(res.data)) {
                    setLogs(res.data.reverse()); // Reverse back to chronological order for UI
                }
            }).catch(console.error);
        };
        fetchLogs();
        const interval = setInterval(fetchLogs, 2000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (autoScroll && logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs, autoScroll]);

    const getLogColor = (level: string) => {
        switch (level) {
            case "CRITICAL": return "#ef4444";
            case "ERROR": return "#ef4444";
            case "WARNING": return "#f59e0b";
            case "INFO": return "#3b82f6";
            default: return "inherit";
        }
    };

    return (
        <div style={{ padding: 24 }}>
            <div style={{
                display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24
            }}>
                <div>
                    <h1 style={{ margin: "0 0 4px", fontSize: 24, fontWeight: 700, color: "var(--text-1)" }}>
                        System Observability & Tracing
                    </h1>
                    <p style={{ margin: 0, color: "var(--text-2)", fontSize: 13 }}>
                        Monitor Real-time logs and Jump into External APM Providers.
                    </p>
                </div>
                <div style={{ display: "flex", gap: 12 }}>
                    <a href="http://localhost:3000" target="_blank" rel="noreferrer" className="btn-secondary" style={{ display: "flex", gap: "8px", alignItems: "center", textDecoration: "none" }}>
                        📊 Grafana Metrics
                    </a>
                    <a href="http://localhost:5555" target="_blank" rel="noreferrer" className="btn-secondary" style={{ display: "flex", gap: "8px", alignItems: "center", textDecoration: "none" }}>
                        ⚙️ Celery Flower
                    </a>
                    <a href="https://sentry.io" target="_blank" rel="noreferrer" className="btn-secondary" style={{ display: "flex", gap: "8px", alignItems: "center", color: "#e11d48", borderColor: "rgba(225, 29, 72, 0.4)", textDecoration: "none" }}>
                        🚨 Sentry Error Tracking
                    </a>
                    <a href="http://localhost:8082" target="_blank" rel="noreferrer" className="btn-secondary" style={{ display: "flex", gap: "8px", alignItems: "center", textDecoration: "none" }}>
                        🗄️ Redis Commander
                    </a>
                </div>
            </div>

            {/* LIVE SYSTEM TERMINAL */}
            <div style={{
                background: "#0f172a",
                borderRadius: 12,
                border: "1px solid #1e293b",
                overflow: "hidden",
                display: "flex",
                flexDirection: "column",
                height: "calc(100vh - 180px)",
                boxShadow: "0 10px 30px rgba(0,0,0,0.5)"
            }}>
                {/* Header toolbar */}
                <div style={{
                    padding: "12px 16px",
                    background: "#1e293b",
                    borderBottom: "1px solid #334155",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center"
                }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#ef4444" }}></div>
                        <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#f59e0b" }}></div>
                        <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#22c55e" }}></div>
                        <span style={{ marginLeft: 16, color: "#94a3b8", fontSize: 13, fontWeight: 600, fontFamily: "monospace" }}>
                            live-stream: uber-django-backend
                        </span>
                    </div>
                    <label style={{ display: "flex", alignItems: "center", gap: 8, color: "#94a3b8", fontSize: 13, cursor: "pointer" }}>
                        <input type="checkbox" checked={autoScroll} onChange={e => setAutoScroll(e.target.checked)} />
                        Auto-scroll
                    </label>
                </div>

                {/* Log Viewport */}
                <div style={{
                    padding: 16, flex: 1, overflowY: "auto", fontFamily: "Menlo, Monaco, Consolas, monospace",
                    fontSize: 12, lineHeight: 1.5, color: "#cbd5e1"
                }}>
                    {logs.map((log, index) => (
                        <div key={index} style={{
                            display: "flex", gap: 12, padding: "4px 0",
                            borderBottom: "1px dashed rgba(255,255,255,0.05)"
                        }}>
                            <span style={{ color: "#64748b", flexShrink: 0, minWidth: 140 }}>
                                {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "-"}
                            </span>
                            <span style={{
                                color: getLogColor(log.level),
                                fontWeight: 700,
                                minWidth: 60, flexShrink: 0
                            }}>
                                [{log.level}]
                            </span>
                            <span style={{ color: "#8b5cf6", flexShrink: 0, width: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                {log.module || "-"}
                            </span>

                            {/* The core message */}
                            <span style={{ flex: 1, wordBreak: "break-word" }}>
                                {log.message}
                                {log.duration_ms && <span style={{ color: "#f59e0b", marginLeft: 8 }}>({log.duration_ms}ms)</span>}
                                {log.trace_id && <span style={{ color: "#64748b", marginLeft: 8 }}>[Trace: {log.trace_id}]</span>}
                            </span>

                            {/* Exceptions */}
                            {log.exception && (
                                <div style={{
                                    width: "100%", marginTop: 8, padding: 8,
                                    background: "rgba(225, 29, 72, 0.1)",
                                    borderLeft: "3px solid #e11d48",
                                    whiteSpace: "pre-wrap", color: "#fca5a5"
                                }}>
                                    {log.exception}
                                </div>
                            )}
                        </div>
                    ))}
                    <div ref={logsEndRef} />
                </div>
            </div>
        </div>
    );
}

import { useEffect, useState } from "react";
import { api } from "../services/api";

interface SystemLog {
    id: number;
    log_type: string;
    message: string;
    description: string | null;
    created_at: string;
}

export default function Alerts() {
    const [logs, setLogs] = useState<SystemLog[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchLogs = async () => {
        try {
            const res = await api.get("/admin/alerts/");
            setLogs(res.data);
        } catch (err) {
            console.error("Alerts API error", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
        const timer = setInterval(fetchLogs, 45000);
        return () => clearInterval(timer);
    }, []);

    if (loading) return <div className="page-center">Fetching System Audit...</div>;

    const getLogTypeStyle = (logType: string) => {
        if (logType === "ERROR") return {
            background: "rgba(239,68,68,0.1)",
            color: "var(--red)",
            border: "1px solid rgba(239,68,68,0.2)"
        };
        if (logType === "WARNING") return {
            background: "rgba(245,158,11,0.1)",
            color: "var(--yellow)",
            border: "1px solid rgba(245,158,11,0.2)"
        };
        return {
            background: "rgba(59,130,246,0.1)",
            color: "var(--accent)",
            border: "1px solid rgba(59,130,246,0.2)"
        };
    };

    return (
        <div className="page" style={{ padding: "36px 48px" }}>
            <header className="page-header">
                <div>
                    <h1 className="page-title">System Activity Audit</h1>
                    <p className="page-sub">Comprehensive logs of critical system events and security alerts</p>
                </div>
                <button className="btn-ghost" onClick={fetchLogs}>Refresh Logs</button>
            </header>

            <div className="glass-card" style={{ padding: 0, overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                        <tr style={{ background: "rgba(255,255,255,0.02)", borderBottom: "1px solid var(--border)" }}>
                            <th style={{ padding: "16px 24px", textAlign: "left", fontSize: 11, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: 1 }}>Event Time</th>
                            <th style={{ padding: "16px 24px", textAlign: "left", fontSize: 11, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: 1 }}>Level</th>
                            <th style={{ padding: "16px 24px", textAlign: "left", fontSize: 11, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: 1 }}>Incident</th>
                            <th style={{ padding: "16px 24px", textAlign: "left", fontSize: 11, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: 1 }}>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logs.length === 0 ? (
                            <tr><td colSpan={4} style={{ padding: 60, textAlign: "center", color: "var(--text-3)" }}>No system alerts recorded in the last 24h.</td></tr>
                        ) : (
                            logs.map(log => (
                                <tr key={log.id} style={{ borderBottom: "1px solid var(--border)" }}>
                                    <td style={{ padding: "20px 24px", fontSize: 13, color: "var(--text-2)", whiteSpace: "nowrap" }}>
                                        {new Date(log.created_at).toLocaleString()}
                                    </td>
                                    <td style={{ padding: "20px 24px" }}>
                                        <span style={{
                                            padding: "4px 10px", borderRadius: 6, fontSize: 10, fontWeight: 800,
                                            ...getLogTypeStyle(log.log_type)
                                        }}>
                                            {log.log_type}
                                        </span>
                                    </td>
                                    <td style={{ padding: "20px 24px", fontSize: 14, fontWeight: 700, color: "var(--text-1)" }}>
                                        {log.message}
                                    </td>
                                    <td style={{ padding: "20px 24px", fontSize: 13, color: "var(--text-3)", lineHeight: 1.5 }}>
                                        {log.description || "—"}
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

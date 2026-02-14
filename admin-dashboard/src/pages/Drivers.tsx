import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { AdminDriver } from "../types";

export default function Drivers() {
  const [drivers, setDrivers] = useState<AdminDriver[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/drivers/admin/drivers/")
      .then(res => {
        // ✅ CRITICAL FIX: handle paginated / wrapped responses
        const data = Array.isArray(res.data)
          ? res.data
          : res.data.results || [];

        setDrivers(data);
      })
      .catch(err => {
        console.error("Drivers API error", err);
        setDrivers([]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 24 }}>Loading drivers…</div>;
  if (!drivers.length) return <div style={{ padding: 24 }}>No drivers found</div>;

  const handleAction = async (driverId: number, action: "suspend" | "unsuspend") => {
    if (!confirm(`Are you sure you want to ${action} driver #${driverId}?`)) return;

    try {
      await api.post("/drivers/admin/drivers/actions/", {
        driver_id: driverId,
        action,
      });
      // Optimistic update
      setDrivers(prev =>
        prev.map(d =>
          d.driver_id === driverId
            ? { ...d, is_suspended: action === "suspend" }
            : d
        )
      );
    } catch (err) {
      console.error("Action failed", err);
      alert("Action failed");
    }
  };

  if (loading) return <div style={{ padding: 40, color: "#888" }}>Loading drivers…</div>;

  return (
    <div style={{ padding: "40px 60px" }}>
      <h1 style={{ marginBottom: "30px", fontSize: "2rem" }}>Drivers</h1>

      <div style={{ overflowX: "auto", borderRadius: "8px", border: "1px solid #333" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", background: "#1e1e1e" }}>
          <thead>
            <tr style={{ background: "#000", textAlign: "left" }}>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>ID</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Phone</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Status</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Rides</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Rating</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Rejections</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Suspended</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Action</th>
            </tr>
          </thead>

          <tbody>
            {drivers.length === 0 ? (
              <tr><td colSpan={8} style={{ padding: 24, textAlign: "center", color: "#666" }}>No drivers found</td></tr>
            ) : (
              drivers.map(d => (
                <tr key={d.driver_id} style={{ borderBottom: "1px solid #333" }}>
                  <td style={{ padding: "16px", color: "#fff" }}>{d.driver_id}</td>
                  <td style={{ padding: "16px", color: "#fff" }}>{d.phone}</td>
                  <td style={{ padding: "16px" }}>
                    <span
                      style={{
                        padding: "4px 8px",
                        borderRadius: "4px",
                        fontSize: "0.75rem",
                        background: d.status === "ONLINE" ? "#2ecc7120" : "#333",
                        color: d.status === "ONLINE" ? "#2ecc71" : "#888",
                        border: `1px solid ${d.status === "ONLINE" ? "#2ecc71" : "#555"}`,
                      }}
                    >
                      {d.status}
                    </span>
                  </td>
                  <td style={{ padding: "16px", color: "#fff" }}>{d.total_rides}</td>
                  <td style={{ padding: "16px", color: "#f1c40f" }}>★ {d.avg_rating}</td>
                  <td style={{ padding: "16px", color: "#fff" }}>{d.rejections_today}</td>
                  <td style={{ padding: "16px", color: d.is_suspended ? "#e74c3c" : "#2ecc71" }}>
                    {d.is_suspended ? "YES" : "NO"}
                  </td>
                  <td style={{ padding: "16px" }}>
                    {d.is_suspended ? (
                      <button
                        onClick={() => handleAction(d.driver_id, "unsuspend")}
                        style={{
                          background: "#2ecc71", color: "#000",
                          padding: "6px 12px", border: "none", borderRadius: "4px",
                          fontSize: "0.85rem", fontWeight: 600, cursor: "pointer"
                        }}
                      >
                        Unsuspend
                      </button>
                    ) : (
                      <button
                        onClick={() => handleAction(d.driver_id, "suspend")}
                        style={{
                          background: "transparent", color: "#e74c3c",
                          padding: "6px 12px", border: "1px solid #e74c3c",
                          borderRadius: "4px", fontSize: "0.85rem", cursor: "pointer"
                        }}
                      >
                        Suspend
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

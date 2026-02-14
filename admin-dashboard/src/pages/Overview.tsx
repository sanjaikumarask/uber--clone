import { useEffect, useState } from "react";
import { api } from "../services/api";
import StatCard from "../components/StatCard";

export default function Overview() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.get("/admin/overview/")
      .then(res => setData(res.data))
      .catch(err => {
        console.error("Overview API error:", err);
      });
  }, []);

  if (!data) return <div style={{ padding: 40, color: "var(--text-secondary)" }}>Loading dashboard data…</div>;

  return (
    <div style={{ padding: "40px 60px" }}>
      <h1 style={{ marginBottom: "40px", fontSize: "2.5rem", fontWeight: 700 }}>Overview</h1>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "24px"
      }}>
        <StatCard label="Online Drivers" value={data.online_drivers} />
        <StatCard label="Busy Drivers" value={data.busy_drivers} />
        <StatCard label="Active Rides" value={data.active_rides} />
        <StatCard label="Completed Today" value={data.completed_today} />
        <StatCard label="Cancelled Today" value={data.cancelled_today} />
      </div>
    </div>
  );
}

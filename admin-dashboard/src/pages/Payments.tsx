import { useEffect, useState } from "react";
import { api } from "../services/api";

interface AdminPayment {
  id: number;
  user_phone: string;
  amount: number;
  status: string;
  created_at: string;
}

export default function Payments() {
  const [rows, setRows] = useState<AdminPayment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/payments/admin/payments/")
      .then(res => {
        const data = Array.isArray(res.data)
          ? res.data
          : res.data.results || [];

        setRows(data);
      })
      .catch(err => {
        console.error("Payments API error", err);
        setRows([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleRefund = async (paymentId: number) => {
    const amount = prompt("Enter refund amount:");
    if (!amount) return;

    try {
      await api.post(`/payments/refund/${paymentId}/`, { amount });
      alert("Refund initiated");
      // refresh rows?
    } catch (err: any) {
      alert(err.response?.data?.error || "Refund failed");
    }
  };

  if (loading) return <div style={{ padding: 40, color: "#888" }}>Loading payments…</div>;

  return (
    <div style={{ padding: "40px 60px" }}>
      <h1 style={{ marginBottom: "30px", fontSize: "2rem" }}>Payments</h1>

      <div style={{ overflowX: "auto", borderRadius: "8px", border: "1px solid #333" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", background: "#1e1e1e" }}>
          <thead>
            <tr style={{ background: "#000", textAlign: "left" }}>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>ID</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>User</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Amount</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Status</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Date</th>
              <th style={{ padding: "16px", color: "#888", fontSize: "0.85rem", textTransform: "uppercase" }}>Action</th>
            </tr>
          </thead>

          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={6} style={{ padding: 24, textAlign: "center", color: "#666" }}>No payments found</td></tr>
            ) : (
              rows.map(p => (
                <tr key={p.id} style={{ borderBottom: "1px solid #333" }}>
                  <td style={{ padding: "16px", color: "#fff" }}>{p.id}</td>
                  <td style={{ padding: "16px", color: "#fff" }}>{p.user_phone}</td>
                  <td style={{ padding: "16px", color: "#fff", fontWeight: 600 }}>₹{p.amount.toFixed(2)}</td>
                  <td style={{ padding: "16px" }}>
                    <span
                      style={{
                        padding: "4px 8px",
                        borderRadius: "4px",
                        fontSize: "0.75rem",
                        background: p.status === "SUCCESS" || p.status === "COMPLETED" ? "#2ecc7120" : "#333",
                        color: p.status === "SUCCESS" || p.status === "COMPLETED" ? "#2ecc71" : "#ccc",
                        border: `1px solid ${p.status === "SUCCESS" || p.status === "COMPLETED" ? "#2ecc71" : "#555"}`,
                      }}
                    >
                      {p.status}
                    </span>
                  </td>
                  <td style={{ padding: "16px", color: "#aaa" }}>{new Date(p.created_at).toLocaleString()}</td>
                  <td style={{ padding: "16px" }}>
                    {(p.status === "SUCCESS" || p.status === "COMPLETED") && (
                      <button
                        onClick={() => handleRefund(p.id)}
                        style={{
                          background: "red", color: "white", padding: "6px 12px",
                          border: "none", borderRadius: "4px", cursor: "pointer", fontSize: "0.85rem"
                        }}
                      >
                        Refund
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

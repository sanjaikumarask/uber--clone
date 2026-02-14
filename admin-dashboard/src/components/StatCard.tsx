interface Props {
  label: string;
  value: number;
}

export default function StatCard({ label, value }: Props) {
  return (
    <div
      style={{
        background: "var(--bg-secondary)",
        padding: "20px",
        borderRadius: "12px",
        border: "1px solid var(--border-color)",
        color: "var(--text-primary)",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
        {label}
      </div>
      <div style={{ fontSize: "2rem", fontWeight: 700 }}>
        {value.toLocaleString()}
      </div>
    </div>
  );
}

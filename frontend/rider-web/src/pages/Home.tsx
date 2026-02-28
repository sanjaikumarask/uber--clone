import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "80vh" }}>
      <div className="card text-center" style={{ width: "100%", maxWidth: "500px", padding: "var(--spacing-xl)", background: "rgba(255, 255, 255, 0.03)", backdropFilter: "blur(20px)", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: "24px" }}>
        <h1 className="text-h1" style={{ marginBottom: "var(--spacing-md)", color: "var(--color-primary)" }}>
          Where to?
        </h1>
        <p className="text-body" style={{ color: "var(--color-text-muted)", marginBottom: "var(--spacing-lg)" }}>
          Get a reliable ride in minutes.
        </p>

        <button
          onClick={() => navigate("/book")}
          className="btn btn-primary"
          style={{
            fontSize: "var(--font-size-lg)",
            padding: "var(--spacing-md) var(--spacing-xl)",
            width: "100%",
            borderRadius: "12px",
            fontWeight: "700"
          }}
        >
          Request a Ride
        </button>

        <div style={{ display: "flex", gap: "12px", marginTop: "var(--spacing-lg)" }}>
          <button
            onClick={() => navigate("/offers")}
            className="btn"
            style={{ flex: 1, background: "rgba(255,255,255,0.05)", color: "#fff", border: "1px solid rgba(255,255,255,0.1)" }}
          >
            🎁 Offers
          </button>
          <button
            onClick={() => navigate("/support")}
            className="btn"
            style={{ flex: 1, background: "rgba(255,255,255,0.05)", color: "#fff", border: "1px solid rgba(255,255,255,0.1)" }}
          >
            🎧 Support
          </button>
        </div>
      </div>
    </div>
  );
}

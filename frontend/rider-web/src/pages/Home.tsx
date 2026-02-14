import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="container" style={{ alignItems: "center", justifyContent: "center", height: "80vh" }}>
      <div className="card text-center" style={{ width: "100%", padding: "var(--spacing-xl)" }}>
        <h1 className="text-h1" style={{ marginBottom: "var(--spacing-md)" }}>
          Where to?
        </h1>
        <p className="text-body" style={{ color: "var(--color-text-muted)", marginBottom: "var(--spacing-lg)" }}>
          Get a reliable ride in minutes.
        </p>

        <button
          onClick={() => navigate("/book")}
          className="btn btn-primary"
          style={{ fontSize: "var(--font-size-lg)", padding: "var(--spacing-md) var(--spacing-xl)" }}
        >
          Request a Ride
        </button>
      </div>
    </div>
  );
}

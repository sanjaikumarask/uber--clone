import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";

export default function Layout() {
    const navigate = useNavigate();
    const location = useLocation();

    const handleLogout = () => {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        navigate("/login");
    };

    const linkStyle = (path: string) => ({
        display: "block",
        padding: "10px 12px",
        borderRadius: "6px",
        color: location.pathname === path ? "#ffffff" : "#b3b3b3",
        background: location.pathname === path ? "#1e1e1e" : "transparent",
        textDecoration: "none",
        fontWeight: location.pathname === path ? 600 : 400,
        marginBottom: 4,
    });

    return (
        <div style={{ display: "flex", minHeight: "100vh", width: "100%" }}>
            {/* SIDEBAR */}
            <aside style={{ width: 260, background: "#000000", padding: 24, display: "flex", flexDirection: "column" }}>
                <h2 style={{ marginBottom: 32, fontSize: "1.5rem", letterSpacing: "-0.5px" }}>Uber Admin</h2>

                <nav style={{ flex: 1 }}>
                    <Link to="/" style={linkStyle("/")}>Overview</Link>
                    <Link to="/drivers" style={linkStyle("/drivers")}>Drivers</Link>
                    <Link to="/rides" style={linkStyle("/rides")}>Rides</Link>
                    <Link to="/payments" style={linkStyle("/payments")}>Payments</Link>
                    <Link to="/live-map" style={linkStyle("/live-map")}>Live Map</Link>
                </nav>

                <div style={{ borderTop: "1px solid #333", paddingTop: 20 }}>
                    <button
                        onClick={handleLogout}
                        style={{
                            background: "#e74c3c", color: "white", border: "none",
                            padding: "10px", width: "100%", borderRadius: "6px", fontWeight: 600
                        }}
                    >
                        Logout
                    </button>
                </div>
            </aside>

            {/* MAIN CONTENT */}
            <main style={{ flex: 1, background: "var(--bg-primary)", overflowY: "auto" }}>
                <Outlet />
            </main>
        </div>
    );
}

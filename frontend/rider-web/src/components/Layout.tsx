import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../domains/auth/auth.store";

export default function Layout() {
    const navigate = useNavigate();
    const location = useLocation();
    const logout = useAuthStore((s) => s.logout);
    const user = useAuthStore((s) => s.user);

    const handleLogout = () => {
        logout();
        navigate("/login");
    };

    // Hide header on certain pages if needed, but usually consistent is better
    const showHeader = !["/ride/searching", "/ride/tracking", "/book"].includes(location.pathname);

    return (
        <div className="flex flex-col min-h-screen" style={{ background: "var(--color-background)" }}>
            {showHeader && (
                <nav className="nav-bar animate-fade" style={{ borderBottom: "1px solid var(--color-border)", background: "rgba(0,0,0,0.3)", backdropFilter: "blur(10px)" }}>
                    <div className="logo" onClick={() => navigate("/home")} style={{ cursor: "pointer" }}>
                        Uber <span>RIDER</span>
                    </div>

                    <div className="flex items-center gap-md">
                        {user && (
                            <div className="flex items-center gap-md">
                                <div className="flex flex-col items-end hide-mobile">
                                    <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>Welcome back</span>
                                    <span style={{ fontSize: "14px", fontWeight: "600" }}>{user.first_name}</span>
                                </div>
                                <div
                                    style={{
                                        width: "40px",
                                        height: "40px",
                                        borderRadius: "50%",
                                        background: "var(--gradient-primary)",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        fontWeight: "bold",
                                        boxShadow: "var(--shadow-accent)"
                                    }}
                                >
                                    {user.first_name?.[0] || "U"}
                                </div>
                                <button
                                    onClick={handleLogout}
                                    className="btn-secondary"
                                    style={{ padding: "8px 16px", borderRadius: "var(--radius-full)", fontSize: "14px" }}
                                >
                                    Sign Out
                                </button>
                            </div>
                        )}
                    </div>
                </nav>
            )}

            <main className="flex-1 flex flex-col">
                <Outlet />
            </main>

            <style>{`
        @media (max-width: 480px) {
          .hide-mobile { display: none; }
        }
      `}</style>
        </div>
    );
}


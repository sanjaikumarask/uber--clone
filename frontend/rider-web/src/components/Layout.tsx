import { Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "../domains/auth/auth.store";

export default function Layout() {
    const navigate = useNavigate();
    const logout = useAuthStore((s) => s.logout);
    const user = useAuthStore((s) => s.user);

    const handleLogout = () => {
        logout();
        navigate("/login");
    };

    return (
        <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
            <header
                style={{
                    padding: "var(--spacing-md)",
                    borderBottom: "1px solid var(--color-border)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    backgroundColor: "var(--color-surface)",
                }}
            >
                <div style={{ fontWeight: "bold", fontSize: "var(--font-size-lg)" }}>
                    Uber <span style={{ color: "var(--color-accent)", fontSize: "0.8em" }}>RIDER</span>
                </div>

                {user && (
                    <div style={{ display: "flex", gap: "var(--spacing-md)", alignItems: "center" }}>
                        <span className="text-sm">Hi, {user.first_name}</span>
                        <button
                            onClick={handleLogout}
                            className="btn btn-secondary"
                            style={{ padding: "4px 12px", fontSize: "var(--font-size-sm)" }}
                        >
                            Logout
                        </button>
                    </div>
                )}
            </header>

            <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>
                <Outlet />
            </main>
        </div>
    );
}

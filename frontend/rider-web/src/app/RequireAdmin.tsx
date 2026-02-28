import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../domains/auth/auth.store";

export default function RequireAdmin() {
    const user = useAuthStore((s) => s.user);

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    if (user.role !== "admin") {
        return <Navigate to="/home" replace />;
    }

    return <Outlet />;
}

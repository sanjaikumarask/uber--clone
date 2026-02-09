import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/auth.store";
import { useEffect, useState } from "react";

export default function RequireAuth({
  children,
}: {
  children: JSX.Element;
}) {
  const token = useAuthStore((s) => s.token);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
  }, []);

  if (!ready) return null;

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../domains/auth/auth.store";
import { login as apiLogin } from "../domains/auth/auth.api";

export default function Login() {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.login);

  async function handleLogin() {
    if (!phone || !password) return;
    setIsLoading(true);
    try {
      const data = await apiLogin(phone, password);
      setAuth(data);
      navigate("/home", { replace: true });
    } catch (err: any) {
      console.error("Login failed:", err);
      const errorMsg = err.response?.data?.non_field_errors?.[0] || "Invalid credentials";
      alert(errorMsg);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="container" style={{ justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
      <div className="glass-card animate-fade w-full" style={{ padding: "var(--spacing-xxl) var(--spacing-xl)" }}>
        <div className="text-center" style={{ marginBottom: "var(--spacing-xl)" }}>
          <h1 className="text-huge" style={{ marginBottom: "var(--spacing-xs)" }}>
            Welcome<span>.</span>
          </h1>
          <p className="text-sm">Sign in to start your journey</p>
        </div>

        <div className="flex flex-col gap-md">
          <div className="input-group">
            <input
              className="input"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Phone Number"
              autoFocus
              type="tel"
            />
          </div>

          <div className="input-group">
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
            />
          </div>

          <button
            onClick={handleLogin}
            className="btn btn-primary"
            style={{ marginTop: "var(--spacing-md)" }}
            disabled={isLoading}
          >
            {isLoading ? "Signing in..." : "Sign In"}
          </button>
        </div>

        <div className="text-center" style={{ marginTop: "var(--spacing-xl)" }}>
          <p className="text-sm">
            Don't have an account? <span className="text-accent" style={{ cursor: "pointer", fontWeight: "600" }}>Sign Up</span>
          </p>
        </div>
      </div>
    </div>
  );
}


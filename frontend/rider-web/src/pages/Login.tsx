import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../domains/auth/auth.store";

export default function Login() {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const loginStore = useAuthStore((s) => s.login);

  async function handleLogin() {
    const res = await fetch("/api/users/login/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone, password }),
    });

    if (!res.ok) {
      alert("Invalid credentials");
      return;
    }

    const data = await res.json();

    // 🔥 THIS WAS MISSING OR WRONG
    loginStore(data);

    // 🔥 THIS WAS MISSING
    navigate("/home", { replace: true });
  }

  return (
    <div className="container" style={{ justifyContent: "center", minHeight: "80vh" }}>
      <div className="card">
        <h1 className="text-h1" style={{ marginBottom: "var(--spacing-lg)", textAlign: "center" }}>
          Login
        </h1>

        <div className="input-group">
          <input
            className="input"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Phone Number"
            autoFocus
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
        >
          Login
        </button>
      </div>
    </div>
  );
}

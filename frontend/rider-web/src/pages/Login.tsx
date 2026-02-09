import { useState } from "react";
import { login } from "../auth/auth.service";
import { useAuthStore } from "../store/auth.store";
import { useNavigate } from "react-router-dom";



export default function Login(): JSX.Element {
  const [username, setUsername] = useState(""); // phone OR username
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setToken = useAuthStore((s) => s.setToken);
  const navigate = useNavigate();

  const submit = async () => {
    try {
      setLoading(true);
      setError(null);

      const res = await login(username, password);

      // SimpleJWT access token
      setToken(res.data.access);

      navigate("/home");
    } catch {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Rider Login</h2>

      <input
        placeholder="Phone or Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <button disabled={loading} onClick={submit}>
        {loading ? "Logging in..." : "Login"}
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}
    </div>
  );
}

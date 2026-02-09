import { useState } from "react";
import { login } from "../../api/auth.api";
import { useAuthStore } from "../../store/auth.store";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const auth = useAuthStore();
  const navigate = useNavigate();

  const submit = async () => {
    const token = await login(username, password);
    auth.login(token);
    navigate("/driver/home");
  };

  return (
    <div>
      <h1>Driver Login</h1>
      <input placeholder="username" onChange={(e) => setUsername(e.target.value)} />
      <input type="password" placeholder="password" onChange={(e) => setPassword(e.target.value)} />
      <button onClick={submit}>Login</button>
    </div>
  );
}

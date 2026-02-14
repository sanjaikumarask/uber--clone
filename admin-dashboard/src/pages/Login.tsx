import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export default function Login() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const navigate = useNavigate();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const response = await api.post("/users/admin-login/", {
                username,
                password,
            });
            localStorage.setItem("access", response.data.access);
            localStorage.setItem("refresh", response.data.refresh);
            navigate("/");
        } catch (err: any) {
            console.error("Login Error:", err);
            const msg = err.response?.data?.detail || err.response?.data?.non_field_errors?.[0] || "Invalid credentials or not an admin";
            setError(msg);
        }
    };

    return (
        <div style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            height: "100vh",
            background: "#121212"
        }}>
            <div style={{
                width: "100%",
                maxWidth: "400px",
                padding: "40px",
                background: "#1e1e1e",
                borderRadius: "12px",
                border: "1px solid #333",
                boxShadow: "0 4px 20px rgba(0,0,0,0.5)"
            }}>
                <h1 style={{ marginBottom: "30px", textAlign: "center", fontSize: "2rem" }}>Admin Login</h1>

                <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    <input
                        placeholder="Username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        style={{
                            padding: "14px",
                            background: "#2c2c2c",
                            border: "1px solid #444",
                            borderRadius: "6px",
                            color: "white",
                            fontSize: "1rem",
                            outline: "none"
                        }}
                    />
                    <input
                        type="password"
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        style={{
                            padding: "14px",
                            background: "#2c2c2c",
                            border: "1px solid #444",
                            borderRadius: "6px",
                            color: "white",
                            fontSize: "1rem",
                            outline: "none"
                        }}
                    />

                    {error && <p style={{ color: "#e74c3c", fontSize: "0.9rem", margin: 0 }}>{error}</p>}

                    <button
                        type="submit"
                        style={{
                            padding: "14px",
                            cursor: "pointer",
                            background: "white",
                            color: "black",
                            fontWeight: 600,
                            borderRadius: "6px",
                            border: "none",
                            fontSize: "1rem",
                            marginTop: "10px"
                        }}
                    >
                        Login
                    </button>
                </form>
            </div>
        </div>
    );
}

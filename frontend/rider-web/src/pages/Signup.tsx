import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { register as apiRegister } from "../domains/auth/auth.api";

export default function Signup() {
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [phone, setPhone] = useState("");
    const [password, setPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    async function handleSignup() {
        if (!phone || !password || !firstName) {
            alert("First name, phone and password are required.");
            return;
        }

        setIsLoading(true);
        try {
            await apiRegister(firstName, lastName, phone, password, "rider");
            alert("Account created successfully! Please sign in.");
            navigate("/login", { replace: true });
        } catch (err: any) {
            console.error("Signup failed:", err);
            // Django REST Framework validations usually come back like { phone: ["already exists"] }
            const errors = err.response?.data;
            if (errors) {
                const errorStrings = Object.entries(errors)
                    .map(([key, val]) => `${key}: ${val}`)
                    .join("\n");
                alert(`Validation Error:\n${errorStrings}`);
            } else {
                alert("Registration failed. Please try again.");
            }
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <div className="container" style={{ justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
            <div className="glass-card animate-fade w-full" style={{ padding: "var(--spacing-xxl) var(--spacing-xl)" }}>
                <div className="text-center" style={{ marginBottom: "var(--spacing-xl)" }}>
                    <h1 className="text-huge" style={{ marginBottom: "var(--spacing-xs)" }}>
                        Join Us<span>.</span>
                    </h1>
                    <p className="text-sm">Create an account to start riding</p>
                </div>

                <div className="flex flex-col gap-md">
                    <div className="flex gap-sm w-full">
                        <div className="input-group" style={{ flex: 1 }}>
                            <input
                                className="input"
                                value={firstName}
                                onChange={(e) => setFirstName(e.target.value)}
                                placeholder="First Name"
                                autoFocus
                            />
                        </div>
                        <div className="input-group" style={{ flex: 1 }}>
                            <input
                                className="input"
                                value={lastName}
                                onChange={(e) => setLastName(e.target.value)}
                                placeholder="Last Name"
                            />
                        </div>
                    </div>

                    <div className="input-group">
                        <input
                            className="input"
                            value={phone}
                            onChange={(e) => setPhone(e.target.value)}
                            placeholder="Phone Number (e.g. +91 999...)"
                            type="tel"
                        />
                    </div>

                    <div className="input-group">
                        <input
                            className="input"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Password (minimum 8 characters)"
                        />
                    </div>

                    <button
                        onClick={handleSignup}
                        className="btn btn-primary"
                        style={{ marginTop: "var(--spacing-md)" }}
                        disabled={isLoading}
                    >
                        {isLoading ? "Creating Account..." : "Sign Up"}
                    </button>
                </div>

                <div className="text-center" style={{ marginTop: "var(--spacing-xl)" }}>
                    <p className="text-sm">
                        Already have an account? <span className="text-accent" style={{ cursor: "pointer", fontWeight: "600" }} onClick={() => navigate("/login")}>Sign In</span>
                    </p>
                </div>
            </div>
        </div>
    );
}

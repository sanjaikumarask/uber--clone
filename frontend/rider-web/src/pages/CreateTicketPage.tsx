
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export default function CreateTicketPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const rideId = location.state?.rideId;

    const [reason, setReason] = useState("OTHER");
    const [description, setDescription] = useState("");
    const [submitting, setSubmitting] = useState(false);

    if (!rideId) {
        return (
            <div style={styles.container}>
                <p>No ride selected. Please selecting a ride from your history.</p>
                <button onClick={() => navigate("/")} style={styles.btn}>Go Home</button>
            </div>
        );
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);

        try {
            const token = localStorage.getItem("access");
            const res = await fetch(`http://localhost:8000/api/supports/rides/${rideId}/ticket/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ reason, description })
            });

            if (res.ok) {
                alert("Ticket created successfully!");
                navigate("/support");
            } else {
                const err = await res.json();
                alert(err.error || "Failed to create ticket");
            }
        } catch (error) {
            console.error(error);
            alert("Error submitting ticket");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h2 style={styles.title}>Report an Issue</h2>
                <p style={styles.subtitle}>Ride #{rideId}</p>

                <form onSubmit={handleSubmit}>
                    <label style={styles.label}>Reason</label>
                    <select
                        style={styles.input}
                        value={reason}
                        onChange={e => setReason(e.target.value)}
                    >
                        <option value="OVERCHARGED">Overcharged</option>
                        <option value="DRIVER_MISCONDUCT">Driver Misconduct</option>
                        <option value="NO_SHOW_DISPUTE">No Show Dispute</option>
                        <option value="ROUTE_DEVIATION">Route Deviation</option>
                        <option value="OTHER">Other</option>
                    </select>

                    <label style={styles.label}>Description</label>
                    <textarea
                        style={{ ...styles.input, height: "100px" }}
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        placeholder="Describe what happened..."
                        required
                    />

                    <div style={styles.actions}>
                        <button type="button" onClick={() => navigate(-1)} style={styles.cancelBtn}>Cancel</button>
                        <button type="submit" disabled={submitting} style={styles.submitBtn}>
                            {submitting ? "Submitting..." : "Submit Ticket"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

const styles: Record<string, React.CSSProperties> = {
    container: {
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#000",
        color: "#fff",
        fontFamily: "'Uber Move', sans-serif"
    },
    card: {
        background: "#161616",
        padding: "30px",
        borderRadius: "12px",
        width: "100%",
        maxWidth: "500px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.5)"
    },
    title: {
        margin: "0 0 5px",
        fontSize: "24px"
    },
    subtitle: {
        margin: "0 0 20px",
        color: "#aaa",
        fontSize: "14px"
    },
    label: {
        display: "block",
        marginBottom: "5px",
        fontSize: "14px",
        fontWeight: "bold",
        color: "#ddd"
    },
    input: {
        width: "100%",
        padding: "12px",
        marginBottom: "20px",
        background: "#222",
        border: "1px solid #333",
        borderRadius: "8px",
        color: "#fff",
        fontSize: "16px"
    },
    actions: {
        display: "flex",
        gap: "10px",
        marginTop: "10px"
    },
    cancelBtn: {
        flex: 1,
        padding: "12px",
        background: "transparent",
        border: "1px solid #333",
        color: "#fff",
        borderRadius: "8px",
        cursor: "pointer"
    },
    submitBtn: {
        flex: 1,
        padding: "12px",
        background: "#22c55e",
        border: "none",
        color: "#fff",
        borderRadius: "8px",
        fontWeight: "bold",
        cursor: "pointer"
    },
    btn: {
        padding: "10px 20px",
        marginTop: "10px",
        cursor: "pointer"
    }
};


import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/http";

interface SupportTicket {
    id: number;
    reason: string;
    description: string;
    status: "OPEN" | "RESOLVED" | "REJECTED";
    created_at: string;
    resolution_note?: string;
}



export default function SupportPage() {
    const navigate = useNavigate();
    const [tickets, setTickets] = useState<SupportTicket[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get("/supports/tickets/")
            .then(res => {
                if (Array.isArray(res.data)) {
                    setTickets(res.data);
                }
            })
            .catch(err => console.error(err))
            .finally(() => setLoading(false));
    }, []);
    return (
        <div style={styles.container}>
            <header style={styles.header}>
                <button onClick={() => navigate(-1)} style={styles.backBtn}>←</button>
                <h1 style={styles.title}>Support Tickets</h1>
            </header>

            <div style={styles.content}>
                {loading ? (
                    <p style={{ color: '#aaa' }}>Loading tickets...</p>
                ) : tickets.length === 0 ? (
                    <div style={styles.empty}>
                        <p>No support tickets found.</p>
                        <p style={{ fontSize: '12px', color: '#666' }}>
                            You can report reporting issues from your ride history.
                        </p>
                    </div>
                ) : (
                    <div style={styles.list}>
                        {tickets.map(ticket => (
                            <div key={ticket.id} style={styles.card}>
                                <div style={styles.cardHeader}>
                                    <span style={styles.reason}>{ticket.reason.replace("_", " ")}</span>
                                    <span style={{
                                        ...styles.status,
                                        background: ticket.status === "OPEN" ? "#eab308" :
                                            ticket.status === "RESOLVED" ? "#22c55e" : "#ef4444"
                                    }}>
                                        {ticket.status}
                                    </span>
                                </div>
                                <p style={styles.date}>{new Date(ticket.created_at).toLocaleDateString()}</p>
                                <p style={styles.desc}>"{ticket.description}"</p>

                                {ticket.resolution_note && (
                                    <div style={styles.response}>
                                        <strong>Support Response:</strong>
                                        <p>{ticket.resolution_note}</p>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

const styles: Record<string, React.CSSProperties> = {
    container: {
        minHeight: "100vh",
        background: "#000",
        color: "#fff",
        fontFamily: "'Uber Move', sans-serif"
    },
    header: {
        padding: "20px",
        display: "flex",
        alignItems: "center",
        gap: "15px",
        borderBottom: "1px solid #222"
    },
    backBtn: {
        background: "none",
        border: "none",
        color: "#fff",
        fontSize: "24px",
        cursor: "pointer"
    },
    title: {
        fontSize: "20px",
        margin: 0
    },
    content: {
        padding: "20px",
        maxWidth: "600px",
        margin: "0 auto"
    },
    empty: {
        textAlign: "center",
        color: "#aaa",
        marginTop: "50px"
    },
    list: {
        display: "flex",
        flexDirection: "column",
        gap: "15px"
    },
    card: {
        background: "#161616",
        padding: "15px",
        borderRadius: "8px",
        border: "1px solid #333"
    },
    cardHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "5px"
    },
    reason: {
        fontWeight: "bold",
        textTransform: "capitalize"
    },
    status: {
        fontSize: "10px",
        padding: "2px 6px",
        borderRadius: "10px",
        color: "#000",
        fontWeight: "bold"
    },
    date: {
        fontSize: "12px",
        color: "#666",
        marginBottom: "10px"
    },
    desc: {
        fontSize: "14px",
        color: "#ddd",
        fontStyle: "italic",
        marginBottom: "10px"
    },
    response: {
        background: "#222",
        padding: "10px",
        borderRadius: "6px",
        marginTop: "10px",
        fontSize: "13px"
    }
};

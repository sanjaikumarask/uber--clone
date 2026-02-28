import { useEffect, useState } from "react";
import { type Offer, getActiveOffers } from "../services/offerService";
import { useNavigate } from "react-router-dom";

export default function OffersPage() {
    const [offers, setOffers] = useState<Offer[]>([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        fetchOffers();
    }, []);

    const fetchOffers = async () => {
        try {
            const data = await getActiveOffers("Chennai");
            setOffers(data);
        } catch (error) {
            console.error("Failed to load offers", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return (
        <div className="container justify-center items-center" style={{ minHeight: "80vh" }}>
            <div className="animate-fade" style={{ color: "var(--color-accent)", fontWeight: "600" }}>Loading exclusive offers...</div>
        </div>
    );

    return (
        <div className="container">
            <div className="flex items-center gap-md" style={{ marginBottom: "var(--spacing-xl)", marginTop: "var(--spacing-lg)" }}>
                <button onClick={() => navigate(-1)} className="btn-secondary" style={{ width: "40px", height: "40px", borderRadius: "50%", padding: 0 }}>←</button>
                <h1 className="text-h1">Special Offers</h1>
            </div>

            <div className="flex flex-col gap-lg">
                {offers.length === 0 ? (
                    <div className="glass-card text-center" style={{ padding: "var(--spacing-xxl)" }}>
                        <div style={{ fontSize: "48px", marginBottom: "var(--spacing-md)" }}>🎁</div>
                        <p className="text-body" style={{ color: "var(--color-text-muted)" }}>
                            No active offers available in Chennai right now. Check back soon!
                        </p>
                    </div>
                ) : (
                    <div className="flex flex-col gap-md">
                        {offers.map((offer) => (
                            <div key={offer.id} className="glass-card animate-fade" style={{ padding: "var(--spacing-lg)" }}>
                                <div className="flex justify-between items-start" style={{ marginBottom: "var(--spacing-sm)" }}>
                                    <div>
                                        <h3 className="text-h2" style={{ marginBottom: "var(--spacing-xs)" }}>{offer.title}</h3>
                                        <p className="text-sm" style={{ lineHeight: "1.4" }}>{offer.description}</p>
                                    </div>
                                    <div className="glass" style={{
                                        padding: "8px 12px",
                                        borderRadius: "var(--radius-md)",
                                        background: "var(--gradient-primary)",
                                        color: "#fff",
                                        fontWeight: "800",
                                        fontSize: "1.1rem",
                                        boxShadow: "var(--shadow-accent)"
                                    }}>
                                        {offer.discount_type === "FLAT" ? "₹" : ""}
                                        {offer.value}
                                        {offer.discount_type === "PERCENTAGE" ? "%" : ""} OFF
                                    </div>
                                </div>

                                <div className="flex justify-between items-center" style={{ marginTop: "var(--spacing-lg)", paddingTop: "var(--spacing-md)", borderTop: "1px solid var(--color-border)" }}>
                                    <div className="flex flex-col">
                                        <span style={{ fontSize: "10px", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "1px" }}>Valid until</span>
                                        <span className="text-sm" style={{ fontWeight: "600" }}>{new Date(offer.valid_to).toLocaleDateString()}</span>
                                    </div>
                                    <button
                                        className="btn btn-primary"
                                        style={{ width: "auto", padding: "10px 24px" }}
                                        onClick={() => alert(`Offer Applied: ${offer.title}`)}
                                    >
                                        Use Offer
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}


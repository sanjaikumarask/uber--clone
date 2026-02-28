import { useState, useEffect, type CSSProperties } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useRideStore } from "../domains/rides/ride.store";
import { api } from "../services/http";

export default function RideCompleted() {
  const navigate = useNavigate();
  const { rideId: paramRideId } = useParams();
  const { rideId: storeRideId, fare: storeFare, reset } = useRideStore();

  const [loading, setLoading] = useState(true);
  const [rideData, setRideData] = useState<any>(null);
  const [paying, setPaying] = useState(false);
  const [paid, setPaid] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scriptLoaded, setScriptLoaded] = useState(false);
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const effectiveRideId = paramRideId || storeRideId?.toString();

  // 1. Fetch Ride Details if needed or refresh
  useEffect(() => {
    if (!effectiveRideId) {
      navigate("/");
      return;
    }

    const fetchRide = async () => {
      try {
        setLoading(true);
        const res = await api.get(`/rides/${effectiveRideId}/`);
        setRideData(res.data);
      } catch (err: any) {
        console.error("Failed to fetch ride details:", err);
        setError("Could not retrieve ride information. Please refresh.");
      } finally {
        setLoading(false);
      }
    };

    fetchRide();
  }, [effectiveRideId, navigate]);

  // 2. Load Razorpay Script
  useEffect(() => {
    if (document.getElementById("razorpay-sdk")) {
      setScriptLoaded(true);
      return;
    }
    const script = document.createElement("script");
    script.id = "razorpay-sdk";
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => setScriptLoaded(true);
    script.onerror = () => setError("Failed to load Razorpay SDK");
    document.body.appendChild(script);
  }, []);

  const handleDone = () => {
    reset();
    navigate("/");
  };

  const currentFare = rideData?.final_fare || rideData?.base_fare || storeFare;

  const handlePay = async () => {
    if (!effectiveRideId || paid) return;
    setPaying(true);
    setError(null);

    try {
      // 1. Create Razorpay Order on Backend
      const orderRes = await api.post(`/payments/create/${effectiveRideId}/`);
      const { order_id, amount, currency, key } = orderRes.data;

      if (!key) {
        setError("Payment gateway not configured. Use the simulation button below to complete payment.");
        return;
      }

      // 2. Open Razorpay Checkout
      const options = {
        key,
        amount,
        currency,
        name: "Uber Clone",
        description: `Ride #${effectiveRideId}`,
        order_id,
        handler: async (response: any) => {
          try {
            setPaying(true);
            await api.post("/payments/verify/", {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            setPaid(true);
            setPaying(false);
          } catch (err: any) {
            console.error("Verification failed:", err);
            setError("Payment verification failed. Please contact support.");
            setPaying(false);
          }
        },
        prefill: {},
        theme: { color: "#000000" },
        modal: {
          ondismiss: () => setPaying(false),
        }
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.on('payment.failed', (response: any) => {
        setError(response.error.description || "Payment failed");
        setPaying(false);
      });
      rzp.open();

    } catch (err: any) {
      console.error("Payment initiation failed:", err);
      const httpStatus = err.response?.status;
      const serverMsg = err.response?.data?.error || err.message || "Failed to initiate payment.";

      if (httpStatus === 503 || serverMsg.toLowerCase().includes("not configured")) {
        setError("Payment gateway not available. Use the simulation option below.");
      } else {
        setError(serverMsg);
      }
    } finally {
      setPaying(false);
    }
  };

  const handleBypass = async () => {
    if (!effectiveRideId) return;
    setPaying(true);
    try {
      await api.post(`/payments/simulate/${effectiveRideId}/`);
      setPaid(true);
    } catch (err: any) {
      console.error("Simulation failed:", err);
      setError("Simulation failed. Please check logs.");
    } finally {
      setPaying(false);
    }
  };

  const handleRatingSubmit = async () => {
    if (!effectiveRideId || !rating) return;
    setPaying(true);
    try {
      await api.post(`/rides/${effectiveRideId}/feedback/`, { rating, comment });
      setFeedbackSubmitted(true);
    } catch (err) {
      console.error("Feedback failed:", err);
      setError("Failed to submit feedback.");
    } finally {
      setPaying(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.page}>
        <div style={styles.card}>
          <p style={styles.subtitle}>Loading ride summary...</p>
        </div>
      </div>
    );
  }

  if (!effectiveRideId) return null;

  return (
    <div style={styles.page}>
      <div style={styles.card}>

        {/* HEADER ICON */}
        <div style={{ ...styles.iconContainer, background: paid ? "#22c55e" : "#eab308" }}>
          <span style={{ fontSize: "32px", color: "#fff" }}>
            {paid ? "✓" : "₹"}
          </span>
        </div>

        {/* TITLE */}
        <h1 style={styles.title}>
          {paid ? "Payment Successful!" : "Ride Completed"}
        </h1>
        <p style={styles.subtitle}>
          {paid
            ? "Receipt has been sent to your email."
            : "Please settle the fare to continue."}
        </p>

        {/* ERROR MESSAGE */}
        {error && (
          <div className="bg-red-900/40 border border-red-500/50 p-3 rounded-lg flex flex-col gap-3 mb-6">
            <div className="flex items-start gap-3">
              <span className="text-red-500 shrink-0 mt-0.5" style={{ fontSize: '1.2rem' }}>⚠️</span>
              <span className="text-xs text-red-200 leading-relaxed font-medium">{error}</span>
            </div>

            {(error.toLowerCase().includes("simulation") || error.toLowerCase().includes("gateway not available")) && (
              <button
                onClick={handleBypass}
                disabled={paying}
                className="text-[10px] font-bold text-yellow-400 hover:text-yellow-300 uppercase tracking-wider text-left pl-8 transition-colors"
                id="bypass-payment-btn"
              >
                {paying ? "Processing..." : "→ Simulate Payment (Dev Mode)"}
              </button>
            )}
          </div>
        )}
        {/* FARE BOX */}
        <div style={styles.fareSummaryBox}>
          <p style={styles.fareSummaryLabel}>TOTAL FARE</p>
          <p style={styles.fareSummaryValue}>₹{Number(currentFare || 0).toFixed(2)}</p>
        </div>



        {/* ACTION BUTTONS */}
        {!paid ? (
          <>
            <button
              onClick={handlePay}
              disabled={paying || !scriptLoaded}
              style={{
                ...styles.button,
                backgroundColor: paying ? "#6b7280" : "#000",
                cursor: paying ? "not-allowed" : "pointer"
              }}
            >
              {paying ? "Processing..." : "Pay Now"}
            </button>
          </>
        ) : (
          <div style={styles.ratingSection}>
            <h3 style={styles.ratingTitle}>Rate your Driver</h3>
            <div style={styles.stars}>
              {[1, 2, 3, 4, 5].map(num => (
                <span
                  key={num}
                  onClick={() => setRating(num)}
                  style={{
                    ...styles.star,
                    color: rating && rating >= num ? "#f59e0b" : "#333"
                  }}
                >
                  ★
                </span>
              ))}
            </div>
            <textarea
              placeholder="Leave a comment..."
              value={comment}
              onChange={e => setComment(e.target.value)}
              style={styles.commentInput}
            />
            {feedbackSubmitted ? (
              <button onClick={handleDone} style={styles.backHomeBtn}>
                Done
              </button>
            ) : (
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={handleRatingSubmit}
                  disabled={!rating || paying}
                  style={styles.button}
                >
                  {paying ? "Submitting..." : "Submit Rating"}
                </button>
                <button
                  onClick={handleDone}
                  style={{ ...styles.button, backgroundColor: 'transparent', border: '1px solid #333' }}
                >
                  Skip
                </button>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: "100vh",
    background: "#000000",
    fontFamily: "'Uber Move', sans-serif"
  },
  card: {
    background: "#161616",
    padding: "40px 30px",
    borderRadius: "20px",
    boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
    textAlign: "center",
    width: "100%",
    maxWidth: "380px",
    color: "#fff",
    border: "1px solid #333",
  },
  iconContainer: {
    width: "80px",
    height: "80px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    margin: "0 auto 24px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.3)"
  },
  title: {
    fontSize: "24px",
    fontWeight: 800,
    margin: "0 0 8px",
    color: "#fff"
  },
  subtitle: {
    fontSize: "15px",
    color: "#AFAFAF",
    margin: "0 0 30px",
    lineHeight: 1.5
  },
  fareSummaryBox: {
    background: "#222",
    padding: "20px",
    borderRadius: "12px",
    margin: "0 0 30px",
    border: "1px solid #333"
  },
  fareSummaryLabel: {
    fontSize: "12px",
    fontWeight: 700,
    color: "#999",
    letterSpacing: "1px",
    margin: "0 0 8px",
    textTransform: "uppercase"
  },
  fareSummaryValue: {
    fontSize: "36px",
    fontWeight: 800,
    color: "#fff",
    margin: 0
  },
  backHomeBtn: {
    width: "100%",
    padding: "16px",
    backgroundColor: "#22c55e",
    color: "#fff",
    border: "none",
    borderRadius: "12px",
    fontSize: "16px",
    fontWeight: 700,
    cursor: "pointer",
    transition: "transform 0.1s",
    boxShadow: "0 4px 12px rgba(34, 197, 94, 0.3)"
  },
  button: {
    width: "100%",
    padding: "16px",
    backgroundColor: "#276EF1",
    color: "#fff",
    border: "none",
    borderRadius: "12px",
    fontSize: "16px",
    fontWeight: 700,
    transition: "background 0.2s",
    cursor: "pointer"
  },
  errorBox: {
    background: "#7f1d1d",
    color: "#fecaca",
    padding: "12px",
    borderRadius: "8px",
    fontSize: "14px",
    marginBottom: "20px",
    textAlign: "left"
  },
  ratingSection: {
    marginTop: "20px",
    display: "flex",
    flexDirection: "column",
    gap: "15px"
  },
  ratingTitle: {
    fontSize: "18px",
    fontWeight: 700,
    margin: 0
  },
  stars: {
    display: "flex",
    justifyContent: "center",
    gap: "10px",
    fontSize: "30px"
  },
  star: {
    cursor: "pointer",
    transition: "color 0.2s"
  },
  commentInput: {
    width: "100%",
    minHeight: "80px",
    background: "#222",
    border: "1px solid #333",
    borderRadius: "8px",
    color: "#fff",
    padding: "10px",
    fontSize: "14px"
  }
};

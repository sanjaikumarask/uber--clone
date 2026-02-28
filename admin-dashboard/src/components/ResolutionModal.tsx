import React, { useState } from "react";

interface ResolutionModalProps {
    ride: any;
    onClose: () => void;
    onSubmit: (data: any) => void;
}

export default function ResolutionModal({ ride, onClose, onSubmit }: ResolutionModalProps) {
    const [reason, setReason] = useState("Driver not moving");
    const [refundAmount, setRefundAmount] = useState(ride?.payment_status === "CAPTURED" ? (ride.final_fare || ride.base_fare).toString() : "0");
    const [compAmount, setCompAmount] = useState("0");
    const [penaltyAmount, setPenaltyAmount] = useState("0");
    const [waiveFee, setWaiveFee] = useState(true);
    const [action, setAction] = useState("CANCEL");

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit({
            ride_id: ride.id,
            action,
            reason,
            refund_amount: parseFloat(refundAmount),
            driver_compensation: parseFloat(compAmount),
            penalty_amount: parseFloat(penaltyAmount),
            waive_fee: waiveFee
        });
    };

    return (
        <div style={styles.overlay}>
            <div style={styles.modal}>
                <div style={styles.header}>
                    <h2 style={styles.title}>Resolve Issue: Trip #{ride.id} {ride.rider_name ? `(${ride.rider_name})` : ""}</h2>
                    <button onClick={onClose} style={styles.closeBtn}>&times;</button>
                </div>

                <form onSubmit={handleSubmit} style={styles.form}>
                    <div style={styles.field}>
                        <label style={styles.label}>Action Type</label>
                        <select
                            value={action}
                            onChange={(e) => setAction(e.target.value)}
                            style={styles.select}
                        >
                            <option value="CANCEL">CANCEL RIDE & RESOLVE</option>
                            <option value="RESOLVE">RESOLVE ONLY (Stay as-is)</option>
                        </select>
                    </div>

                    <div style={styles.field}>
                        <label style={styles.label}>Reason for Resolution</label>
                        <select
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            style={styles.select}
                        >
                            <option value="Driver not moving">Driver not moving (Auto-Penalty ₹50)</option>
                            <option value="Rider no-show">Rider no-show</option>
                            <option value="Bad experience">Bad experience (Rating -0.2)</option>
                            <option value="System issue">System issue</option>
                            <option value="Other">Other / Manual Adjustment</option>
                        </select>
                    </div>

                    <div style={styles.grid}>
                        <div style={styles.field}>
                            <label style={styles.label}>Rider Refund (₹)</label>
                            <input
                                type="number"
                                value={refundAmount}
                                onChange={(e) => setRefundAmount(e.target.value)}
                                style={styles.input}
                                placeholder="0.00"
                            />
                            <span style={styles.hint}>Max: ₹{ride.final_fare || ride.base_fare}</span>
                        </div>

                        <div style={styles.field}>
                            <label style={styles.label}>Driver Compensation (₹)</label>
                            <input
                                type="number"
                                value={compAmount}
                                onChange={(e) => setCompAmount(e.target.value)}
                                style={styles.input}
                                placeholder="0.00"
                            />
                        </div>
                    </div>

                    <div style={styles.field}>
                        <label style={styles.label}>Manual Driver Penalty (₹)</label>
                        <input
                            type="number"
                            value={penaltyAmount}
                            onChange={(e) => setPenaltyAmount(e.target.value)}
                            style={styles.input}
                            placeholder="0.00"
                        />
                    </div>

                    <div style={styles.checkboxGroup}>
                        <input
                            type="checkbox"
                            id="waiveFee"
                            checked={waiveFee}
                            onChange={(e) => setWaiveFee(e.target.checked)}
                        />
                        <label htmlFor="waiveFee" style={styles.checkboxLabel}>Waive all platform fees for this ride</label>
                    </div>

                    <div style={styles.actions}>
                        <button type="button" onClick={onClose} style={styles.cancelBtn}>Discard</button>
                        <button type="submit" style={styles.submitBtn}>
                            Confirm Resolution
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

const styles: Record<string, React.CSSProperties> = {
    overlay: {
        position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: "rgba(0,0,0,0.8)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 10000,
    },
    modal: {
        backgroundColor: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "16px",
        width: "100%", maxWidth: "480px",
        padding: "24px",
        boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
    },
    header: {
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: "24px",
    },
    title: { fontSize: "18px", fontWeight: 800, color: "var(--text-1)" },
    closeBtn: {
        background: "none", border: "none", color: "var(--text-dim)",
        fontSize: "24px", cursor: "pointer",
    },
    form: { display: "flex", flexDirection: "column", gap: "20px" },
    field: { display: "flex", flexDirection: "column", gap: "8px" },
    label: { fontSize: "11px", fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.5px" },
    select: {
        padding: "10px 12px", borderRadius: "8px",
        backgroundColor: "var(--bg-3)", border: "1px solid var(--border)",
        color: "var(--text-1)", fontSize: "14px", outline: "none",
    },
    input: {
        padding: "10px 12px", borderRadius: "8px",
        backgroundColor: "var(--bg-3)", border: "1px solid var(--border)",
        color: "var(--text-1)", fontSize: "14px", outline: "none",
    },
    grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" },
    hint: { fontSize: "10px", color: "var(--accent)", marginTop: "2px" },
    checkboxGroup: { display: "flex", alignItems: "center", gap: "8px" },
    checkboxLabel: { fontSize: "13px", color: "var(--text-2)" },
    actions: { display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "12px" },
    cancelBtn: {
        padding: "10px 20px", borderRadius: "8px", border: "1px solid var(--border)",
        background: "transparent", color: "var(--text-2)", cursor: "pointer", fontSize: "13px", fontWeight: 600,
    },
    submitBtn: {
        padding: "10px 20px", borderRadius: "8px", border: "none",
        background: "var(--accent)", color: "#fff", cursor: "pointer", fontSize: "13px", fontWeight: 700,
        boxShadow: "0 4px 12px var(--accent-glow)",
    },
};

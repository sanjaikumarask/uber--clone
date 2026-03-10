import { useEffect, useState } from "react";
import { api } from "../services/api";

interface DriverDocument {
    id: number;
    type: string;
    status: string;
    file_path: string;
    rejection_reason: string;
}

interface PendingDriver {
    driver_id: number;
    name: string;
    phone: string;
    email: string;
    documents: DriverDocument[];
    created_at: string;
}

export default function Verification() {
    const [drivers, setDrivers] = useState<PendingDriver[]>([]);
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState<number | null>(null);
    const [selectedImg, setSelectedImg] = useState<string | null>(null);
    const [rejectionModal, setRejectionModal] = useState<{ isOpen: boolean, docId: number | null }>({ isOpen: false, docId: null });
    const [rejectionReason, setRejectionReason] = useState("");

    const fetchPending = () => {
        setLoading(true);
        api.get("/drivers/admin/drivers/pending/")
            .then(res => setDrivers(res.data))
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchPending();
    }, []);

    const updateDriverDocumentState = (docId: number, action: "approve" | "reject", reason?: string) => {
        setDrivers(prev => prev.map(d => {
            const updatedDocs = d.documents.map(doc => {
                if (doc.id === docId) {
                    return { ...doc, status: action === "approve" ? "APPROVED" : "REJECTED", rejection_reason: action === "reject" ? (reason || "") : "" };
                }
                return doc;
            });
            return { ...d, documents: updatedDocs };
        }));
    };

    const handleDocAction = async (docId: number, action: "approve" | "reject", reason?: string) => {
        try {
            await api.post(`/drivers/admin/documents/${docId}/approve/`, {
                action,
                reason: action === "reject" ? reason : ""
            });

            updateDriverDocumentState(docId, action, reason);

            if (rejectionModal.isOpen) setRejectionModal({ isOpen: false, docId: null });
        } catch (err) {
            alert("Action failed.");
        } finally {
            setRejectionReason("");
        }
    };

    const approveAll = async (driver: PendingDriver) => {
        const nonApprovedDocs = driver.documents.filter(d => d.status !== "APPROVED");
        setProcessing(driver.driver_id);
        try {
            for (const doc of nonApprovedDocs) {
                await api.post(`/drivers/admin/documents/${doc.id}/approve/`, { action: "approve" });
            }
            alert(`Driver ${driver.name} approved and activated!`);
            setDrivers(prev => prev.filter(d => d.driver_id !== driver.driver_id));
        } catch (err) {
            alert("Failed to approve all documents.");
        } finally {
            setProcessing(null);
        }
    };

    if (loading) {
        return (
            <div className="page" style={{ padding: "40px" }}>
                <div className="skeleton" style={{ height: 40, width: 300, marginBottom: 30 }} />
                <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24 }}>
                    {[1, 2].map(i => <div key={i} className="skeleton" style={{ height: 300 }} />)}
                </div>
            </div>
        );
    }

    return (
        <div className="page" style={{ padding: "40px" }}>
            <header className="page-header" style={{ marginBottom: "32px" }}>
                <div>
                    <h1 className="page-title">Driver Approvals</h1>
                    <p className="page-sub" style={{ color: "var(--text-dim)" }}>Review on-boarding documents and activate driver profiles.</p>
                </div>
                <div className="badge badge-blue" style={{ marginTop: "12px" }}>
                    {drivers.length} Drivers Waiting
                </div>
            </header>

            {drivers.length === 0 ? (
                <div className="card" style={{ padding: "80px 0", textAlign: "center", border: "1px dashed var(--border)" }}>
                    <div style={{ fontSize: "48px", marginBottom: "16px" }}>✔️</div>
                    <h2 style={{ fontSize: "1.5rem", marginBottom: "8px" }}>All Caught Up</h2>
                    <p style={{ color: "var(--text-dim)" }}>No pending driver registrations at the moment.</p>
                    <button className="btn-ghost" style={{ marginTop: "16px" }} onClick={fetchPending}>Refresh List</button>
                </div>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                    {drivers.map(driver => (
                        <div key={driver.driver_id} className="card animate-fade" style={{ padding: 0, overflow: "hidden", border: "1px solid var(--border)", borderRadius: "12px" }}>
                            {/* Driver Info Header */}
                            <div style={{ padding: "24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "rgba(255,255,255,0.02)" }}>
                                <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
                                    <div style={{ width: 56, height: 56, borderRadius: "50%", backgroundColor: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "24px", color: "#fff", fontWeight: 800 }}>
                                        {driver.name.charAt(0)}
                                    </div>
                                    <div>
                                        <h3 style={{ margin: 0, fontSize: "1.25rem" }}>{driver.name}</h3>
                                        <div style={{ display: "flex", gap: "15px", marginTop: "4px" }}>
                                            <span style={{ fontSize: "13px", color: "var(--text-dim)" }}>📱 {driver.phone}</span>
                                            <span style={{ fontSize: "13px", color: "var(--text-dim)" }}>📧 {driver.email}</span>
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    <button
                                        className="btn-primary"
                                        style={{ background: "var(--green)", minWidth: 160, borderRadius: "8px" }}
                                        onClick={() => approveAll(driver)}
                                        disabled={processing === driver.driver_id}
                                    >
                                        {processing === driver.driver_id ? "Activating..." : "Approve Driver"}
                                    </button>
                                </div>
                            </div>

                            {/* Documents Grid */}
                            <div style={{ padding: "24px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "20px" }}>
                                {["LICENSE", "RC", "INSURANCE"].map(type => {
                                    const doc = driver.documents.find(d => d.type === type);
                                    return (
                                        <div key={type} className="glass-card" style={{ padding: "16px", borderRadius: "10px", border: doc?.status === "REJECTED" ? "1px solid var(--red)" : "1px solid var(--border)" }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                                                <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent)", letterSpacing: 1 }}>{type}</span>
                                                <span className={`badge ${doc?.status === "APPROVED" ? "badge-green" : doc?.status === "REJECTED" ? "badge-red" : "badge-yellow"}`}>
                                                    {doc?.status || "MISSING"}
                                                </span>
                                            </div>

                                            {doc ? (
                                                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                                                    <button
                                                        onClick={() => setSelectedImg(doc.file_path)}
                                                        style={{ height: 160, backgroundColor: "#000", borderRadius: 8, overflow: "hidden", cursor: "zoom-in", border: "1px solid var(--border)", padding: 0, display: "block", width: "100%" }}
                                                        aria-label={`Preview ${type} document`}
                                                    >
                                                        <img src={doc.file_path} style={{ width: "100%", height: "100%", objectFit: "cover" }} alt={`${type} document`} />
                                                    </button>
                                                    {doc.status === "PENDING" && (
                                                        <div style={{ display: "flex", gap: "10px" }}>
                                                            <button
                                                                className="btn-ghost"
                                                                style={{ flex: 1, fontSize: "12px", padding: "6px" }}
                                                                onClick={() => handleDocAction(doc.id, "approve")}
                                                            >
                                                                ✅ OK
                                                            </button>
                                                            <button
                                                                className="btn-ghost"
                                                                style={{ flex: 1, fontSize: "12px", padding: "6px", color: "var(--red)" }}
                                                                onClick={() => setRejectionModal({ isOpen: true, docId: doc.id })}
                                                            >
                                                                ❌ Reject
                                                            </button>
                                                        </div>
                                                    )}
                                                    {doc.status === "REJECTED" && (
                                                        <div style={{ fontSize: "11px", color: "var(--red)", fontStyle: "italic", borderTop: "1px solid rgba(239,68,68,0.2)", paddingTop: "8px" }}>
                                                            Reason: {doc.rejection_reason || "Invalid document"}
                                                        </div>
                                                    )}
                                                </div>
                                            ) : (
                                                <div style={{ height: 160, borderRadius: 8, border: "1px dashed var(--border)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-dim)" }}>
                                                    Not Uploaded Yet
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Rejection Modal */}
            {rejectionModal.isOpen && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <button
                        onClick={() => setRejectionModal({ isOpen: false, docId: null })}
                        style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.8)", backdropFilter: "blur(8px)", border: "none", cursor: "default", padding: 0, width: "100%", height: "100%" }}
                        aria-label="Close modal"
                    />
                    <div className="card animate-fade" style={{ position: "relative", width: 400, padding: 30, borderRadius: "12px", border: "1px solid var(--border)", background: "var(--bg-2)" }}>
                        <h3 style={{ marginBottom: 10 }}>Reject Document</h3>
                        <p style={{ color: "var(--text-dim)", fontSize: "14px", marginBottom: 20 }}>Please select a reason for rejecting this document:</p>

                        <select
                            className="input"
                            style={{ marginBottom: 15, width: "100%", padding: "10px", borderRadius: "8px", background: "var(--bg-3)", border: "1px solid var(--border)", color: "#fff" }}
                            value={rejectionReason}
                            onChange={(e) => setRejectionReason(e.target.value)}
                        >
                            <option value="">Select a reason...</option>
                            <option value="Image is blurry or unreadable">Blurry Image</option>
                            <option value="Document has expired">Expired Document</option>
                            <option value="Wrong document type">Incorrect Type</option>
                            <option value="Name doesn't match profile">Name Mismatch</option>
                            <option value="other">Other...</option>
                        </select>

                        {rejectionReason === "other" && (
                            <textarea
                                className="input"
                                placeholder="Type reason here..."
                                style={{ height: 80, marginBottom: 15, padding: 10, width: "100%", borderRadius: "8px", background: "var(--bg-3)", border: "1px solid var(--border)", color: "#fff", resize: "none" }}
                                onChange={(e) => setRejectionReason(e.target.value)}
                            />
                        )}

                        <div style={{ display: "flex", gap: 10 }}>
                            <button className="btn-primary" style={{ flex: 1, background: "var(--red)", borderRadius: "8px", padding: "10px" }} onClick={() => handleDocAction(rejectionModal.docId!, "reject", rejectionReason)}>Confirm Rejection</button>
                            <button className="btn-ghost" style={{ flex: 1, borderRadius: "8px", padding: "10px" }} onClick={() => setRejectionModal({ isOpen: false, docId: null })}>Cancel</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Image Preview Modal */}
            {selectedImg && (
                <button
                    onClick={() => setSelectedImg(null)}
                    style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.95)", zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center", padding: 40, cursor: "zoom-out", border: "none", width: "100%" }}
                    aria-label="Close image preview"
                >
                    <img src={selectedImg} style={{ maxWidth: "90%", maxHeight: "90%", borderRadius: 12, boxShadow: "0 0 50px rgba(0,0,0,0.5)", pointerEvents: "none" }} alt="Document preview" />
                    <span style={{ position: "absolute", top: 40, right: 40, color: "#fff", fontSize: "40px", fontWeight: "bold", lineHeight: 1 }}>×</span>
                </button>
            )}
        </div>
    );
}

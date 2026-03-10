import { useEffect, useState, type FormEvent } from "react";
import { api } from "../services/api";

interface PricingConfig {
    id: number;
    vehicle_type: string;
    base_fare: string | number;
    base_distance_km: string | number;
    per_km_rate: string | number;
    waiting_per_minute: string | number;
    surge_multiplier: string | number;
    minimum_fare: string | number;
    waiting_free_minutes: string | number;
    platform_commission_pct: string | number;
    is_active: boolean;
}

export default function FareConfig() {
    const [configs, setConfigs] = useState<PricingConfig[]>([]);
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    const fetchConfigs = async () => {
        try {
            const res = await api.get("/admin/fare-config/");
            setConfigs(res.data);
            if (res.data.length > 0 && !selectedId) {
                setSelectedId(res.data[0].id);
            }
        } catch (err) {
            console.error("Failed to fetch fare configs:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchConfigs();
    }, []);

    const selectedConfig = configs.find(c => c.id === selectedId);

    const handleUpdate = async (e: FormEvent) => {
        e.preventDefault();
        if (!selectedConfig) return;
        setSubmitting(true);
        try {
            await api.patch(`/admin/fare-config/${selectedId}/`, selectedConfig);
            alert("Pricing updated successfully!");
            fetchConfigs();
        } catch (err) {
            alert("Failed to update pricing.");
        } finally {
            setSubmitting(false);
        }
    };

    const updateField = (field: keyof PricingConfig, value: string | boolean) => {
        setConfigs(prev => prev.map(c =>
            c.id === selectedId ? { ...c, [field]: value } : c
        ));
    };

    if (loading) return <div style={{ padding: 60, color: "#fff" }}>Loading Configuration...</div>;

    return (
        <div style={{ padding: "36px 48px" }}>
            <header style={{ marginBottom: 32 }}>
                <h1 style={{ fontSize: 24, fontWeight: 800, color: "#fff", marginBottom: 8 }}>Fare Configuration</h1>
                <p style={{ color: "#94a3b8", fontSize: 14 }}>Manage platform pricing and surge multipliers per vehicle type</p>
            </header>

            <div style={{ display: "flex", gap: 12, marginBottom: 32 }}>
                {configs.map(c => (
                    <button
                        key={c.id}
                        onClick={() => setSelectedId(c.id)}
                        style={{
                            padding: "10px 20px", borderRadius: 12, textTransform: "uppercase", fontWeight: 700, fontSize: 13,
                            background: selectedId === c.id ? "#3b82f6" : "rgba(255,255,255,0.05)",
                            color: "#fff", border: "none", cursor: "pointer"
                        }}
                    >
                        {c.vehicle_type}
                    </button>
                ))}
            </div>

            {selectedConfig && (
                <div style={{ padding: 40, maxWidth: 1000, background: "rgba(15,23,42,0.6)", borderRadius: 16, border: "1px solid rgba(255,255,255,0.1)" }}>
                    <form onSubmit={handleUpdate}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 32, marginBottom: 40 }}>
                            <FormGroup
                                label="Base Fare (₹)"
                                value={selectedConfig.base_fare}
                                onChange={v => updateField("base_fare", v)}
                                desc="Minimum amount for any trip start"
                            />
                            <FormGroup
                                label="Base Distance (km)"
                                value={selectedConfig.base_distance_km}
                                onChange={v => updateField("base_distance_km", v)}
                                desc="Distance included in base fare"
                            />
                            <FormGroup
                                label="Per KM Rate (₹)"
                                value={selectedConfig.per_km_rate}
                                onChange={v => updateField("per_km_rate", v)}
                                desc="Charge for every km above base distance"
                            />
                            <FormGroup
                                label="Waiting Rate (₹/min)"
                                value={selectedConfig.waiting_per_minute}
                                onChange={v => updateField("waiting_per_minute", v)}
                                desc="Applied after free waiting time"
                            />
                            <FormGroup
                                label="Surge Multiplier"
                                value={selectedConfig.surge_multiplier}
                                onChange={v => updateField("surge_multiplier", v)}
                                desc="Current global demand multiplier"
                                color="#f59e0b"
                            />
                            <FormGroup
                                label="Minimum Fare (₹)"
                                value={selectedConfig.minimum_fare}
                                onChange={v => updateField("minimum_fare", v)}
                                desc="Absolute floor for any trip price"
                            />
                            <FormGroup
                                label="Waiting Free Minutes"
                                value={selectedConfig.waiting_free_minutes}
                                onChange={v => updateField("waiting_free_minutes", v)}
                                desc="First N minutes of waiting are free"
                            />
                            <FormGroup
                                label="Platform Commission Pct"
                                value={selectedConfig.platform_commission_pct}
                                onChange={v => updateField("platform_commission_pct", v)}
                                desc="Platform cut from each ride (%)"
                            />

                            {/* Checkbox for is_active */}
                            <div>
                                <div style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>
                                    Is Active
                                </div>
                                <label htmlFor="fare-is-active" style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", height: "48px" }}>
                                    <input
                                        id="fare-is-active"
                                        type="checkbox"
                                        checked={selectedConfig.is_active}
                                        onChange={e => updateField("is_active", e.target.checked)}
                                        style={{ width: 24, height: 24, cursor: "pointer", accentColor: "#3b82f6" }}
                                    />
                                    <span style={{ color: "#fff", fontSize: 16, fontWeight: 600 }}>Active</span>
                                </label>
                                <div style={{ fontSize: 10, color: "#64748b", marginTop: 6, fontWeight: 500 }}>Enable or disable this vehicle type</div>
                            </div>
                        </div>

                        <div style={{ padding: "20px", background: "rgba(59,130,246,0.05)", borderRadius: 12, border: "1px solid rgba(59,130,246,0.1)", marginBottom: 32 }}>
                            <div style={{ fontWeight: 700, fontSize: 13, color: "#3b82f6", marginBottom: 4 }}>Live Preview Calculation</div>
                            <div style={{ fontSize: 11, color: "#94a3b8" }}>
                                Estimated 5km journey: ₹{Math.round(Number(selectedConfig.base_fare) + (Math.max(0, 5 - Number(selectedConfig.base_distance_km)) * Number(selectedConfig.per_km_rate)))}
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            style={{
                                width: "100%", padding: 16, fontSize: 14, fontWeight: 700,
                                background: "#3b82f6", color: "#fff", border: "none", borderRadius: 12, cursor: "pointer"
                            }}
                        >
                            {submitting ? "Applying Changes..." : "Save Configuration"}
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
}

interface FormGroupProps {
    label: string;
    value: string | number;
    onChange: (val: string) => void;
    desc?: string;
    color?: string;
}

function FormGroup({ label, value, onChange, desc, color }: FormGroupProps) {
    return (
        <div>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: color || "#94a3b8", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>
                {label}
            </label>
            <input
                type="number"
                step="0.01"
                value={value}
                onChange={e => onChange(e.target.value)}
                style={{
                    width: "100%", background: "#1e293b", border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 10, padding: "12px 16px", color: "#fff", fontSize: 18, fontWeight: 800,
                    outline: "none"
                }}
            />
            {desc && <div style={{ fontSize: 10, color: "#64748b", marginTop: 6, fontWeight: 500 }}>{desc}</div>}
        </div>
    );
}

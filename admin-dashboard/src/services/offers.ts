import { api } from "./api";

// ─── Types ─────────────────────────────────────────────────────────
export interface OfferData {
    id?: number;
    code: string;
    title: string;
    description?: string;
    discount_type: "FLAT" | "PERCENTAGE";
    value: number;
    max_discount?: number | null;
    min_ride_value?: number;
    usage_limit?: number | null;
    per_user_limit?: number;
    total_usage_count?: number;
    valid_from: string;
    valid_to: string;
    is_active: boolean;
    city?: string;
    created_at?: string;
}

export interface OfferAnalytics {
    total_discounts_given: number;
    per_offer_breakdown: {
        offer__id: number;
        offer__code: string;
        offer__title: string;
        usage_count: number;
        total_discount: number;
    }[];
    daily_last_7_days: {
        date: string;
        total: number;
        count: number;
    }[];
}

// ─── API Calls ─────────────────────────────────────────────────────
export const getOffers = () => api.get<OfferData[]>("/offers/admin/");
export const createOffer = (data: Partial<OfferData>) => api.post("/offers/admin/", data);
export const updateOffer = (id: number, data: Partial<OfferData>) => api.patch(`/offers/admin/${id}/`, data);
export const deleteOffer = (id: number) => api.delete(`/offers/admin/${id}/`);
export const activateOffer = (id: number) => api.post(`/offers/admin/${id}/activate/`);
export const deactivateOffer = (id: number) => api.post(`/offers/admin/${id}/deactivate/`);
export const getOfferAnalytics = () => api.get<OfferAnalytics>("/offers/admin/analytics/");

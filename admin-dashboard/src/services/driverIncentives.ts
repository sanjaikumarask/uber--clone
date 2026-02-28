import { api } from "./api";

// ─── Types ─────────────────────────────────────────────────────────
export interface DriverIncentive {
    id?: number;
    type: "STREAK" | "PEAK" | "ZONE";
    title: string;
    description?: string;
    condition: Record<string, any>;
    reward_amount: number;
    max_per_day: number;
    valid_from: string;
    valid_to: string;
    is_active: boolean;
    city?: string;
    created_at?: string;
    current_progress?: number;
}

export interface IncentiveEarning {
    id: number;
    incentive: number;
    driver: number;
    ride: number;
    bonus_amount: number;
    created_at: string;
}

export interface IncentiveAnalytics {
    total_incentives_paid: number;
    per_incentive_breakdown: {
        incentive__id: number;
        incentive__title: string;
        incentive__type: string;
        total_paid: number;
        redemption_count: number;
    }[];
    daily_last_7_days: {
        date: string;
        total: number;
    }[];
}

// ─── API Calls ─────────────────────────────────────────────────────
export const getIncentives = () => api.get<DriverIncentive[]>("/driver-incentives/incentives/");
export const createIncentive = (data: Partial<DriverIncentive>) => api.post("/driver-incentives/incentives/", data);
export const updateIncentive = (id: number, data: Partial<DriverIncentive>) => api.patch(`/driver-incentives/incentives/${id}/`, data);
export const deleteIncentive = (id: number) => api.delete(`/driver-incentives/incentives/${id}/`);
export const activateIncentive = (id: number) => api.post(`/driver-incentives/incentives/${id}/activate/`);
export const deactivateIncentive = (id: number) => api.post(`/driver-incentives/incentives/${id}/deactivate/`);
export const getIncentiveEarnings = () => api.get<IncentiveEarning[]>("/driver-incentives/earnings/");
export const getIncentiveAnalytics = () => api.get<IncentiveAnalytics>("/driver-incentives/analytics/");

import { api } from "./api";

export interface DriverIncentive {
    id: number;
    type: "STREAK" | "PEAK" | "ZONE";
    title: string;
    description: string;
    condition: Record<string, any>;
    reward_amount: string; // From DecimalField
    max_per_day: number;
    valid_from: string;
    valid_to: string;
    city: string;
    is_active: boolean;
    current_progress?: number;
}

export interface DriverIncentiveEarning {
    id: number;
    incentive: number; // ID
    driver: number;
    ride: number;
    bonus_amount: number;
    created_at: string;
}

export const getActiveIncentives = async (): Promise<DriverIncentive[]> => {
    const response = await api.get("driver-incentives/incentives/");
    return response.data;
};

export const getIncentiveEarnings = async (): Promise<DriverIncentiveEarning[]> => {
    const response = await api.get("driver-incentives/earnings/");
    return response.data;
};

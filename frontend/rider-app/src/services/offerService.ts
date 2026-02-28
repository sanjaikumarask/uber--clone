import { api } from "./api";

export interface Offer {
    id: number;
    code: string;
    title: string;
    description: string;
    discount_type: "FLAT" | "PERCENTAGE";
    value: number;
    max_discount: number | null;
    min_ride_value: number;
    valid_from: string;
    valid_to: string;
    city: string;
}

export const getActiveOffers = async (city: string = "Chennai"): Promise<Offer[]> => {
    const response = await api.get(`offers/active/?city=${city}`);
    return response.data;
};

export const validateOffer = async (code: string, rideValue: number, city: string) => {
    const response = await api.post("offers/validate/", { code, ride_value: rideValue, city });
    return response.data;
};

export const applyOffer = async (code: string, rideId: number) => {
    const response = await api.post("offers/apply/", { code, ride_id: rideId });
    return response.data;
};


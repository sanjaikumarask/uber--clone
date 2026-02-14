export interface AdminDriver {
  driver_id: number;
  phone: string;
  status: "ONLINE" | "BUSY" | "OFFLINE";
  lat: number | null;
  lng: number | null;
  total_rides: number;
  avg_rating: number;
  rejections_today: number;
  is_suspended: boolean;
  updated_at: string;
}

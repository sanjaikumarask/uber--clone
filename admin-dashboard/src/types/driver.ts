export interface AdminDriver {
  driver_id: number;
  name: string;
  phone: string;
  // kept for backward compat with LiveMap
  first_name?: string;
  last_name?: string;
  status: "ONLINE" | "BUSY" | "OFFLINE" | "BLOCKED";
  level: "NORMAL" | "ACTIVE" | "CONSISTENT" | "PRO";
  lat?: number | null;
  lng?: number | null;
  // metrics
  offered_rides: number;
  accepted_rides: number;
  completed_rides: number;
  cancelled_rides: number;
  acceptance_rate: number;
  cancellation_rate: number;
  weekly_rides: number;
  peak_hour_rides: number;
  score: number;
  trust_score: number;
  avg_rating: number;
  fraud_flags: number;
  // suspension
  is_suspended: boolean;
  suspended_until?: string | null;
  updated_at: string;
}

export interface LevelHistoryEntry {
  old_level: string;
  new_level: string;
  changed_by: string;
  reason: string;
  timestamp: string;
}

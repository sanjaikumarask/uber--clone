export type RideStatus =
  | "SEARCHING"
  | "OFFERED"
  | "ASSIGNED"
  | "ARRIVED"
  | "ONGOING"
  | "COMPLETED"
  | "CANCELLED"
  | "NO_SHOW";

export interface DriverLocation {
  lat: number;
  lng: number;
}

export interface Ride {
  id: number;
  status: RideStatus;
  driver_location?: DriverLocation | null;
}

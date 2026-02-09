import { useNavigate } from "react-router-dom";
import { createRide } from "../services/ride.service";
import { useRideStore } from "../store/ride.store";
import type { RideStatus } from "../store/ride.store";


const ACTIVE_STATUSES: RideStatus[] = [
  "SEARCHING",
  "ASSIGNED",
  "ARRIVED",
  "ONGOING",
];

export default function BookRide(): JSX.Element {
  const navigate = useNavigate();
  const status = useRideStore((s) => s.status);
  const setRide = useRideStore((s) => s.setRide);

  const submit = async () => {
    if (ACTIVE_STATUSES.includes(status)) {
      navigate("/ride/searching", { replace: true });
      return;
    }

    const res = await createRide({
      pickup_lat: 12.9716,
      pickup_lng: 77.5946,
      drop_lat: 12.9352,
      drop_lng: 77.6245,
    });

    setRide(res.ride_id, res.status);
    navigate("/ride/searching", { replace: true });
  };

  return (
    <div>
      <h2>Book Ride</h2>
      <button onClick={submit}>Find Driver</button>
    </div>
  );
}

import { useRideStore } from "../domains/rides/ride.store";
import { useNavigate } from "react-router-dom";

export default function RideCompleted() {
  const reset = useRideStore((s) => s.reset);
  const navigate = useNavigate();

  const done = () => {
    reset();
    navigate("/home");
  };

  return (
    <div>
      <h1>Ride Completed</h1>
      <button onClick={done}>Back to Home</button>
    </div>
  );
}

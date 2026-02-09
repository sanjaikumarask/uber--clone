import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth.store";

export default function Home(): JSX.Element {
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div>
      <h2>Rider Home</h2>
      <button onClick={() => navigate("/book")}>Book Ride</button>
      <button onClick={onLogout}>Logout</button>
    </div>
  );
}

import { Outlet } from "react-router-dom";

export default function DriverLayout() {
  return (
    <div>
      <header>
        <h2>Driver Panel</h2>
      </header>

      <main>
        <Outlet />
      </main>
    </div>
  );
}

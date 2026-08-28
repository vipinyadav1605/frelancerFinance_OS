import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { GlobalSearch } from "./GlobalSearch";
import { NotificationBell } from "./NotificationBell";

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <nav className="navbar">
      <div className="navbar-brand">Freelancer Finance OS</div>
      <div className="navbar-links">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/invoices">Invoices</Link>
        <Link to="/recurring-invoices">Recurring</Link>
        <Link to="/expenses">Expenses</Link>
        <Link to="/clients">Clients</Link>
        <Link to="/settings">Settings</Link>
      </div>
      <div className="navbar-user">
        <GlobalSearch />
        <NotificationBell />
        <span>{user.email}</span>
        <button className="btn btn-link" onClick={handleLogout}>Log out</button>
      </div>
    </nav>
  );
}

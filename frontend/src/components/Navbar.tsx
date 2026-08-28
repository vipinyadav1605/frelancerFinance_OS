import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { GlobalSearch } from "./GlobalSearch";
import { NotificationBell } from "./NotificationBell";

const LINKS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/invoices", label: "Invoices" },
  { to: "/recurring-invoices", label: "Recurring" },
  { to: "/expenses", label: "Expenses" },
  { to: "/clients", label: "Clients" },
  { to: "/settings", label: "Settings" },
];

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  if (!user) return null;

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <nav className="navbar">
      <div className="navbar-brand">Freelancer Finance OS</div>
      <button
        className="navbar-toggle"
        onClick={() => setMenuOpen((v) => !v)}
        aria-label={menuOpen ? "Close menu" : "Open menu"}
        aria-expanded={menuOpen}
      >
        {menuOpen ? "✕" : "☰"}
      </button>
      <div className={`navbar-links ${menuOpen ? "navbar-links-open" : ""}`}>
        {LINKS.map((link) => <Link key={link.to} to={link.to}>{link.label}</Link>)}
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

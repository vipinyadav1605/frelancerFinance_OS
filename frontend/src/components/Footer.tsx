import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="app-footer">
      <span>&copy; {new Date().getFullYear()} Freelancer Finance OS</span>
      <span className="app-footer-sep">&bull;</span>
      <span>GST invoicing &amp; bookkeeping for Indian freelancers</span>
      <span className="app-footer-sep">&bull;</span>
      <Link to="/terms">Terms of Service</Link>
      <span className="app-footer-sep">&bull;</span>
      <Link to="/privacy">Privacy Policy</Link>
    </footer>
  );
}

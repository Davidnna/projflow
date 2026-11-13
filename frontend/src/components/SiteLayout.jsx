import { NavLink, Link } from "react-router-dom";
import BrandLogo from "./BrandLogo.jsx";

export default function SiteLayout({ children }) {
  return (
    <div className="site-shell">
      <header className="site-header">
        <div className="header-inner">
          <BrandLogo />
          <nav className="main-nav" aria-label="Main navigation">
            <NavLink to="/" end>Overview</NavLink>
            <NavLink to="/platform">Platform</NavLink>
            <NavLink to="/status">System status</NavLink>
          </nav>
          <Link className="header-action" to="/status">System status <span aria-hidden="true">↗</span></Link>
        </div>
      </header>
      <main>{children}</main>
      <footer className="site-footer">
        <div className="footer-inner">
          <BrandLogo compact />
          <p>From Proposal to Final Defence.</p>
          <span>© {new Date().getFullYear()} ProjFlow</span>
        </div>
      </footer>
    </div>
  );
}

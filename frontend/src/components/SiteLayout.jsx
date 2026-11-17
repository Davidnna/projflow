import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import BrandLogo from "./BrandLogo.jsx";

export default function SiteLayout() {
    const { isAuthenticated } = useAuth();
    return (
        <div className="site-shell">
            <header className="site-header">
                <div className="header-inner">
                    <BrandLogo />
                    <nav className="main-nav" aria-label="Main navigation">
                        <NavLink to="/" end>Overview</NavLink>
                        <NavLink to="/platform">About ProjFlow</NavLink>
                    </nav>
                    {isAuthenticated
                        ? <Link className="header-action" to="/app/overview">Open workspace <span aria-hidden="true">↗</span></Link>
                        : <div className="public-header-actions"><Link className="public-login-link" to="/login">Sign in</Link><Link className="header-action" to="/register">Student registration <span aria-hidden="true">↗</span></Link></div>}
                </div>
            </header>
            <main><Outlet /></main>
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

import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import BrandLogo from "./BrandLogo.jsx";

const publicLinks = [
    { to: "/", label: "Home", end: true },
    { to: "/about", label: "About" },
    { to: "/features", label: "Features" },
    { to: "/how-it-works", label: "How it works" },
];

export default function SiteLayout() {
    const { isAuthenticated } = useAuth();
    const [menuOpen, setMenuOpen] = useState(false);

    const closeMenu = () => setMenuOpen(false);

    return (
        <div className="site-shell">
            <header className="public-header">
                <div className="public-header-inner">
                    <BrandLogo />
                    <nav className="public-nav" aria-label="Main navigation">
                        {publicLinks.map((item) => (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                end={item.end}
                                onClick={closeMenu}
                            >
                                {item.label}
                            </NavLink>
                        ))}
                    </nav>
                    <div className="public-header-actions">
                        {isAuthenticated ? (
                            <Link className="public-primary-link" to="/app/overview">
                                Open workspace <span aria-hidden="true">↗</span>
                            </Link>
                        ) : (
                            <>
                                <Link className="public-signin-link" to="/login">Sign in</Link>
                                <Link className="public-primary-link" to="/register">
                                    Student registration <span aria-hidden="true">↗</span>
                                </Link>
                            </>
                        )}
                        <button
                            className="public-menu-toggle"
                            type="button"
                            aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
                            aria-expanded={menuOpen}
                            onClick={() => setMenuOpen((open) => !open)}
                        >
                            <span />
                            <span />
                            <span />
                        </button>
                    </div>
                </div>
                <nav
                    className={`public-mobile-nav${menuOpen ? " public-mobile-nav--open" : ""}`}
                    aria-label="Mobile navigation"
                    hidden={!menuOpen}
                >
                    {publicLinks.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            end={item.end}
                            onClick={closeMenu}
                        >
                            {item.label}
                        </NavLink>
                    ))}
                    {isAuthenticated ? (
                        <Link to="/app/overview" onClick={closeMenu}>Open workspace</Link>
                    ) : (
                        <>
                            <Link to="/login" onClick={closeMenu}>Sign in</Link>
                            <Link to="/register" onClick={closeMenu}>Student registration</Link>
                        </>
                    )}
                </nav>
            </header>
            <main className="public-main"><Outlet /></main>
            <footer className="public-footer">
                <div className="public-footer-main">
                    <div className="public-footer-brand">
                        <BrandLogo compact />
                        <p>Clearer coordination for the final-year project process.</p>
                    </div>
                    <div className="public-footer-column">
                        <h2>Explore</h2>
                        <Link to="/about">About ProjFlow</Link>
                        <Link to="/features">Platform features</Link>
                        <Link to="/how-it-works">How it works</Link>
                    </div>
                    <div className="public-footer-column">
                        <h2>Access</h2>
                        <Link to="/login">Sign in</Link>
                        <Link to="/register">Student registration</Link>
                    </div>
                    <div className="public-footer-column public-footer-help">
                        <h2>Need help?</h2>
                        <p>For questions about eligibility or access, contact your department's Project Coordinator.</p>
                    </div>
                </div>
                <div className="public-footer-bottom">
                    <span>© {new Date().getFullYear()} ProjFlow. All rights reserved.</span>
                    <span>From Proposal to Final Defence.</span>
                </div>
            </footer>
        </div>
    );
}

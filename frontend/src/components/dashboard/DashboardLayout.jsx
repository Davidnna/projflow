import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../../auth/AuthContext.jsx";
import BrandLogo from "../BrandLogo.jsx";

const lecturerLinks = [
    { to: "/app/overview", label: "Overview", icon: "◫", end: true },
    { to: "/app/topics/review", label: "Topic reviews", icon: "✎" },
    { to: "/app/progress", label: "Report reviews", icon: "▤" },
];

const studentLinks = [
    { to: "/app/overview", label: "Overview", icon: "◫", end: true },
    { to: "/app/topics", label: "My project topic", icon: "✎" },
    { to: "/app/my-progress", label: "My project report", icon: "▤" },
];

const coordinatorLinks = [
    { to: "/app/overview", label: "Overview", icon: "◫", end: true },
    { to: "/app/sessions", label: "Academic sessions", icon: "▦" },
    { to: "/app/students", label: "Student records", icon: "♙" },
    { to: "/app/registrations", label: "Registrations", icon: "✓" },
    { to: "/app/lecturers", label: "Lecturers", icon: "♧" },
    { to: "/app/supervisors", label: "Supervisor allocation", icon: "⇄" },
    { to: "/app/report-structure", label: "Report structure", icon: "▤" },
    { to: "/app/coordinator-access", label: "Coordinator access", icon: "♙" },
];

export default function DashboardLayout() {
    const { user, logout, hasAnyRole } = useAuth();
    const [menuOpen, setMenuOpen] = useState(false);
    const navigate = useNavigate();
    const isCoordinator = hasAnyRole(["administrator", "project_coordinator"]);
    const isProjectCoordinator = hasAnyRole(["project_coordinator"]);
    const isAdministrator = hasAnyRole(["administrator"]);
    const isLecturer = hasAnyRole(["lecturer"]);
    const visibleCoordinatorLinks = coordinatorLinks.filter((link) => {
        if (link.to === "/app/report-structure") {
            return isProjectCoordinator;
        }
        if (link.to === "/app/coordinator-access") {
            return isAdministrator;
        }
        return true;
    });
    const links = [
        ...(isCoordinator ? visibleCoordinatorLinks : [{ to: "/app/overview", label: "Overview", icon: "◫", end: true }]),
        ...(isLecturer && isCoordinator ? lecturerLinks.slice(1) : isLecturer ? lecturerLinks.slice(1) : []),
        ...(hasAnyRole(["student"]) ? studentLinks.slice(1) : []),
        ...(hasAnyRole(["project_coordinator", "lecturer", "student"]) ? [{ to: "/app/completion", label: "Final project & defence", icon: "▣" }] : []),
        { to: "/app/notifications", label: "Notifications", icon: "◉" },
    ];

    async function handleLogout() {
        await logout();
        navigate("/", { replace: true });
    }

    const roleLabel = isCoordinator
        ? (user?.roles?.includes("administrator") ? "Administrator" : "Project Coordinator")
        : isLecturer ? "Lecturer" : "Student";

    return (
        <div className="workspace-shell">
            <aside className={`workspace-sidebar${menuOpen ? " workspace-sidebar--open" : ""}`}>
                <div className="sidebar-brand"><BrandLogo compact /></div>
                <div className="sidebar-section-label">WORKSPACE</div>
                <nav className="sidebar-nav" aria-label="Workspace navigation">
                    {links.map((link) => (
                        <NavLink key={link.to} to={link.to} end={link.end} onClick={() => setMenuOpen(false)}>
                            <span className="sidebar-nav-icon" aria-hidden="true">{link.icon}</span>
                            {link.label}
                        </NavLink>
                    ))}
                    {!isCoordinator && isLecturer && (
                        <div className="sidebar-note">Your assigned students and supervision activities will appear here.</div>
                    )}
                    {!isCoordinator && !isLecturer && (
                        <div className="sidebar-note">Your registration details and project information will appear here.</div>
                    )}
                </nav>
                <div className="sidebar-bottom">
                    <div className="sidebar-help-card">
                        <span className="sidebar-help-icon">?</span>
                        <strong>Need assistance?</strong>
                        <span>Contact your department's project administration team.</span>
                    </div>
                    <button className="sidebar-logout" onClick={handleLogout}><span>↪</span> Sign out</button>
                </div>
            </aside>

            <div className="workspace-main">
                <header className="workspace-topbar">
                    <button className="mobile-menu-button" onClick={() => setMenuOpen((open) => !open)} aria-label="Toggle navigation">☰</button>
                    <div className="topbar-context"><span className="topbar-context-dot" /> Department workspace <span className="topbar-separator">/</span> {roleLabel}</div>
                    <div className="topbar-user">
                        <div className="topbar-user-copy"><strong>{user?.full_name || `${user?.first_name || ""} ${user?.last_name || ""}`.trim()}</strong><span>{roleLabel}</span></div>
                        <div className="avatar-circle">{(user?.first_name || user?.email || "P").slice(0, 1).toUpperCase()}</div>
                    </div>
                </header>
                <main className="workspace-content"><Outlet /></main>
                <footer className="workspace-footer"><span>ProjFlow · From Proposal to Final Defence</span><span>Your department's project workspace</span></footer>
            </div>
            {menuOpen && <button className="sidebar-backdrop" onClick={() => setMenuOpen(false)} aria-label="Close navigation" />}
        </div>
    );
}

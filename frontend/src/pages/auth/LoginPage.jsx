import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext.jsx";
import BrandLogo from "../../components/BrandLogo.jsx";

export default function LoginPage() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [submitting, setSubmitting] = useState(false);

    async function handleSubmit(event) {
        event.preventDefault();
        setSubmitting(true);
        setError("");
        try {
            await login(email.trim(), password);
            navigate(location.state?.from?.pathname || "/app/overview", { replace: true });
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <main className="auth-page">
            <section className="auth-panel auth-panel--form">
                <div className="auth-brand"><BrandLogo /></div>
                <div className="auth-form-wrap">
                    <div className="auth-eyebrow">DEPARTMENTAL WORKSPACE</div>
                    <h1>Welcome back.</h1>
                    <p className="auth-intro">Sign in to continue to your ProjFlow workspace.</p>
                    {error && <div className="auth-error" role="alert">{error}</div>}
                    <form className="auth-form" onSubmit={handleSubmit}>
                        <label><span>Email address</span><input type="email" required autoComplete="email" placeholder="name@department.edu" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
                        <label><span>Password</span><input type="password" required autoComplete="current-password" placeholder="Enter your password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
                        <button className="button button-primary auth-submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in to ProjFlow"}<span>→</span></button>
                    </form>
                    <div className="auth-switch">New student? <Link to="/register">Create an account</Link></div>
                    <Link className="auth-back-link" to="/">← Back to public website</Link>
                </div>
                <div className="auth-legal">© {new Date().getFullYear()} ProjFlow · From Proposal to Final Defence</div>
            </section>
            <aside className="auth-panel auth-panel--visual">
                <div className="auth-visual-orbit auth-orbit-one" /><div className="auth-visual-orbit auth-orbit-two" />
                <div className="auth-visual-content">
                    <div className="auth-visual-mark">PF</div>
                    <div className="auth-visual-kicker">ONE DEPARTMENT. ONE WORKSPACE.</div>
                    <h2>Bring every project stage into focus.</h2>
                    <p>Coordinate academic sessions, student records and supervision responsibilities through one organised system.</p>
                    <div className="auth-visual-points"><span><b>01</b> Clear academic workflows</span><span><b>02</b> Accountable decisions</span><span><b>03</b> Connected project records</span></div>
                </div>
                <div className="auth-visual-footer">PROJFLOW · 0.3.3</div>
            </aside>
        </main>
    );
}

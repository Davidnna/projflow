import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import BrandLogo from "../../components/BrandLogo.jsx";
import { apiRequest, endpoints } from "../../api.js";

const initialForm = {
    setup_token: "",
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    confirm_password: "",
};

export default function InitialAdministratorSetupPage() {
    const [availability, setAvailability] = useState("checking");
    const [form, setForm] = useState(initialForm);
    const [error, setError] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [createdEmail, setCreatedEmail] = useState("");

    useEffect(() => {
        let active = true;
        apiRequest(endpoints.initialAdministratorSetup, { auth: false })
            .then((response) => {
                if (active) {
                    setAvailability(response.setup_available ? "available" : "unavailable");
                }
            })
            .catch(() => {
                if (active) {
                    setAvailability("error");
                }
            });
        return () => {
            active = false;
        };
    }, []);

    function update(field, value) {
        setForm((current) => ({ ...current, [field]: value }));
    }

    async function handleSubmit(event) {
        event.preventDefault();
        setError("");

        if (form.password !== form.confirm_password) {
            setError("The passwords do not match.");
            return;
        }
        if (form.password.length < 12) {
            setError("Use a password containing at least 12 characters.");
            return;
        }

        setSubmitting(true);
        try {
            const response = await apiRequest(endpoints.initialAdministratorSetup, {
                method: "POST",
                auth: false,
                body: {
                    setup_token: form.setup_token,
                    first_name: form.first_name.trim(),
                    last_name: form.last_name.trim(),
                    email: form.email.trim(),
                    password: form.password,
                },
            });
            setCreatedEmail(response.email || form.email.trim());
            setForm(initialForm);
            setAvailability("completed");
        } catch (requestError) {
            setError(requestError.message);
            if (requestError.statusCode === 410) {
                setAvailability("unavailable");
            }
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <main className="auth-page auth-page--register">
            <section className="auth-panel auth-panel--form">
                <div className="auth-brand"><BrandLogo /></div>
                <div className="auth-form-wrap auth-form-wrap--wide">
                    <div className="auth-eyebrow">INITIAL SYSTEM CONFIGURATION</div>
                    {availability === "completed" ? (
                        <div className="setup-complete" role="status">
                            <div className="auth-success-icon">✓</div>
                            <h1>Administrator created.</h1>
                            <p className="auth-intro">The first ProjFlow Administrator account has been created successfully for <strong>{createdEmail}</strong>.</p>
                            <p className="setup-note">The initial setup route is now closed because an Administrator exists. Remove the temporary setup secret from Render Environment before continuing.</p>
                            <Link className="button button-primary auth-submit" to="/login">Continue to sign in <span>→</span></Link>
                        </div>
                    ) : (
                        <>
                            <h1>Create the first Administrator.</h1>
                            <p className="auth-intro">This one-time setup creates the initial system Administrator directly in the live ProjFlow database. It is available only before an Administrator account exists.</p>
                            {error && <div className="auth-error" role="alert">{error}</div>}
                            {availability === "checking" && <div className="setup-notice" role="status">Checking whether initial setup is available…</div>}
                            {availability === "error" && <div className="setup-notice setup-notice--error" role="alert">ProjFlow could not reach the API. Check the live service and try again.</div>}
                            {availability === "unavailable" && <div className="setup-notice" role="status">Initial setup is currently unavailable. The temporary setup secret may not be configured, or an Administrator account has already been created.</div>}
                            {availability === "available" && (
                                <form className="auth-form" onSubmit={handleSubmit}>
                                    <label>
                                        <span>One-time setup secret</span>
                                        <input type="password" required autoComplete="off" spellCheck="false" value={form.setup_token} onChange={(event) => update("setup_token", event.target.value)} />
                                        <small className="auth-field-hint">Enter the temporary secret configured in Render. It is not your account password.</small>
                                    </label>
                                    <div className="auth-field-grid">
                                        <label><span>First name</span><input required maxLength="150" autoComplete="given-name" value={form.first_name} onChange={(event) => update("first_name", event.target.value)} /></label>
                                        <label><span>Last name</span><input required maxLength="150" autoComplete="family-name" value={form.last_name} onChange={(event) => update("last_name", event.target.value)} /></label>
                                    </div>
                                    <label><span>Administrator email address</span><input type="email" required maxLength="254" autoComplete="email" value={form.email} onChange={(event) => update("email", event.target.value)} /></label>
                                    <label><span>Password</span><input type="password" required minLength="12" maxLength="128" autoComplete="new-password" value={form.password} onChange={(event) => update("password", event.target.value)} /><small className="auth-field-hint">Use at least 12 characters. Django will also check password strength.</small></label>
                                    <label><span>Confirm password</span><input type="password" required minLength="12" maxLength="128" autoComplete="new-password" value={form.confirm_password} onChange={(event) => update("confirm_password", event.target.value)} /></label>
                                    <button className="button button-primary auth-submit" disabled={submitting}>{submitting ? "Creating Administrator…" : "Create Administrator account"}<span>→</span></button>
                                </form>
                            )}
                        </>
                    )}
                    <div className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></div>
                    <Link className="auth-back-link" to="/">← Back to public website</Link>
                </div>
                <div className="auth-legal">© {new Date().getFullYear()} ProjFlow · From Proposal to Final Defence</div>
            </section>
            <aside className="auth-panel auth-panel--visual">
                <div className="auth-visual-orbit auth-orbit-one" />
                <div className="auth-visual-orbit auth-orbit-two" />
                <div className="auth-visual-content">
                    <div className="auth-visual-mark">PF</div>
                    <div className="auth-visual-kicker">SECURE INITIAL SETUP</div>
                    <h2>Establish the first system administrator.</h2>
                    <p>The one-time setup secret protects account creation. After the first Administrator is created, this setup process closes automatically.</p>
                    <div className="auth-visual-points"><span><b>01</b> Live production database</span><span><b>02</b> One-time setup access</span><span><b>03</b> Automatic Administrator role</span></div>
                </div>
                <div className="auth-visual-footer">PROJFLOW · 0.3.1</div>
            </aside>
        </main>
    );
}

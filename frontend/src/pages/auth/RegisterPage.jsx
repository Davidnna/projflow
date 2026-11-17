import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext.jsx";
import BrandLogo from "../../components/BrandLogo.jsx";
import { StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const initialForm = { first_name: "", last_name: "", other_names: "", matric_number: "", email: "", phone: "", password: "" };

export default function RegisterPage() {
    const { register } = useAuth();
    const [form, setForm] = useState(initialForm);
    const [error, setError] = useState("");
    const [result, setResult] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    function update(field, value) {
        setForm((current) => ({ ...current, [field]: value }));
    }

    async function handleSubmit(event) {
        event.preventDefault();
        setSubmitting(true);
        setError("");
        try {
            const response = await register(form);
            setResult(response);
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSubmitting(false);
        }
    }

    if (result) {
        const enrollment = result.enrollment;
        const verified = ["auto_verified", "manually_approved"].includes(enrollment.verification_status);
        return (
            <main className="auth-page auth-page--register">
                <section className="auth-panel auth-panel--form">
                    <div className="auth-brand"><BrandLogo /></div>
                    <div className="auth-form-wrap auth-success-wrap">
                        <div className="auth-success-icon">✓</div>
                        <div className="auth-eyebrow">REGISTRATION</div>
                        <h1>{verified ? "Registration complete." : "Registration received."}</h1>
                        <p className="auth-intro">{verified ? "Your registration is complete. You can now sign in to your ProjFlow workspace." : "Your registration has been received and is awaiting review. You can sign in later to check its status."}</p>
                        <div className="registration-result-card"><div><small>Matriculation number</small><strong>{enrollment.matric_number}</strong></div><div><small>Academic session</small><strong>{enrollment.session_name}</strong></div><div><small>Registration status</small><StatusBadge value={enrollment.verification_status}>{verified ? "Verified" : "Awaiting review"}</StatusBadge></div></div>
                        <p className="registration-result-note">Use your email address and password to sign in.</p>
                        <Link className="button button-primary auth-submit" to="/login">Continue to sign in <span>→</span></Link>
                    </div>
                    <div className="auth-legal">© {new Date().getFullYear()} ProjFlow · From Proposal to Final Defence</div>
                </section>
                <aside className="auth-panel auth-panel--visual"><div className="auth-visual-orbit auth-orbit-one" /><div className="auth-visual-orbit auth-orbit-two" /><div className="auth-visual-content"><div className="auth-visual-mark">PF</div><div className="auth-visual-kicker">STUDENT REGISTRATION</div><h2>Welcome to your project workspace.</h2><p>Complete your registration to get started. Your department will guide you through the next steps.</p></div><div className="auth-visual-footer">PROJFLOW</div></aside>
            </main>
        );
    }

    return (
        <main className="auth-page auth-page--register">
            <section className="auth-panel auth-panel--form">
                <div className="auth-brand"><BrandLogo /></div>
                <div className="auth-form-wrap auth-form-wrap--wide">
                    <div className="auth-eyebrow">STUDENT REGISTRATION</div>
                    <h1>Create your account.</h1>
                    <p className="auth-intro">Enter your personal and academic details carefully, using the information held by your department.</p>
                    {error && <div className="auth-error" role="alert">{error}</div>}
                    <form className="auth-form" onSubmit={handleSubmit}>
                        <div className="auth-field-grid"><label><span>First name</span><input required maxLength="150" value={form.first_name} onChange={(event) => update("first_name", event.target.value)} /></label><label><span>Last name</span><input required maxLength="150" value={form.last_name} onChange={(event) => update("last_name", event.target.value)} /></label></div>
                        <label><span>Other names <small>(if recorded by the department)</small></span><input maxLength="150" value={form.other_names} onChange={(event) => update("other_names", event.target.value)} /><small className="auth-field-hint">Enter all other names as they appear in your academic records.</small></label>
                        <label><span>Matriculation number</span><input required maxLength="40" autoCapitalize="characters" value={form.matric_number} onChange={(event) => update("matric_number", event.target.value)} /></label>
                        <label><span>Email address</span><input type="email" required autoComplete="email" value={form.email} onChange={(event) => update("email", event.target.value)} /></label>
                        <label><span>Phone number <small>(if recorded by the department)</small></span><input type="tel" maxLength="30" autoComplete="tel" value={form.phone} onChange={(event) => update("phone", event.target.value)} /><small className="auth-field-hint">Provide the phone number associated with your student record, if applicable.</small></label>
                        <label><span>Password</span><input type="password" required minLength="12" autoComplete="new-password" value={form.password} onChange={(event) => update("password", event.target.value)} /><small className="auth-field-hint">Use at least 12 characters.</small></label>
                        <button className="button button-primary auth-submit" disabled={submitting}>{submitting ? "Submitting registration…" : "Create student account"}<span>→</span></button>
                    </form>
                    <div className="auth-switch">Already registered? <Link to="/login">Sign in</Link></div>
                    <Link className="auth-back-link" to="/">← Back to public website</Link>
                </div>
                <div className="auth-legal">© {new Date().getFullYear()} ProjFlow · From Proposal to Final Defence</div>
            </section>
            <aside className="auth-panel auth-panel--visual"><div className="auth-visual-orbit auth-orbit-one" /><div className="auth-visual-orbit auth-orbit-two" /><div className="auth-visual-content"><div className="auth-visual-mark">PF</div><div className="auth-visual-kicker">STUDENT ONBOARDING</div><h2>Start with the right academic record.</h2><p>Provide accurate details so your department can confirm your student registration.</p><div className="auth-visual-points"><span><b>01</b> Enter your details</span><span><b>02</b> Submit your registration</span><span><b>03</b> Access your workspace</span></div></div><div className="auth-visual-footer">PROJFLOW</div></aside>
        </main>
    );
}

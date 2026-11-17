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
        return (
            <main className="auth-page auth-page--register">
                <section className="auth-panel auth-panel--form">
                    <div className="auth-brand"><BrandLogo /></div>
                    <div className="auth-form-wrap auth-success-wrap">
                        <div className="auth-success-icon">✓</div>
                        <div className="auth-eyebrow">REGISTRATION SUBMITTED</div>
                        <h1>You're in the system.</h1>
                        <p className="auth-intro">{enrollment.verification_status === "auto_verified" ? "Your details matched the departmental register. Your account has been automatically verified." : "Your account has been created, but some details could not be matched automatically. The registration has been referred for manual review."}</p>
                        <div className="registration-result-card"><div><small>Matriculation number</small><strong>{enrollment.matric_number}</strong></div><div><small>Academic session</small><strong>{enrollment.session_name}</strong></div><div><small>Verification status</small><StatusBadge value={enrollment.verification_status} /></div></div>
                        {enrollment.verification_notes && <div className="registration-result-note">{enrollment.verification_notes}</div>}
                        <p className="registration-result-note">You can sign in to check your registration status. Project activities become available after verification and supervisor allocation.</p>
                        <Link className="button button-primary auth-submit" to="/login">Continue to sign in <span>→</span></Link>
                    </div>
                    <div className="auth-legal">© {new Date().getFullYear()} ProjFlow · From Proposal to Final Defence</div>
                </section>
                <aside className="auth-panel auth-panel--visual"><div className="auth-visual-orbit auth-orbit-one" /><div className="auth-visual-orbit auth-orbit-two" /><div className="auth-visual-content"><div className="auth-visual-mark">PF</div><div className="auth-visual-kicker">STUDENT ONBOARDING</div><h2>A structured start to your final-year project.</h2><p>Once your registration is verified, the Project Coordinator will allocate your supervisor before topic proposal submission.</p></div><div className="auth-visual-footer">PROJFLOW · 0.3.3</div></aside>
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
                    <p className="auth-intro">Enter your details exactly as they appear in the departmental register. ProjFlow checks your matriculation number, names and any email or phone number recorded for you.</p>
                    {error && <div className="auth-error" role="alert">{error}</div>}
                    <form className="auth-form" onSubmit={handleSubmit}>
                        <div className="auth-field-grid"><label><span>First name</span><input required maxLength="150" value={form.first_name} onChange={(event) => update("first_name", event.target.value)} /></label><label><span>Last name</span><input required maxLength="150" value={form.last_name} onChange={(event) => update("last_name", event.target.value)} /></label></div>
                        <label><span>Other names <small>(if recorded by the department)</small></span><input maxLength="150" value={form.other_names} onChange={(event) => update("other_names", event.target.value)} /><small className="auth-field-hint">Enter all other names exactly as shown in your departmental record.</small></label>
                        <label><span>Matriculation number</span><input required maxLength="40" autoCapitalize="characters" value={form.matric_number} onChange={(event) => update("matric_number", event.target.value)} /></label>
                        <label><span>Email address</span><input type="email" required autoComplete="email" value={form.email} onChange={(event) => update("email", event.target.value)} /></label>
                        <label><span>Phone number <small>(if recorded by the department)</small></span><input type="tel" maxLength="30" autoComplete="tel" value={form.phone} onChange={(event) => update("phone", event.target.value)} /><small className="auth-field-hint">Use the same phone number format as your departmental record.</small></label>
                        <label><span>Password</span><input type="password" required minLength="12" autoComplete="new-password" value={form.password} onChange={(event) => update("password", event.target.value)} /><small className="auth-field-hint">Use at least 12 characters.</small></label>
                        <button className="button button-primary auth-submit" disabled={submitting}>{submitting ? "Submitting registration…" : "Create student account"}<span>→</span></button>
                    </form>
                    <div className="auth-switch">Already registered? <Link to="/login">Sign in</Link></div>
                    <Link className="auth-back-link" to="/">← Back to public website</Link>
                </div>
                <div className="auth-legal">© {new Date().getFullYear()} ProjFlow · From Proposal to Final Defence</div>
            </section>
            <aside className="auth-panel auth-panel--visual"><div className="auth-visual-orbit auth-orbit-one" /><div className="auth-visual-orbit auth-orbit-two" /><div className="auth-visual-content"><div className="auth-visual-mark">PF</div><div className="auth-visual-kicker">STUDENT ONBOARDING</div><h2>Start with the right academic record.</h2><p>ProjFlow checks registration details against the departmental roster. Unmatched or inconsistent records are referred for manual review.</p><div className="auth-visual-points"><span><b>01</b> Register your details</span><span><b>02</b> Verify your eligibility</span><span><b>03</b> Receive supervisor allocation</span></div></div><div className="auth-visual-footer">PROJFLOW · 0.3.3</div></aside>
        </main>
    );
}

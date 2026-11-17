export function PageHeader({ eyebrow, title, description, actions }) {
    return (
        <div className="workspace-page-heading">
            <div>
                {eyebrow && <div className="workspace-eyebrow">{eyebrow}</div>}
                <h1>{title}</h1>
                {description && <p>{description}</p>}
            </div>
            {actions && <div className="workspace-page-actions">{actions}</div>}
        </div>
    );
}

export function StatCard({ label, value, detail, icon, tone = "blue" }) {
    return (
        <article className="metric-card">
            <div className={`metric-icon metric-icon--${tone}`}>{icon}</div>
            <div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
        </article>
    );
}

export function StatusBadge({ value, children }) {
    const labels = {
        active: "Active",
        auto_verified: "Verified",
        manually_approved: "Verified",
        pending_review: "Awaiting review",
        rejected: "Rejected",
        planned: "Not active",
        closed: "Closed",
        previewed: "Ready to import",
        committed: "Imported",
        valid: "Valid",
        invalid: "Needs attention",
        duplicate: "Duplicate",
        inactive: "Inactive",
        approved: "Approved",
        pending: "Pending",
    };
    const fallback = String(value || "Unknown").replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
    const label = children || labels[value] || fallback;
    const tone = ["active", "auto_verified", "manually_approved", "committed", "approved", "valid"].includes(value)
        ? "success"
        : ["pending_review", "planned", "previewed", "pending", "invalid", "duplicate"].includes(value)
            ? "warning"
            : ["closed", "rejected", "inactive"].includes(value) ? "muted" : "info";
    return <span className={`state-badge state-badge--${tone}`}>{label}</span>;
}

export function LoadingState({ label = "Loading records…" }) {
    return <div className="workspace-loading"><span className="loading-spinner" />{label}</div>;
}

export function EmptyState({ title, description, action }) {
    return (
        <div className="empty-state">
            <div className="empty-state-symbol">⌁</div>
            <strong>{title}</strong>
            <p>{description}</p>
            {action}
        </div>
    );
}

export function Alert({ type = "info", children, onClose }) {
    return (
        <div className={`inline-alert inline-alert--${type}`} role="status">
            <span>{type === "success" ? "✓" : type === "error" ? "!" : "i"}</span>
            <div>{children}</div>
            {onClose && <button onClick={onClose} aria-label="Dismiss message">×</button>}
        </div>
    );
}

export function Modal({ title, description, onClose, children, size = "normal" }) {
    return (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
                onClose();
            }
        }}>
            <section className={`modal-card${size === "wide" ? " modal-card--wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
                <div className="modal-heading">
                    <div><h2>{title}</h2>{description && <p>{description}</p>}</div>
                    <button className="modal-close" onClick={onClose} aria-label="Close dialog">×</button>
                </div>
                {children}
            </section>
        </div>
    );
}

export function Field({ label, hint, error, children, className = "" }) {
    return (
        <label className={`form-field ${className}`}>
            <span className="form-label">{label}</span>
            {children}
            {hint && <small className="field-hint">{hint}</small>}
            {error && <small className="field-error">{error}</small>}
        </label>
    );
}

export function formatDate(value) {
    if (!value) {
        return "—";
    }
    return new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

export function getInitials(name = "") {
    return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "PF";
}

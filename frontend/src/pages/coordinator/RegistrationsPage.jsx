import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

export default function RegistrationsPage() {
    const [enrollments, setEnrollments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [filter, setFilter] = useState("pending_review");
    const [selected, setSelected] = useState(null);
    const [decision, setDecision] = useState("approve");
    const [notes, setNotes] = useState("");
    const [saving, setSaving] = useState(false);

    const loadEnrollments = useCallback(async () => {
        setLoading(true);
        try {
            setEnrollments(getList(await apiRequest(endpoints.enrollments)));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadEnrollments(); }, [loadEnrollments]);

    const visibleEnrollments = useMemo(() => enrollments.filter((item) => filter === "all" || item.verification_status === filter), [enrollments, filter]);

    function openReview(enrollment, nextDecision) {
        setSelected(enrollment);
        setDecision(nextDecision);
        setNotes("");
    }

    async function submitReview(event) {
        event.preventDefault();
        if (decision === "reject" && !notes.trim()) {
            setError("A reason is required when rejecting a student registration.");
            return;
        }
        setSaving(true);
        setError("");
        try {
            await apiRequest(`${endpoints.enrollments}${selected.id}/review/`, {
                method: "POST",
                body: { decision, notes },
            });
            setSuccess(`${selected.student_name}'s registration has been ${decision === "approve" ? "approved" : "rejected"}.`);
            setSelected(null);
            await loadEnrollments();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    const pendingCount = enrollments.filter((item) => item.verification_status === "pending_review").length;

    return (
        <>
            <PageHeader eyebrow="STUDENT ONBOARDING" title="Registration review" description="Review student registrations that could not be automatically verified against the departmental roster." />
            {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <div className="queue-summary"><div><span className="queue-summary-icon">◷</span><span><strong>{pendingCount}</strong><small>Awaiting manual review</small></span></div><p>Automatically verified students do not require manual approval. Rejected registrations remain in the historical record.</p></div>
            <section className="surface-card dashboard-table-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">REGISTRATION QUEUE</span><h2>Student registrations <span className="heading-count">{visibleEnrollments.length}</span></h2></div><div className="table-toolbar"><select aria-label="Filter registration status" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="pending_review">Pending review</option><option value="auto_verified">Automatically verified</option><option value="manually_approved">Manually approved</option><option value="rejected">Rejected</option><option value="all">All registrations</option></select></div></div>
                {loading ? <LoadingState /> : visibleEnrollments.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Student</th><th>Matriculation no.</th><th>Academic session</th><th>Verification</th><th>Registered</th><th>Action</th></tr></thead><tbody>
                    {visibleEnrollments.map((item) => <tr key={item.id}><td><strong>{item.student_name}</strong><small>{item.student_email}</small>{item.verification_notes && <small className="table-muted">{item.verification_notes}</small>}</td><td>{item.matric_number}</td><td>{item.session_name}</td><td><StatusBadge value={item.verification_status} /></td><td>{new Date(item.created_at).toLocaleDateString()}</td><td>{item.verification_status === "pending_review" ? <div className="table-actions"><button className="table-action table-action--primary" onClick={() => openReview(item, "approve")}>Approve</button><button className="table-action table-action--danger" onClick={() => openReview(item, "reject")}>Reject</button></div> : <span className="table-muted">Reviewed</span>}</td></tr>)}
                </tbody></table></div> : <EmptyState title="No registrations in this view" description={filter === "pending_review" ? "There are no student registrations awaiting manual verification." : "Try another status filter to view other registrations."} />}
            </section>
            {selected && <Modal title={decision === "approve" ? "Approve student registration" : "Reject student registration"} description={`${selected.student_name} · ${selected.matric_number}`} onClose={() => setSelected(null)}>
                <form className="modal-form" onSubmit={submitReview}>
                    <div className="review-student-summary"><span className="review-avatar">{selected.student_name?.slice(0, 1).toUpperCase()}</span><div><strong>{selected.student_name}</strong><small>{selected.student_email}</small><small>{selected.session_name}</small></div></div>
                    <Field label={decision === "approve" ? "Review notes (optional)" : "Reason for rejection"} hint={decision === "reject" ? "A clear reason is required and will be retained in the registration history." : "Add any relevant verification note."}><textarea rows="4" required={decision === "reject"} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder={decision === "reject" ? "Explain why this registration cannot be approved…" : "Optional review notes…"} /></Field>
                    <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setSelected(null)}>Cancel</button><button className={`button ${decision === "approve" ? "button-primary" : "button-danger"}`} disabled={saving}>{saving ? "Submitting…" : decision === "approve" ? "Confirm approval" : "Confirm rejection"}</button></div>
                </form>
            </Modal>}
        </>
    );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const filters = [
    { value: "submitted", label: "Awaiting review" },
    { value: "revision_requested", label: "Revision requested" },
    { value: "reviewed", label: "Reviewed" },
    { value: "all", label: "All reports" },
];

const assessments = [
    { value: "on_track", label: "On track" },
    { value: "needs_attention", label: "Needs attention" },
    { value: "behind_schedule", label: "Behind schedule" },
    { value: "completed", label: "Milestone completed" },
];

const assessmentLabels = Object.fromEntries(assessments.map((item) => [item.value, item.label]));

export default function ProgressReviewPage() {
    const [reports, setReports] = useState([]);
    const [activeFilter, setActiveFilter] = useState("submitted");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [selected, setSelected] = useState(null);
    const [decision, setDecision] = useState("review");
    const [assessment, setAssessment] = useState("on_track");
    const [feedback, setFeedback] = useState("");

    const loadReports = useCallback(async () => {
        setLoading(true);
        try {
            setReports(getList(await apiRequest(endpoints.progressReports)));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadReports(); }, [loadReports]);

    const counts = useMemo(() => ({
        submitted: reports.filter((item) => item.status === "submitted").length,
        revision_requested: reports.filter((item) => item.status === "revision_requested").length,
        reviewed: reports.filter((item) => item.status === "reviewed").length,
        all: reports.length,
    }), [reports]);
    const visibleReports = useMemo(
        () => activeFilter === "all" ? reports : reports.filter((item) => item.status === activeFilter),
        [activeFilter, reports],
    );

    function openReport(report) {
        setSelected(report);
        setDecision("review");
        setAssessment("on_track");
        setFeedback("");
        setError("");
    }

    async function submitReview(event) {
        event.preventDefault();
        if (decision === "request_revision" && !feedback.trim()) {
            setError("Please provide feedback explaining the requested changes.");
            return;
        }
        setSaving(true);
        setError("");
        setSuccess("");
        try {
            await apiRequest(`${endpoints.progressReports}${selected.id}/review/`, {
                method: "POST",
                body: { decision, assessment, feedback },
            });
            setSuccess(decision === "request_revision" ? "Revision requested successfully." : "Progress report reviewed successfully.");
            setSelected(null);
            await loadReports();
            setActiveFilter(decision === "request_revision" ? "revision_requested" : "reviewed");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    return (
        <>
            <PageHeader
                eyebrow="SUPERVISION"
                title="Student progress"
                description="Review milestone reports, assess progress and provide guidance to your supervisees."
                actions={<button className="button button-secondary" onClick={loadReports} disabled={loading}>Refresh</button>}
            />
            {error && !selected && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <section className="surface-card dashboard-table-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">SUPERVISION RECORDS</span><h2>{filters.find((item) => item.value === activeFilter)?.label} <span className="heading-count">{counts[activeFilter]}</span></h2></div></div>
                <div className="topic-filter-tabs" role="tablist" aria-label="Filter progress reports">
                    {filters.map((filter) => (
                        <button key={filter.value} type="button" role="tab" aria-selected={activeFilter === filter.value} className={`topic-filter-tab${activeFilter === filter.value ? " topic-filter-tab--active" : ""}`} onClick={() => setActiveFilter(filter.value)}>
                            {filter.label}<span>{counts[filter.value]}</span>
                        </button>
                    ))}
                </div>
                {loading ? <LoadingState /> : visibleReports.length ? (
                    <div className="progress-supervisor-list">
                        {visibleReports.map((report) => (
                            <article className="progress-supervisor-item" key={report.id}>
                                <div className="progress-supervisor-heading">
                                    <div><strong>{report.student_name}</strong><span>{report.matric_number} · {report.session_name}</span></div>
                                    <StatusBadge value={report.status} />
                                </div>
                                <h3>{report.milestone_title}</h3>
                                <p>{report.latest_revision?.completed_activities || "No report details available."}</p>
                                <div className="progress-supervisor-footer">
                                    <span>Submitted {new Date(report.submitted_at).toLocaleDateString()}</span>
                                    <button className="button button-secondary" onClick={() => openReport(report)}>{report.can_review ? "Review report" : "View report"}</button>
                                </div>
                            </article>
                        ))}
                    </div>
                ) : (
                    <EmptyState title="No progress reports in this section" description="Reports from your assigned students will appear here when they are submitted." />
                )}
            </section>
            {selected && (
                <Modal title={selected.can_review ? "Review progress report" : "Progress report"} description={`${selected.student_name} · ${selected.matric_number} · ${selected.milestone_title}`} onClose={() => setSelected(null)} size="wide">
                    <div className="progress-report-detail">
                        <div className="progress-detail-heading"><StatusBadge value={selected.status} /><span>Submitted {new Date(selected.submitted_at).toLocaleDateString()}</span></div>
                        <section><h3>Activities completed</h3><p>{selected.latest_revision?.completed_activities}</p></section>
                        {selected.latest_revision?.challenges && <section><h3>Challenges encountered</h3><p>{selected.latest_revision.challenges}</p></section>}
                        {selected.latest_revision?.next_steps && <section><h3>Planned next steps</h3><p>{selected.latest_revision.next_steps}</p></section>}
                        {selected.revisions?.length > 1 && <section><h3>Submission history</h3>{selected.revisions.map((revision) => <div className="progress-history-row" key={revision.id}><strong>Submission {revision.revision_number}</strong><span>{new Date(revision.submitted_at).toLocaleDateString()}</span></div>)}</section>}
                        {selected.reviews?.length > 0 && <section><h3>Previous assessments</h3>{selected.reviews.map((review) => <article className="progress-feedback-entry" key={review.id}><div><strong>{assessmentLabels[review.assessment] || review.assessment}</strong><span>{new Date(review.reviewed_at).toLocaleDateString()}</span></div>{review.feedback && <p>{review.feedback}</p>}</article>)}</section>}
                    </div>
                    {selected.can_review && (
                        <form className="modal-form progress-review-form" onSubmit={submitReview}>
                            {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
                            <Field label="Assessment"><select value={assessment} onChange={(event) => setAssessment(event.target.value)}>{assessments.map((item) => <option key={item.value} value={item.value} disabled={decision === "request_revision" && item.value === "completed"}>{item.label}</option>)}</select></Field>
                            <Field label="Decision"><select value={decision} onChange={(event) => { const nextDecision = event.target.value; setDecision(nextDecision); if (nextDecision === "request_revision" && assessment === "completed") setAssessment("needs_attention"); }}><option value="review">Complete review</option><option value="request_revision">Request revision</option></select></Field>
                            <Field label="Feedback" hint={decision === "request_revision" ? "Explain what the student needs to revise." : ["needs_attention", "behind_schedule"].includes(assessment) ? "Explain the concern and the action expected from the student." : "Provide guidance or recommendations (optional)."}><textarea rows="4" maxLength="5000" required={decision === "request_revision" || ["needs_attention", "behind_schedule"].includes(assessment)} value={feedback} onChange={(event) => setFeedback(event.target.value)} /></Field>
                            <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setSelected(null)}>Close</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : "Submit assessment"}</button></div>
                        </form>
                    )}
                </Modal>
            )}
        </>
    );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";
import { triggerDownload } from "../../utils/download.js";

const filters = [
    { value: "submitted", label: "Awaiting review" },
    { value: "revision_requested", label: "Revision requested" },
    { value: "approved", label: "Approved" },
    { value: "all", label: "All submissions" },
];

function formatFileSize(value) {
    if (!value) return "";
    if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ProgressReviewPage() {
    const [submissions, setSubmissions] = useState([]);
    const [activeFilter, setActiveFilter] = useState("submitted");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [downloadingId, setDownloadingId] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [selected, setSelected] = useState(null);
    const [decision, setDecision] = useState("approve");
    const [feedback, setFeedback] = useState("");
    const [annotation, setAnnotation] = useState(null);

    const loadSubmissions = useCallback(async () => {
        setLoading(true);
        try {
            setSubmissions(getList(await apiRequest(endpoints.reportSubmissions)));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadSubmissions(); }, [loadSubmissions]);

    const counts = useMemo(() => ({
        submitted: submissions.filter((item) => item.status === "submitted").length,
        revision_requested: submissions.filter((item) => item.status === "revision_requested").length,
        approved: submissions.filter((item) => item.status === "approved").length,
        all: submissions.length,
    }), [submissions]);
    const visibleSubmissions = useMemo(
        () => activeFilter === "all" ? submissions : submissions.filter((item) => item.status === activeFilter),
        [activeFilter, submissions],
    );

    function openSubmission(submission) {
        setSelected(submission);
        setDecision("approve");
        setFeedback("");
        setAnnotation(null);
        setError("");
    }

    async function downloadRevision(revision) {
        setDownloadingId(revision.id);
        setError("");
        try {
            const result = await apiRequest(revision.download_path);
            triggerDownload(result.url, revision.original_filename);
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setDownloadingId("");
        }
    }

    async function submitReview(event) {
        event.preventDefault();
        if (decision === "request_revision" && !feedback.trim()) {
            setError("Provide feedback explaining the changes required.");
            return;
        }
        setSaving(true);
        setError("");
        setSuccess("");
        try {
            const body = new FormData();
            body.append("decision", decision);
            body.append("feedback", feedback);
            if (annotation) body.append("annotation", annotation);
            await apiRequest(`${endpoints.reportSubmissions}${selected.id}/review/`, {
                method: "POST", body, formData: true, timeout: 120000,
            });
            setSuccess(decision === "request_revision" ? "Revision requested successfully." : "Report section approved successfully.");
            setSelected(null);
            await loadSubmissions();
            setActiveFilter(decision === "request_revision" ? "revision_requested" : "approved");
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
                title="Project report reviews"
                description="Review report documents from your assigned students, provide feedback and approve each section."
                actions={<button className="button button-secondary" onClick={loadSubmissions} disabled={loading}>Refresh</button>}
            />
            {error && !selected && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <section className="surface-card dashboard-table-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">SUPERVISION RECORDS</span><h2>{filters.find((item) => item.value === activeFilter)?.label} <span className="heading-count">{counts[activeFilter]}</span></h2></div></div>
                <div className="topic-filter-tabs" role="tablist" aria-label="Filter report submissions">
                    {filters.map((filter) => (
                        <button key={filter.value} type="button" role="tab" aria-selected={activeFilter === filter.value} className={`topic-filter-tab${activeFilter === filter.value ? " topic-filter-tab--active" : ""}`} onClick={() => setActiveFilter(filter.value)}>
                            {filter.label}<span>{counts[filter.value]}</span>
                        </button>
                    ))}
                </div>
                {loading ? <LoadingState /> : visibleSubmissions.length ? (
                    <div className="report-supervisor-list">
                        {visibleSubmissions.map((submission) => (
                            <article className="report-supervisor-item" key={submission.id}>
                                <div className="report-supervisor-heading">
                                    <div><strong>{submission.student_name}</strong><span>{submission.matric_number} · {submission.session_name}</span></div>
                                    <StatusBadge value={submission.status} />
                                </div>
                                <h3>{submission.section_title}</h3>
                                <div className="report-supervisor-file"><span className="report-file-symbol">DOC</span><div><strong>{submission.latest_revision?.original_filename || "Document unavailable"}</strong><span>{formatFileSize(submission.latest_revision?.file_size)} · Submitted {new Date(submission.submitted_at).toLocaleDateString()}</span></div></div>
                                {submission.latest_revision?.submission_note && <p className="report-supervisor-note">{submission.latest_revision.submission_note}</p>}
                                <div className="progress-supervisor-footer">
                                    <span>{submission.revisions?.length || 0} submission version{submission.revisions?.length === 1 ? "" : "s"}</span>
                                    <button className="button button-secondary" onClick={() => openSubmission(submission)}>{submission.can_review ? "Review section" : "View submission"}</button>
                                </div>
                            </article>
                        ))}
                    </div>
                ) : (
                    <EmptyState title="No report submissions in this section" description="Documents submitted by your assigned students will appear here." />
                )}
            </section>
            {selected && (
                <Modal title={selected.can_review ? "Review report section" : "Report section"} description={`${selected.student_name} · ${selected.matric_number} · ${selected.section_title}`} onClose={() => setSelected(null)} size="wide">
                    <div className="report-review-detail">
                        <div className="report-review-detail-heading"><StatusBadge value={selected.status} /><span>Latest submission {new Date(selected.submitted_at).toLocaleString()}</span></div>
                        <section>
                            <h3>Submitted document</h3>
                            {selected.revisions?.map((revision) => (
                                <article className="report-review-file-row" key={revision.id}>
                                    <div className="report-file-symbol">DOC</div>
                                    <div><strong>Version {revision.revision_number}: {revision.original_filename}</strong><span>{formatFileSize(revision.file_size)} · {new Date(revision.submitted_at).toLocaleString()}</span></div>
                                    <button type="button" className="table-action table-action--primary" disabled={downloadingId === revision.id} onClick={() => downloadRevision(revision)}>{downloadingId === revision.id ? "Preparing…" : "Download"}</button>
                                    {revision.submission_note && <p>{revision.submission_note}</p>}
                                </article>
                            ))}
                        </section>
                        {selected.reviews?.length > 0 && (
                            <section>
                                <h3>Review history</h3>
                                {selected.reviews.map((review) => (
                                    <article className="report-review-history-entry" key={review.id}>
                                        <div><strong>{review.decision === "approve" ? "Section approved" : "Revision requested"}</strong><span>{review.reviewer_name} · {new Date(review.reviewed_at).toLocaleDateString()}</span></div>
                                        {review.feedback && <p>{review.feedback}</p>}
                                        {review.annotation_download_path && <button type="button" className="table-action table-action--primary" onClick={() => downloadRevision({ id: review.id, download_path: review.annotation_download_path, original_filename: review.annotation_filename })}>Download annotated copy: {review.annotation_filename}</button>}
                                    </article>
                                ))}
                            </section>
                        )}
                    </div>
                    {selected.can_review && (
                        <form className="modal-form report-review-form" onSubmit={submitReview}>
                            {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
                            <Field label="Decision"><select value={decision} onChange={(event) => setDecision(event.target.value)}><option value="approve">Approve section</option><option value="request_revision">Request revision</option></select></Field>
                            <Field label="Feedback" hint={decision === "request_revision" ? "Explain the corrections the student must make." : "Add any academic comments or recommendations (optional)."}><textarea rows="4" maxLength="5000" required={decision === "request_revision"} value={feedback} onChange={(event) => setFeedback(event.target.value)} /></Field>
                            <Field label="Annotated document (optional)" hint="Upload a corrected PDF or DOCX, up to 20 MB."><input type="file" accept=".pdf,.docx" onChange={(event) => setAnnotation(event.target.files[0] || null)} /></Field>
                            <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setSelected(null)}>Close</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : decision === "approve" ? "Approve section" : "Request revision"}</button></div>
                        </form>
                    )}
                </Modal>
            )}
        </>
    );
}

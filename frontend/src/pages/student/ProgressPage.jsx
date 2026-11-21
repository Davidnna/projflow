import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";
import { triggerDownload } from "../../utils/download.js";

const emptyForm = { file: null, submission_note: "" };

function formatFileSize(value) {
    if (!value) return "";
    if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function ReportHistory({ submission, onDownload }) {
    return (
        <div className="report-submission-history">
            {submission.revisions?.length > 0 && (
                <details>
                    <summary>Submission history ({submission.revisions.length})</summary>
                    <div className="report-history-list">
                        {submission.revisions.map((revision) => (
                            <article className="report-history-entry" key={revision.id}>
                                <div className="report-history-entry-copy">
                                    <strong>Submission {revision.revision_number}</strong>
                                    <span>{new Date(revision.submitted_at).toLocaleString()}</span>
                                    <small>{revision.original_filename} · {formatFileSize(revision.file_size)}</small>
                                </div>
                                <button type="button" className="table-action table-action--primary" onClick={() => onDownload(revision)}>Download</button>
                                {revision.submission_note && <p>{revision.submission_note}</p>}
                            </article>
                        ))}
                    </div>
                </details>
            )}
            {submission.reviews?.length > 0 && (
                <div className="report-feedback-list">
                    <h4>Supervisor feedback</h4>
                    {submission.reviews.map((review) => (
                        <article key={review.id}>
                            <div><strong>{review.decision === "approve" ? "Section approved" : "Revision requested"}</strong><span>{new Date(review.reviewed_at).toLocaleDateString()}</span></div>
                            {review.feedback && <p>{review.feedback}</p>}
                        </article>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function ProgressPage() {
    const [sections, setSections] = useState([]);
    const [submissions, setSubmissions] = useState([]);
    const [enrollment, setEnrollment] = useState(null);
    const [assignment, setAssignment] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [downloadingId, setDownloadingId] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [selectedSection, setSelectedSection] = useState(null);
    const [editingSubmission, setEditingSubmission] = useState(null);
    const [form, setForm] = useState(emptyForm);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [enrollmentData, assignmentData, sectionData, submissionData] = await Promise.all([
                apiRequest(`${endpoints.enrollments}mine/`),
                apiRequest(endpoints.assignments),
                apiRequest(endpoints.reportSections),
                apiRequest(endpoints.reportSubmissions),
            ]);
            setEnrollment(enrollmentData);
            setAssignment(getList(assignmentData).find(
                (item) => item.is_current && item.session_name === enrollmentData.session_name,
            ) || null);
            setSections(getList(sectionData));
            setSubmissions(getList(submissionData));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const verified = ["auto_verified", "manually_approved"].includes(enrollment?.verification_status);
    const sessionSections = useMemo(
        () => sections.filter((item) => item.session_name === enrollment?.session_name).sort((a, b) => a.sequence - b.sequence),
        [sections, enrollment?.session_name],
    );
    const sessionActive = sessionSections.some((item) => item.session_status === "active");
    const sessionSubmissions = useMemo(
        () => submissions.filter((item) => item.session_name === enrollment?.session_name),
        [submissions, enrollment?.session_name],
    );
    const submissionsBySection = useMemo(
        () => new Map(sessionSubmissions.map((submission) => [submission.section, submission])),
        [sessionSubmissions],
    );
    const unlockedSectionIds = useMemo(() => {
        const unlocked = new Set();
        let blocked = false;
        sessionSections.filter((section) => section.is_active).forEach((section) => {
            if (blocked) return;
            unlocked.add(section.id);
            const submission = submissionsBySection.get(section.id);
            if (!submission) {
                if (section.is_required) blocked = true;
            } else if (submission.status !== "approved") {
                blocked = true;
            }
        });
        return unlocked;
    }, [sessionSections, submissionsBySection]);
    const approvedCount = sessionSubmissions.filter((item) => item.status === "approved").length;
    const requiredCount = sessionSections.filter((item) => item.is_active && item.is_required).length;

    function openSubmit(section, submission = null) {
        setSelectedSection(section);
        setEditingSubmission(submission);
        setForm({ file: null, submission_note: "" });
        setError("");
    }

    function closeModal() {
        setSelectedSection(null);
        setEditingSubmission(null);
        setForm(emptyForm);
    }

    async function submitSection(event) {
        event.preventDefault();
        if (!form.file) {
            setError("Select a PDF or DOCX document to continue.");
            return;
        }
        const extension = form.file.name.toLowerCase().split(".").pop();
        if (!["pdf", "docx"].includes(extension)) {
            setError("Upload the report section as a PDF or DOCX document.");
            return;
        }
        if (form.file.size > 20 * 1024 * 1024) {
            setError("Each report document must not exceed 20 MB.");
            return;
        }
        setSaving(true);
        setError("");
        setSuccess("");
        const body = new FormData();
        body.append("file", form.file);
        body.append("submission_note", form.submission_note.trim());
        if (!editingSubmission) body.append("section", selectedSection.id);
        try {
            if (editingSubmission) {
                await apiRequest(`${endpoints.reportSubmissions}${editingSubmission.id}/resubmit/`, {
                    method: "POST",
                    body,
                    formData: true,
                    timeout: 120000,
                });
                setSuccess("Your revised report section has been submitted.");
            } else {
                await apiRequest(endpoints.reportSubmissions, {
                    method: "POST",
                    body,
                    formData: true,
                    timeout: 120000,
                });
                setSuccess("Your report section has been submitted to your supervisor.");
            }
            closeModal();
            await loadData();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
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

    return (
        <>
            <PageHeader
                eyebrow="PROJECT REPORT"
                title="My project report"
                description="Submit each part of your report as a separate document and follow your supervisor's feedback."
                actions={<button className="button button-secondary" onClick={loadData} disabled={loading}>Refresh</button>}
            />
            {error && !selectedSection && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            {loading ? <LoadingState /> : (
                <>
                    {!verified && <Alert type="warning">Your student registration must be verified before you can submit report sections.</Alert>}
                    {verified && !assignment && <Alert type="info">Your supervisor must be assigned before you can submit report sections.</Alert>}
                    {verified && assignment && !sessionActive && sessionSections.length > 0 && <Alert type="info">Your academic session is not currently active. You can still view previous submissions and feedback.</Alert>}
                    {!sessionSections.length ? (
                        <EmptyState title="Your report structure is not available yet" description="The report sections for your academic session will appear here when they have been configured by the department." />
                    ) : (
                        <>
                            <div className="progress-summary-strip report-summary-strip">
                                <div><span>Academic session</span><strong>{enrollment?.session_name || "—"}</strong></div>
                                <div><span>Supervisor</span><strong>{assignment?.lecturer_name || sessionSubmissions[0]?.supervisor_name || "Not currently assigned"}</strong></div>
                                <div><span>Required sections approved</span><strong>{approvedCount} of {requiredCount}</strong></div>
                            </div>
                            <div className="report-section-list">
                                {sessionSections.map((section) => {
                                    const submission = submissionsBySection.get(section.id);
                                    const unlocked = unlockedSectionIds.has(section.id);
                                    const latest = submission?.latest_revision;
                                    const canSubmit = Boolean(
                                        verified && assignment && sessionActive && section.is_active && unlocked && !submission,
                                    );
                                    const canRevise = Boolean(
                                        verified && assignment && sessionActive && section.is_active && unlocked && submission?.can_resubmit,
                                    );
                                    const state = submission?.status || (!section.is_active ? "inactive" : unlocked ? "not_submitted" : "locked");
                                    return (
                                        <article className={`surface-card report-section-card${!unlocked && !submission ? " report-section-card--locked" : ""}`} key={section.id}>
                                            <div className="report-section-top">
                                                <div className="report-section-number">{section.sequence}</div>
                                                <div className="report-section-heading">
                                                    <div><span className="panel-eyebrow">REPORT SECTION {section.sequence}</span><h2>{section.title}</h2></div>
                                                    <div className="report-section-badges"><StatusBadge value={state} />{!section.is_required && <span className="report-required-label report-required-label--optional">Optional</span>}</div>
                                                </div>
                                            </div>
                                            {section.description && <p className="report-section-description">{section.description}</p>}
                                            <div className="report-section-footer">
                                                <span>{section.due_date ? `Due ${new Date(`${section.due_date}T00:00:00`).toLocaleDateString()}` : "No due date"}</span>
                                                {canSubmit && <button className="button button-primary" onClick={() => openSubmit(section)}>Upload section</button>}
                                                {canRevise && <button className="button button-primary" onClick={() => openSubmit(section, submission)}>Upload revised section</button>}
                                                {submission && !canRevise && <span className="report-section-submitted">Submitted {new Date(submission.submitted_at).toLocaleDateString()}</span>}
                                                {!submission && !unlocked && section.is_active && <span className="report-section-locked-label">Complete the previous required section first</span>}
                                                {!section.is_active && !submission && <span className="report-section-locked-label">Not currently available</span>}
                                            </div>
                                            {submission && latest && (
                                                <div className="report-current-submission">
                                                    <div className="report-current-file">
                                                        <div className="report-file-symbol">DOC</div>
                                                        <div><strong>{latest.original_filename}</strong><span>{formatFileSize(latest.file_size)} · {new Date(latest.submitted_at).toLocaleString()}</span></div>
                                                        <button type="button" className="table-action table-action--primary" disabled={downloadingId === latest.id} onClick={() => downloadRevision(latest)}>{downloadingId === latest.id ? "Preparing…" : "Download"}</button>
                                                    </div>
                                                    {latest.submission_note && <p className="report-submission-note"><strong>Submission note:</strong> {latest.submission_note}</p>}
                                                    <ReportHistory submission={submission} onDownload={(revision) => downloadRevision(revision)} />
                                                </div>
                                            )}
                                        </article>
                                    );
                                })}
                            </div>
                        </>
                    )}
                </>
            )}
            {selectedSection && (
                <Modal title={editingSubmission ? "Resubmit report section" : "Submit report section"} description={selectedSection.title} onClose={closeModal} size="wide">
                    <form className="modal-form report-upload-form" onSubmit={submitSection}>
                        {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
                        <Field label="Report document" hint="Upload a PDF or DOCX file. Maximum file size: 20 MB.">
                            <input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required onChange={(event) => setForm({ ...form, file: event.target.files?.[0] || null })} />
                        </Field>
                        {form.file && <div className="report-selected-file"><strong>{form.file.name}</strong><span>{formatFileSize(form.file.size)}</span></div>}
                        <Field label="Submission note (optional)" hint="Add a short note for your supervisor if there is anything they should know about this submission."><textarea rows="3" maxLength="5000" value={form.submission_note} onChange={(event) => setForm({ ...form, submission_note: event.target.value })} /></Field>
                        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={closeModal}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Uploading…" : editingSubmission ? "Submit revision" : "Submit section"}</button></div>
                    </form>
                </Modal>
            )}
        </>
    );
}

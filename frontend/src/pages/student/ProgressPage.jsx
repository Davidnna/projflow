import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const emptyForm = { completed_activities: "", challenges: "", next_steps: "" };

const assessmentLabels = {
    on_track: "On track",
    needs_attention: "Needs attention",
    behind_schedule: "Behind schedule",
    completed: "Milestone completed",
};

function ReportHistory({ report }) {
    return (
        <div className="progress-history">
            {report.revisions?.length > 0 && (
                <details>
                    <summary>Submission history ({report.revisions.length})</summary>
                    <div className="progress-history-list">
                        {report.revisions.map((revision) => (
                            <article key={revision.id}>
                                <strong>Submission {revision.revision_number}</strong>
                                <span>{new Date(revision.submitted_at).toLocaleDateString()}</span>
                                <p>{revision.completed_activities}</p>
                            </article>
                        ))}
                    </div>
                </details>
            )}
            {report.reviews?.length > 0 && (
                <div className="progress-feedback-list">
                    <h4>Supervisor feedback</h4>
                    {report.reviews.map((review) => (
                        <article key={review.id}>
                            <div><strong>{assessmentLabels[review.assessment] || review.assessment}</strong><span>{new Date(review.reviewed_at).toLocaleDateString()}</span></div>
                            {review.feedback && <p>{review.feedback}</p>}
                        </article>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function ProgressPage() {
    const [milestones, setMilestones] = useState([]);
    const [reports, setReports] = useState([]);
    const [enrollment, setEnrollment] = useState(null);
    const [assignment, setAssignment] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [selectedMilestone, setSelectedMilestone] = useState(null);
    const [editingReport, setEditingReport] = useState(null);
    const [form, setForm] = useState(emptyForm);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [enrollmentData, assignmentData, milestoneData, reportData] = await Promise.all([
                apiRequest(`${endpoints.enrollments}mine/`),
                apiRequest(endpoints.assignments),
                apiRequest(endpoints.milestones),
                apiRequest(endpoints.progressReports),
            ]);
            setEnrollment(enrollmentData);
            setAssignment(getList(assignmentData).find(
                (item) => item.is_current && item.session_name === enrollmentData.session_name,
            ) || null);
            setMilestones(getList(milestoneData));
            setReports(getList(reportData));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const verified = ["auto_verified", "manually_approved"].includes(enrollment?.verification_status);
    const sessionMilestones = useMemo(
        () => milestones.filter((item) => item.session_name === enrollment?.session_name).sort((a, b) => a.sequence - b.sequence),
        [milestones, enrollment?.session_name],
    );
    const sessionReports = useMemo(
        () => reports.filter((item) => item.session_name === enrollment?.session_name),
        [reports, enrollment?.session_name],
    );
    const reportsByMilestone = useMemo(
        () => new Map(sessionReports.map((report) => [report.milestone, report])),
        [sessionReports],
    );

    function openSubmit(milestone, report = null) {
        setSelectedMilestone(milestone);
        setEditingReport(report);
        const latest = report?.latest_revision;
        setForm(latest ? {
            completed_activities: latest.completed_activities || "",
            challenges: latest.challenges || "",
            next_steps: latest.next_steps || "",
        } : emptyForm);
        setError("");
    }

    function closeModal() {
        setSelectedMilestone(null);
        setEditingReport(null);
        setForm(emptyForm);
    }

    async function submitReport(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        setSuccess("");
        try {
            const payload = {
                completed_activities: form.completed_activities.trim(),
                challenges: form.challenges.trim(),
                next_steps: form.next_steps.trim(),
            };
            if (editingReport) {
                await apiRequest(`${endpoints.progressReports}${editingReport.id}/resubmit/`, {
                    method: "POST",
                    body: payload,
                });
                setSuccess("Your revised progress report has been submitted.");
            } else {
                await apiRequest(endpoints.progressReports, {
                    method: "POST",
                    body: { milestone: selectedMilestone.id, ...payload },
                });
                setSuccess("Your progress report has been submitted to your supervisor.");
            }
            closeModal();
            await loadData();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    return (
        <>
            <PageHeader
                eyebrow="PROJECT WORK"
                title="Project progress"
                description="Submit progress updates at each project milestone and review your supervisor's feedback."
                actions={<button className="button button-secondary" onClick={loadData} disabled={loading}>Refresh</button>}
            />
            {error && !selectedMilestone && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            {loading ? <LoadingState /> : (
                <>
                    {!verified && <Alert type="warning">Your student registration must be verified before you can submit progress reports.</Alert>}
                    {verified && !assignment && <Alert type="info">Your supervisor must be assigned before you can submit new progress reports.</Alert>}
                    {!sessionMilestones.length && <EmptyState title="Project milestones are not available yet" description="Your project milestones will appear here when they have been set for your academic session." />}
                    {sessionMilestones.length > 0 && (
                        <>
                    <div className="progress-summary-strip">
                        <div><span>Academic session</span><strong>{enrollment?.session_name || "—"}</strong></div>
                        <div><span>Supervisor</span><strong>{assignment?.lecturer_name || sessionReports[0]?.supervisor_name || "Not currently assigned"}</strong></div>
                        <div><span>Reports submitted</span><strong>{sessionReports.length} of {sessionMilestones.length}</strong></div>
                    </div>
                    <div className="progress-milestone-list">
                        {sessionMilestones.map((milestone) => {
                            const report = reportsByMilestone.get(milestone.id);
                            const canSubmit = Boolean(verified && assignment && milestone.is_active && !report);
                            const canRevise = Boolean(assignment && milestone.is_active && report?.can_resubmit);
                            const latest = report?.latest_revision;
                            return (
                                <article className="surface-card progress-milestone-card" key={milestone.id}>
                                    <div className="progress-milestone-top">
                                        <div className="milestone-number">{milestone.sequence}</div>
                                        <div className="progress-milestone-title"><span className="panel-eyebrow">PROJECT MILESTONE</span><h2>{milestone.title}</h2></div>
                                        {report ? <StatusBadge value={report.status} /> : <StatusBadge value={milestone.is_active && sessionActive ? "not_submitted" : "inactive"} />}
                                    </div>
                                    {milestone.description && <p className="progress-milestone-description">{milestone.description}</p>}
                                    {milestone.expected_achievement && <div className="progress-expected"><strong>Expected achievement</strong><p>{milestone.expected_achievement}</p></div>}
                                    <div className="progress-milestone-footer">
                                        <span>{milestone.due_date ? `Due ${new Date(`${milestone.due_date}T00:00:00`).toLocaleDateString()}` : "No due date set"}</span>
                                        {canSubmit && <button className="button button-primary" onClick={() => openSubmit(milestone)}>Submit progress report</button>}
                                        {canRevise && <button className="button button-primary" onClick={() => openSubmit(milestone, report)}>Revise report</button>}
                                        {report && !canRevise && <span className="progress-submitted-label">Submitted {new Date(report.submitted_at).toLocaleDateString()}</span>}
                                        {!report && (!milestone.is_active || !sessionActive) && <span className="progress-submitted-label">Not currently available</span>}
                                    </div>
                                    {report && latest && (
                                        <div className="progress-report-content">
                                            <div><h3>Completed activities</h3><p>{latest.completed_activities}</p></div>
                                            {latest.challenges && <div><h3>Challenges</h3><p>{latest.challenges}</p></div>}
                                            {latest.next_steps && <div><h3>Next steps</h3><p>{latest.next_steps}</p></div>}
                                            <ReportHistory report={report} />
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
            {selectedMilestone && (
                <Modal title={editingReport ? "Revise progress report" : "Submit progress report"} description={selectedMilestone.title} onClose={closeModal} size="wide">
                    <form className="modal-form progress-report-form" onSubmit={submitReport}>
                        {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
                        <Field label="Activities completed" hint="Describe the work you have completed for this milestone."><textarea required rows="5" maxLength="10000" value={form.completed_activities} onChange={(event) => setForm({ ...form, completed_activities: event.target.value })} /></Field>
                        <Field label="Challenges encountered" hint="You may leave this blank if you have not encountered any challenges."><textarea rows="4" maxLength="5000" value={form.challenges} onChange={(event) => setForm({ ...form, challenges: event.target.value })} /></Field>
                        <Field label="Planned next steps"><textarea rows="4" maxLength="5000" value={form.next_steps} onChange={(event) => setForm({ ...form, next_steps: event.target.value })} /></Field>
                        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={closeModal}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Submitting…" : editingReport ? "Resubmit report" : "Submit report"}</button></div>
                    </form>
                </Modal>
            )}
        </>
    );
}

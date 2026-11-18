import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const emptyForm = {
    title: "",
    abstract: "",
    problem_statement: "",
    research_objectives: "",
    keywords: "",
};

function topicToForm(topic) {
    return {
        title: topic.title || "",
        abstract: topic.abstract || "",
        problem_statement: topic.problem_statement || "",
        research_objectives: topic.research_objectives || "",
        keywords: (topic.keywords || []).join(", "),
    };
}

function toPayload(form) {
    return {
        title: form.title.trim(),
        abstract: form.abstract.trim(),
        problem_statement: form.problem_statement.trim(),
        research_objectives: form.research_objectives.trim(),
        keywords: form.keywords.split(",").map((item) => item.trim()).filter(Boolean),
    };
}

function ReviewHistory({ reviews = [] }) {
    if (!reviews.length) {
        return null;
    }
    return (
        <div className="topic-review-history">
            <h3>Supervisor feedback</h3>
            {reviews.map((review) => (
                <article className="topic-review-item" key={review.id}>
                    <div className="topic-review-heading">
                        <StatusBadge value={review.decision === "approve" ? "approved" : review.decision === "request_revision" ? "revision_requested" : "rejected"} />
                        <span>{new Date(review.reviewed_at).toLocaleDateString()}</span>
                    </div>
                    {review.feedback && <p>{review.feedback}</p>}
                </article>
            ))}
        </div>
    );
}

function TopicSummary({ topic, onRevise }) {
    const latestRevision = topic.revisions?.[topic.revisions.length - 1];
    return (
        <section className="surface-card topic-summary-card">
            <div className="surface-card-heading">
                <div>
                    <span className="panel-eyebrow">YOUR PROJECT TOPIC</span>
                    <h2>{topic.title}</h2>
                </div>
                <StatusBadge value={topic.status} />
            </div>
            <div className="topic-summary-meta">
                <span>Supervisor: <strong>{topic.supervisor_name || "Not assigned"}</strong></span>
                <span>Submitted: <strong>{new Date(topic.submitted_at).toLocaleDateString()}</strong></span>
                <span>Revision: <strong>{latestRevision?.revision_number || 1}</strong></span>
            </div>
            <div className="topic-content-block">
                <h3>Abstract</h3>
                <p>{topic.abstract}</p>
            </div>
            <div className="topic-content-block">
                <h3>Problem statement</h3>
                <p>{topic.problem_statement}</p>
            </div>
            <div className="topic-content-block">
                <h3>Research objectives</h3>
                <p>{topic.research_objectives}</p>
            </div>
            <div className="topic-keywords">{(topic.keywords || []).map((keyword) => <span key={keyword}>{keyword}</span>)}</div>
            {topic.status === "submitted" && <Alert type="info">Your proposal has been sent to your supervisor for review.</Alert>}
            {topic.status === "approved" && <Alert type="success">Your project topic has been approved.</Alert>}
            {topic.status === "revision_requested" && (
                <div className="topic-revision-action">
                    <Alert type="warning">Your supervisor has requested changes. Review the feedback and submit an updated proposal.</Alert>
                    <button className="button button-primary" onClick={() => onRevise(topic)}>Revise and resubmit</button>
                </div>
            )}
            <ReviewHistory reviews={topic.reviews} />
        </section>
    );
}

export default function ProjectTopicPage() {
    const [topics, setTopics] = useState([]);
    const [enrollment, setEnrollment] = useState(null);
    const [assignment, setAssignment] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [editingTopic, setEditingTopic] = useState(null);
    const [modalOpen, setModalOpen] = useState(false);
    const [form, setForm] = useState(emptyForm);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [topicData, enrollmentData, assignmentData] = await Promise.all([
                apiRequest(`${endpoints.topics}mine/`),
                apiRequest(`${endpoints.enrollments}mine/`),
                apiRequest(endpoints.assignments),
            ]);
            setTopics(getList(topicData));
            setEnrollment(enrollmentData);
            setAssignment(getList(assignmentData).find((item) => item.is_current) || null);
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const currentTopic = useMemo(() => topics.find((topic) => topic.is_current) || null, [topics]);
    const previousTopics = useMemo(() => topics.filter((topic) => !topic.is_current), [topics]);
    const verified = ["auto_verified", "manually_approved"].includes(enrollment?.verification_status);

    function openNewProposal() {
        setEditingTopic(null);
        setForm(emptyForm);
        setModalOpen(true);
        setError("");
    }

    function openRevision(topic) {
        setEditingTopic(topic);
        setForm(topicToForm(topic));
        setModalOpen(true);
        setError("");
    }

    async function submitProposal(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        setSuccess("");
        try {
            const payload = toPayload(form);
            if (editingTopic) {
                await apiRequest(`${endpoints.topics}${editingTopic.id}/resubmit/`, {
                    method: "POST",
                    body: payload,
                    timeout: 120000,
                });
                setSuccess("Your revised project topic has been submitted to your supervisor.");
            } else {
                await apiRequest(endpoints.topics, {
                    method: "POST",
                    body: payload,
                    timeout: 120000,
                });
                setSuccess("Your project topic has been submitted to your supervisor.");
            }
            setEditingTopic(null);
            setModalOpen(false);
            setForm(emptyForm);
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
                title="My project topic"
                description="Submit your proposed research topic and follow your supervisor's feedback."
                actions={!currentTopic && verified && assignment ? <button className="button button-primary" onClick={openNewProposal}>＋ Submit topic</button> : null}
            />
            {error && !modalOpen && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            {loading ? <LoadingState /> : (
                <>
                    {!verified && <Alert type="warning">Your student registration must be complete before you can submit a project topic.</Alert>}
                    {verified && !assignment && <Alert type="info">Your supervisor has not yet been assigned. You can submit your project topic once an assignment has been made.</Alert>}
                    {currentTopic ? (
                        <TopicSummary topic={currentTopic} onRevise={openRevision} />
                    ) : verified && assignment ? (
                        <section className="surface-card topic-start-card">
                            <div className="topic-start-icon">✎</div>
                            <h2>Submit your project proposal</h2>
                            <p>Prepare your proposed title, abstract, problem statement, research objectives and keywords. Your proposal will be sent to your assigned supervisor.</p>
                            <div className="topic-supervisor-note">Your supervisor: <strong>{assignment.lecturer_name}</strong></div>
                            <button className="button button-primary" onClick={openNewProposal}>Start proposal</button>
                        </section>
                    ) : null}
                    {previousTopics.length > 0 && (
                        <section className="surface-card dashboard-table-card topic-history-card">
                            <div className="surface-card-heading"><div><span className="panel-eyebrow">PREVIOUS PROPOSALS</span><h2>Submission history</h2></div></div>
                            <div className="table-scroll"><table className="data-table"><thead><tr><th>Project topic</th><th>Submitted</th><th>Status</th></tr></thead><tbody>
                                {previousTopics.map((topic) => <tr key={topic.id}><td><strong>{topic.title}</strong></td><td>{new Date(topic.submitted_at).toLocaleDateString()}</td><td><StatusBadge value={topic.status} /></td></tr>)}
                            </tbody></table></div>
                        </section>
                    )}
                    {!currentTopic && !previousTopics.length && (!verified || !assignment) && <EmptyState title="Your project topic will appear here" description="Once your registration is verified and a supervisor is assigned, you can submit your proposal." />}
                </>
            )}
            {modalOpen && verified && assignment && (
                <Modal
                    title={editingTopic ? "Revise project proposal" : "Submit project proposal"}
                    description="Complete each section before submitting your proposal for supervisor review."
                    onClose={() => { setEditingTopic(null); setModalOpen(false); }}
                    size="wide"
                >
                    <form className="modal-form topic-form" onSubmit={submitProposal}>
                        {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
                        <Field label="Proposed project title"><input required maxLength="300" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Enter your proposed project title" /></Field>
                        <Field label="Abstract" hint="Provide a concise summary of the proposed study."><textarea required rows="5" value={form.abstract} onChange={(event) => setForm({ ...form, abstract: event.target.value })} /></Field>
                        <Field label="Problem statement" hint="Explain the problem your project intends to address."><textarea required rows="5" value={form.problem_statement} onChange={(event) => setForm({ ...form, problem_statement: event.target.value })} /></Field>
                        <Field label="Research objectives" hint="State the main aim and specific objectives."><textarea required rows="4" value={form.research_objectives} onChange={(event) => setForm({ ...form, research_objectives: event.target.value })} /></Field>
                        <Field label="Keywords" hint="Separate keywords with commas. Enter at least one keyword."><input required value={form.keywords} onChange={(event) => setForm({ ...form, keywords: event.target.value })} placeholder="e.g. machine learning, health informatics, prediction" /></Field>
                        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => { setEditingTopic(null); setModalOpen(false); }}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Submitting…" : editingTopic ? "Resubmit proposal" : "Submit proposal"}</button></div>
                    </form>
                </Modal>
            )}
        </>
    );
}

import { useCallback, useEffect, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const decisions = [
    { value: "approve", label: "Approve topic", tone: "button-primary" },
    { value: "request_revision", label: "Request revision", tone: "button-secondary" },
    { value: "reject", label: "Reject topic", tone: "button-danger" },
];

export default function TopicReviewPage() {
    const [topics, setTopics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [selected, setSelected] = useState(null);
    const [decision, setDecision] = useState("approve");
    const [feedback, setFeedback] = useState("");

    const loadTopics = useCallback(async () => {
        setLoading(true);
        try {
            setTopics(getList(await apiRequest(`${endpoints.topics}review-queue/`)));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadTopics(); }, [loadTopics]);

    function openReview(topic, nextDecision) {
        setSelected(topic);
        setDecision(nextDecision);
        setFeedback("");
        setError("");
    }

    async function submitReview(event) {
        event.preventDefault();
        if (decision !== "approve" && !feedback.trim()) {
            setError("Please provide feedback for this decision.");
            return;
        }
        setSaving(true);
        setError("");
        setSuccess("");
        try {
            await apiRequest(`${endpoints.topics}${selected.id}/review/`, {
                method: "POST",
                body: { decision, feedback },
            });
            const messages = {
                approve: "The project topic has been approved.",
                request_revision: "Revision has been requested. The student can now update the proposal.",
                reject: "The project topic has been rejected.",
            };
            setSuccess(messages[decision]);
            setSelected(null);
            await loadTopics();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    return (
        <>
            <PageHeader eyebrow="SUPERVISION" title="Project topic reviews" description="Review proposals submitted by students assigned to you." />
            {error && !selected && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <section className="surface-card dashboard-table-card topic-queue-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">AWAITING YOUR REVIEW</span><h2>Submitted proposals <span className="heading-count">{topics.length}</span></h2></div></div>
                {loading ? <LoadingState /> : topics.length ? (
                    <div className="topic-queue-list">
                        {topics.map((topic) => (
                            <article className="topic-queue-item" key={topic.id}>
                                <div className="topic-queue-main">
                                    <div className="topic-queue-student"><strong>{topic.student_name}</strong><span>{topic.matric_number} · {topic.session_name}</span></div>
                                    <StatusBadge value={topic.status} />
                                </div>
                                <h3>{topic.title}</h3>
                                <p>{topic.abstract}</p>
                                <div className="topic-keywords">{(topic.keywords || []).map((keyword) => <span key={keyword}>{keyword}</span>)}</div>
                                <div className="topic-queue-actions">
                                    <button className="button button-secondary" onClick={() => openReview(topic, "approve")}>Review proposal</button>
                                    <span>Submitted {new Date(topic.submitted_at).toLocaleDateString()}</span>
                                </div>
                            </article>
                        ))}
                    </div>
                ) : <EmptyState title="No proposals awaiting review" description="New submissions from your assigned students will appear here." />}
            </section>
            {selected && (
                <Modal title="Review project proposal" description={`${selected.student_name} · ${selected.matric_number}`} onClose={() => setSelected(null)} size="wide">
                    <div className="topic-review-detail">
                        <h2>{selected.title}</h2>
                        <div className="topic-content-block"><h3>Abstract</h3><p>{selected.abstract}</p></div>
                        <div className="topic-content-block"><h3>Problem statement</h3><p>{selected.problem_statement}</p></div>
                        <div className="topic-content-block"><h3>Research objectives</h3><p>{selected.research_objectives}</p></div>
                        <div className="topic-keywords">{(selected.keywords || []).map((keyword) => <span key={keyword}>{keyword}</span>)}</div>
                        {selected.revisions?.length > 1 && (
                            <div className="topic-revision-list"><h3>Submission history</h3>{selected.revisions.map((revision) => <div key={revision.id}><strong>Revision {revision.revision_number}</strong><span>{new Date(revision.submitted_at).toLocaleDateString()}</span></div>)}</div>
                        )}
                        {selected.reviews?.length > 0 && (
                            <div className="topic-review-history">
                                <h3>Previous review feedback</h3>
                                {selected.reviews.map((review) => (
                                    <article className="topic-review-item" key={review.id}>
                                        <div className="topic-review-heading">
                                            <StatusBadge value={review.decision === "approve" ? "approved" : review.decision === "request_revision" ? "revision_requested" : "rejected"} />
                                            <span>{new Date(review.reviewed_at).toLocaleDateString()}</span>
                                        </div>
                                        {review.feedback && <p>{review.feedback}</p>}
                                    </article>
                                ))}
                            </div>
                        )}
                    </div>
                    <form className="modal-form topic-review-form" onSubmit={submitReview}>
                        {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
                        <Field label="Decision"><select value={decision} onChange={(event) => setDecision(event.target.value)}>{decisions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></Field>
                        <Field label={decision === "approve" ? "Feedback (optional)" : "Feedback to student"} hint={decision === "approve" ? "You may add a note for the student." : "Explain the changes required or the reason for rejection."}><textarea rows="4" required={decision !== "approve"} value={feedback} onChange={(event) => setFeedback(event.target.value)} /></Field>
                        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setSelected(null)}>Cancel</button><button className={`button ${decisions.find((item) => item.value === decision)?.tone || "button-primary"}`} disabled={saving}>{saving ? "Submitting…" : "Submit decision"}</button></div>
                    </form>
                </Modal>
            )}
        </>
    );
}

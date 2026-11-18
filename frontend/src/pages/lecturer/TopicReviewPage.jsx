import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const decisions = [
    { value: "approve", label: "Approve topic", tone: "button-primary" },
    { value: "request_revision", label: "Request revision", tone: "button-secondary" },
    { value: "reject", label: "Reject topic", tone: "button-danger" },
];

const filters = [
    { value: "submitted", label: "Awaiting review" },
    { value: "approved", label: "Approved" },
    { value: "revision_requested", label: "Revision requested" },
    { value: "rejected", label: "Rejected" },
    { value: "all", label: "All topics" },
];

export default function TopicReviewPage() {
    const [topics, setTopics] = useState([]);
    const [activeFilter, setActiveFilter] = useState("submitted");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [selected, setSelected] = useState(null);
    const [decision, setDecision] = useState("approve");
    const [feedback, setFeedback] = useState("");
    const [similarityReport, setSimilarityReport] = useState(null);
    const [similarityLoading, setSimilarityLoading] = useState(false);
    const [similarityRunning, setSimilarityRunning] = useState(false);
    const [similarityError, setSimilarityError] = useState("");

    const loadTopics = useCallback(async () => {
        setLoading(true);
        try {
            setTopics(getList(await apiRequest(`${endpoints.topics}supervised/`)));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadTopics(); }, [loadTopics]);

    useEffect(() => {
        if (!selected?.id || !selected.can_view_similarity) {
            setSimilarityReport(null);
            setSimilarityError("");
            setSimilarityLoading(false);
            return undefined;
        }

        let active = true;
        setSimilarityReport(null);
        setSimilarityError("");
        setSimilarityLoading(true);
        apiRequest(`${endpoints.topics}${selected.id}/similarity-report/`)
            .then((report) => {
                if (active) {
                    setSimilarityReport(report);
                }
            })
            .catch((requestError) => {
                if (active) {
                    setSimilarityError(requestError.message);
                }
            })
            .finally(() => {
                if (active) {
                    setSimilarityLoading(false);
                }
            });

        return () => { active = false; };
    }, [selected?.id, selected?.can_view_similarity]);

    const visibleTopics = useMemo(() => {
        if (activeFilter === "all") {
            return topics;
        }
        return topics.filter((topic) => topic.status === activeFilter);
    }, [activeFilter, topics]);

    const counts = useMemo(() => ({
        submitted: topics.filter((topic) => topic.status === "submitted").length,
        approved: topics.filter((topic) => topic.status === "approved").length,
        revision_requested: topics.filter((topic) => topic.status === "revision_requested").length,
        rejected: topics.filter((topic) => topic.status === "rejected").length,
        all: topics.length,
    }), [topics]);

    function openTopic(topic) {
        setSelected(topic);
        setDecision("approve");
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
            if (decision === "approve") {
                setActiveFilter("approved");
            } else if (decision === "request_revision") {
                setActiveFilter("revision_requested");
            } else {
                setActiveFilter("rejected");
            }
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    const canReview = selected?.can_review === true;

    async function runSimilarityCheck() {
        if (!selected?.id) {
            return;
        }
        setSimilarityRunning(true);
        setSimilarityError("");
        try {
            const report = await apiRequest(`${endpoints.topics}${selected.id}/run-similarity/`, {
                method: "POST",
                timeout: 120000,
            });
            setSimilarityReport(report);
        } catch (requestError) {
            setSimilarityError(requestError.message);
        } finally {
            setSimilarityRunning(false);
        }
    }

    return (
        <>
            <PageHeader
                eyebrow="SUPERVISION"
                title="Project topics"
                description="Review proposals from your assigned students and keep track of your decisions."
                actions={<button className="button button-secondary" onClick={loadTopics} disabled={loading}>Refresh</button>}
            />
            {error && !selected && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <section className="surface-card dashboard-table-card topic-queue-card">
                <div className="surface-card-heading">
                    <div>
                        <span className="panel-eyebrow">SUPERVISION RECORDS</span>
                        <h2>{filters.find((filter) => filter.value === activeFilter)?.label} <span className="heading-count">{counts[activeFilter]}</span></h2>
                    </div>
                </div>
                <div className="topic-filter-tabs" role="tablist" aria-label="Filter project topics">
                    {filters.map((filter) => (
                        <button
                            key={filter.value}
                            type="button"
                            role="tab"
                            aria-selected={activeFilter === filter.value}
                            className={`topic-filter-tab${activeFilter === filter.value ? " topic-filter-tab--active" : ""}`}
                            onClick={() => setActiveFilter(filter.value)}
                        >
                            {filter.label}
                            <span>{counts[filter.value]}</span>
                        </button>
                    ))}
                </div>
                {loading ? <LoadingState /> : visibleTopics.length ? (
                    <div className="topic-queue-list">
                        {visibleTopics.map((topic) => (
                            <article className="topic-queue-item" key={topic.id}>
                                <div className="topic-queue-main">
                                    <div className="topic-queue-student"><strong>{topic.student_name}</strong><span>{topic.matric_number} · {topic.session_name}</span></div>
                                    <StatusBadge value={topic.status} />
                                </div>
                                <h3>{topic.title}</h3>
                                <p>{topic.abstract}</p>
                                <div className="topic-keywords">{(topic.keywords || []).map((keyword) => <span key={keyword}>{keyword}</span>)}</div>
                                <div className="topic-queue-actions">
                                    <button className="button button-secondary" onClick={() => openTopic(topic)}>{topic.status === "submitted" ? "Review proposal" : "View proposal"}</button>
                                    <span>{topic.status === "submitted" ? "Submitted" : "Reviewed"} {new Date(topic.status === "submitted" ? topic.submitted_at : topic.reviewed_at || topic.submitted_at).toLocaleDateString()}</span>
                                </div>
                            </article>
                        ))}
                    </div>
                ) : (
                    <EmptyState
                        title={activeFilter === "approved" ? "No approved topics yet" : "No topics in this section"}
                        description={activeFilter === "submitted" ? "New proposals from your assigned students will appear here." : "Topics matching this status will appear here."}
                    />
                )}
            </section>
            {selected && (
                <Modal
                    title={canReview ? "Review project proposal" : "Project proposal"}
                    description={`${selected.student_name} · ${selected.matric_number}`}
                    onClose={() => setSelected(null)}
                    size="wide"
                >
                    <div className="topic-review-detail">
                        <div className="topic-queue-main"><h2>{selected.title}</h2><StatusBadge value={selected.status} /></div>
                        <div className="topic-content-block"><h3>Abstract</h3><p>{selected.abstract}</p></div>
                        <div className="topic-content-block"><h3>Problem statement</h3><p>{selected.problem_statement}</p></div>
                        <div className="topic-content-block"><h3>Research objectives</h3><p>{selected.research_objectives}</p></div>
                        <div className="topic-keywords">{(selected.keywords || []).map((keyword) => <span key={keyword}>{keyword}</span>)}</div>
                        {selected.revisions?.length > 0 && (
                            <div className="topic-revision-list"><h3>Submission history</h3>{selected.revisions.map((revision) => <div key={revision.id}><strong>Revision {revision.revision_number}</strong><span>{new Date(revision.submitted_at).toLocaleDateString()}</span></div>)}</div>
                        )}
                        {selected.can_view_similarity && (
                            <section className="topic-similarity-panel" aria-live="polite">
                                <div className="topic-similarity-heading">
                                    <div>
                                        <h3>Potentially related previous projects</h3>
                                        <p>Use these findings as guidance during your academic review. Similarity scores do not establish plagiarism or make an approval decision.</p>
                                    </div>
                                </div>
                                {similarityLoading ? (
                                    <p className="topic-similarity-message">Checking related project topics…</p>
                                ) : similarityError ? (
                                    <div className="topic-similarity-message">
                                        <p>{similarityError}</p>
                                        <button type="button" className="button button-secondary" onClick={runSimilarityCheck} disabled={similarityRunning}>
                                            {similarityRunning ? "Checking…" : "Try again"}
                                        </button>
                                    </div>
                                ) : similarityReport?.status === "completed" ? (
                                    similarityReport.matches?.length ? (
                                        <div className="topic-similarity-list">
                                            {similarityReport.matches.map((match) => (
                                                <article className="topic-similarity-item" key={match.id}>
                                                    <div className="topic-similarity-item-heading">
                                                        <div>
                                                            <h4>{match.previous_title}</h4>
                                                            <p>{match.academic_session} · {match.project_status_label}</p>
                                                        </div>
                                                        <strong>{match.similarity_percent}%</strong>
                                                    </div>
                                                    {match.matched_sections?.length > 0 && (
                                                        <div className="topic-similarity-sections">
                                                            {match.matched_sections.map((section) => (
                                                                <div className="topic-similarity-section" key={section.section}>
                                                                    <div><strong>{section.section}</strong><span>{section.similarity_percent}%</span></div>
                                                                    <p>{section.excerpt}</p>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </article>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="topic-similarity-message">No closely related previous project topics were identified.</p>
                                    )
                                ) : (
                                    <div className="topic-similarity-message">
                                        <p>A similarity review is not available for this proposal yet.</p>
                                        <button type="button" className="button button-secondary" onClick={runSimilarityCheck} disabled={similarityRunning}>
                                            {similarityRunning ? "Checking…" : "Run similarity check"}
                                        </button>
                                    </div>
                                )}
                            </section>
                        )}
                        {selected.reviews?.length > 0 && (
                            <div className="topic-review-history">
                                <h3>Review history</h3>
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
                    {canReview ? (
                        <form className="modal-form topic-review-form" onSubmit={submitReview}>
                            {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
                            <Field label="Decision"><select value={decision} onChange={(event) => setDecision(event.target.value)}>{decisions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></Field>
                            <Field label={decision === "approve" ? "Feedback (optional)" : "Feedback to student"} hint={decision === "approve" ? "You may add a note for the student." : "Explain the changes required or the reason for rejection."}><textarea rows="4" required={decision !== "approve"} value={feedback} onChange={(event) => setFeedback(event.target.value)} /></Field>
                            <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setSelected(null)}>Cancel</button><button className={`button ${decisions.find((item) => item.value === decision)?.tone || "button-primary"}`} disabled={saving}>{saving ? "Submitting…" : "Submit decision"}</button></div>
                        </form>
                    ) : (
                        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setSelected(null)}>Close</button></div>
                    )}
                </Modal>
            )}
        </>
    );
}

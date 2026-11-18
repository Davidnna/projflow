import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const emptyForm = {
    title: "",
    description: "",
    expected_achievement: "",
    sequence: "",
    due_date: "",
    is_active: true,
};

export default function MilestonesPage() {
    const [sessions, setSessions] = useState([]);
    const [milestones, setMilestones] = useState([]);
    const [sessionId, setSessionId] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const [form, setForm] = useState(emptyForm);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [sessionData, milestoneData] = await Promise.all([
                apiRequest(endpoints.sessions),
                apiRequest(endpoints.milestones),
            ]);
            const sessionList = getList(sessionData);
            setSessions(sessionList);
            setMilestones(getList(milestoneData));
            setSessionId((current) => current || sessionList.find((item) => item.status === "active")?.id || sessionList[0]?.id || "");
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const selectedSession = sessions.find((item) => item.id === sessionId) || null;
    const hasSubmittedReports = Boolean(editing?.report_count);
    const visibleMilestones = useMemo(
        () => milestones.filter((item) => item.session === sessionId).sort((a, b) => a.sequence - b.sequence),
        [milestones, sessionId],
    );

    function openCreate() {
        setEditing(null);
        const nextSequence = visibleMilestones.reduce((maximum, item) => Math.max(maximum, item.sequence), 0) + 1;
        setForm({ ...emptyForm, sequence: String(nextSequence) });
        setModalOpen(true);
        setError("");
    }

    function openEdit(milestone) {
        setEditing(milestone);
        setForm({
            title: milestone.title || "",
            description: milestone.description || "",
            expected_achievement: milestone.expected_achievement || "",
            sequence: String(milestone.sequence),
            due_date: milestone.due_date || "",
            is_active: milestone.is_active,
        });
        setModalOpen(true);
        setError("");
    }

    async function saveMilestone(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        setSuccess("");
        const payload = {
            session: sessionId,
            title: form.title.trim(),
            description: form.description.trim(),
            expected_achievement: form.expected_achievement.trim(),
            sequence: Number(form.sequence),
            due_date: form.due_date || null,
            is_active: form.is_active,
        };
        try {
            if (editing) {
                await apiRequest(`${endpoints.milestones}${editing.id}/`, { method: "PATCH", body: payload });
                setSuccess("Milestone updated successfully.");
            } else {
                await apiRequest(endpoints.milestones, { method: "POST", body: payload });
                setSuccess("Milestone added successfully.");
            }
            setModalOpen(false);
            setEditing(null);
            await loadData();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    async function toggleMilestone(milestone) {
        const action = milestone.is_active ? "deactivate" : "activate";
        if (!window.confirm(`Are you sure you want to ${action} this milestone?`)) {
            return;
        }
        setError("");
        setSuccess("");
        try {
            await apiRequest(`${endpoints.milestones}${milestone.id}/`, {
                method: "PATCH",
                body: { is_active: !milestone.is_active },
            });
            setSuccess(`Milestone ${milestone.is_active ? "deactivated" : "activated"} successfully.`);
            await loadData();
        } catch (requestError) {
            setError(requestError.message);
        }
    }

    return (
        <>
            <PageHeader
                eyebrow="PROJECT ADMINISTRATION"
                title="Project milestones"
                description="Set the common project stages students will follow in each academic session."
                actions={<button className="button button-primary" onClick={openCreate} disabled={!sessionId || selectedSession?.status === "closed"}>＋ Add milestone</button>}
            />
            {error && !modalOpen && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <section className="surface-card milestone-controls">
                <Field label="Academic session">
                    <select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
                        <option value="">Select an academic session</option>
                        {sessions.map((session) => <option key={session.id} value={session.id}>{session.name} · {session.status === "active" ? "Active" : session.status === "closed" ? "Closed" : "Not active"}</option>)}
                    </select>
                </Field>
                {selectedSession && <div className="milestone-session-status"><StatusBadge value={selectedSession.status} /><span>{selectedSession.name}</span></div>}
            </section>
            <div className="info-callout"><span>i</span><p>All students in the selected session follow the same milestone structure. Only the Project Coordinator can define or change these milestones. Due dates are optional and can be set when the department is ready.</p></div>
            {loading ? <LoadingState /> : !sessions.length ? (
                <EmptyState title="No academic sessions available" description="Create an academic session before defining its project milestones." />
            ) : !sessionId ? (
                <EmptyState title="Select an academic session" description="Choose the session for which you want to manage milestones." />
            ) : visibleMilestones.length ? (
                <section className="surface-card milestone-list-card">
                    <div className="surface-card-heading"><div><span className="panel-eyebrow">MILESTONE STRUCTURE</span><h2>{visibleMilestones.length} milestone{visibleMilestones.length === 1 ? "" : "s"}</h2></div></div>
                    <div className="milestone-list">
                        {visibleMilestones.map((milestone) => (
                            <article className={`milestone-item${!milestone.is_active ? " milestone-item--inactive" : ""}`} key={milestone.id}>
                                <div className="milestone-number">{milestone.sequence}</div>
                                <div className="milestone-copy">
                                    <div className="milestone-item-heading"><h3>{milestone.title}</h3><StatusBadge value={milestone.is_active ? "active" : "inactive"} /></div>
                                    {milestone.description && <p>{milestone.description}</p>}
                                    {milestone.expected_achievement && <small><strong>Expected achievement:</strong> {milestone.expected_achievement}</small>}
                                    <div className="milestone-meta"><span>{milestone.due_date ? `Due ${new Date(`${milestone.due_date}T00:00:00`).toLocaleDateString()}` : "No due date set"}</span></div>
                                </div>
                                <div className="milestone-actions">
                                    <button className="table-action table-action--primary" onClick={() => openEdit(milestone)} disabled={selectedSession?.status === "closed"}>Edit</button>
                                    <button className="table-action" onClick={() => toggleMilestone(milestone)} disabled={selectedSession?.status === "closed"}>{milestone.is_active ? "Deactivate" : "Activate"}</button>
                                </div>
                            </article>
                        ))}
                    </div>
                </section>
            ) : (
                <EmptyState title="No milestones defined" description="Add the first milestone for this academic session. All students in the session will use the same structure." action={<button className="button button-primary" onClick={openCreate}>Add first milestone</button>} />
            )}
            {modalOpen && (
                <Modal title={editing ? "Edit milestone" : "Add project milestone"} description={`${selectedSession?.name || "Selected session"} · Common to all students`} onClose={() => setModalOpen(false)}>
                    <form className="modal-form" onSubmit={saveMilestone}>
                        {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
                        {hasSubmittedReports && <Alert type="info">This milestone already has student reports. Its title, description, expected achievement and order are now fixed; you can still change its due date or availability.</Alert>}
                        <Field label="Milestone title"><input required maxLength="200" disabled={hasSubmittedReports} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="e.g. Literature review" /></Field>
                        <Field label="Description"><textarea rows="3" disabled={hasSubmittedReports} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Describe this project stage…" /></Field>
                        <Field label="Expected achievement"><textarea rows="3" disabled={hasSubmittedReports} value={form.expected_achievement} onChange={(event) => setForm({ ...form, expected_achievement: event.target.value })} placeholder="What should students have completed?" /></Field>
                        <div className="form-grid-two">
                            <Field label="Order"><input required type="number" min="1" step="1" disabled={hasSubmittedReports} value={form.sequence} onChange={(event) => setForm({ ...form, sequence: event.target.value })} /></Field>
                            <Field label="Due date (optional)"><input type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} /></Field>
                        </div>
                        {editing && <label className="checkbox-field"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /> Available to students</label>}
                        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setModalOpen(false)}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : "Add milestone"}</button></div>
                    </form>
                </Modal>
            )}
        </>
    );
}

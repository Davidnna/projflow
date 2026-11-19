import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const emptyForm = {
    title: "",
    description: "",
    sequence: "",
    due_date: "",
    is_required: true,
    is_active: true,
};

export default function ReportStructurePage() {
    const [sessions, setSessions] = useState([]);
    const [sections, setSections] = useState([]);
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
            const [sessionData, sectionData] = await Promise.all([
                apiRequest(endpoints.sessions),
                apiRequest(endpoints.reportSections),
            ]);
            const sessionList = getList(sessionData);
            setSessions(sessionList);
            setSections(getList(sectionData));
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
    const visibleSections = useMemo(
        () => sections.filter((item) => item.session === sessionId).sort((a, b) => a.sequence - b.sequence),
        [sections, sessionId],
    );
    const sessionHasSubmissions = visibleSections.some((item) => item.submission_count > 0);

    function openCreate() {
        setEditing(null);
        const nextSequence = visibleSections.reduce((maximum, item) => Math.max(maximum, item.sequence), 0) + 1;
        setForm({ ...emptyForm, sequence: String(nextSequence) });
        setModalOpen(true);
        setError("");
    }

    function openEdit(section) {
        setEditing(section);
        setForm({
            title: section.title || "",
            description: section.description || "",
            sequence: String(section.sequence),
            due_date: section.due_date || "",
            is_required: section.is_required,
            is_active: section.is_active,
        });
        setModalOpen(true);
        setError("");
    }

    async function createStandardStructure() {
        if (!window.confirm(`Create the suggested eight-section project report structure for ${selectedSession?.name}? You can adjust it before students begin submitting documents.`)) {
            return;
        }
        setSaving(true);
        setError("");
        setSuccess("");
        try {
            await apiRequest(`${endpoints.reportSections}create-standard-structure/`, {
                method: "POST",
                body: { session: sessionId },
            });
            setSuccess("The standard project report structure has been created.");
            await loadData();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    async function saveSection(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        setSuccess("");
        const payload = editing && sessionHasSubmissions
            ? { due_date: form.due_date || null }
            : {
                session: sessionId,
                title: form.title.trim(),
                description: form.description.trim(),
                sequence: Number(form.sequence),
                due_date: form.due_date || null,
                is_required: form.is_required,
                is_active: form.is_active,
            };
        try {
            if (editing) {
                await apiRequest(`${endpoints.reportSections}${editing.id}/`, { method: "PATCH", body: payload });
                setSuccess("Report section updated successfully.");
            } else {
                await apiRequest(endpoints.reportSections, { method: "POST", body: payload });
                setSuccess("Report section added successfully.");
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

    return (
        <>
            <PageHeader
                eyebrow="PROJECT ADMINISTRATION"
                title="Project report structure"
                description="Define the report sections every student in an academic session must submit for supervisor review."
                actions={<button className="button button-primary" onClick={openCreate} disabled={!sessionId || selectedSession?.status === "closed"}>＋ Add section</button>}
            />
            {error && !modalOpen && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <section className="surface-card report-structure-controls">
                <Field label="Academic session">
                    <select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
                        <option value="">Select an academic session</option>
                        {sessions.map((session) => <option key={session.id} value={session.id}>{session.name} · {session.status === "active" ? "Active" : session.status === "closed" ? "Closed" : "Not active"}</option>)}
                    </select>
                </Field>
                {selectedSession && <div className="report-structure-session-status"><StatusBadge value={selectedSession.status} /><span>{selectedSession.name}</span></div>}
            </section>
            <div className="info-callout"><span>i</span><p>Students submit each section as a separate PDF or DOCX document. The next required section becomes available after the previous section is approved by the assigned supervisor. Finalise the structure before submissions begin.</p></div>
            {loading ? <LoadingState /> : !sessions.length ? (
                <EmptyState title="No academic sessions available" description="Create an academic session before setting up its project report structure." />
            ) : !sessionId ? (
                <EmptyState title="Select an academic session" description="Choose the session for which you want to configure the report structure." />
            ) : visibleSections.length ? (
                <section className="surface-card report-structure-list-card">
                    <div className="surface-card-heading">
                        <div><span className="panel-eyebrow">REQUIRED REPORT SEQUENCE</span><h2>{visibleSections.length} report section{visibleSections.length === 1 ? "" : "s"}</h2></div>
                    </div>
                    {sessionHasSubmissions && <Alert type="info">Students have started submitting this report structure. Section names, descriptions and order are now protected to preserve their academic records. Due dates can still be adjusted.</Alert>}
                    <div className="report-structure-list">
                        {visibleSections.map((section) => (
                            <article className={`report-structure-item${!section.is_active ? " report-structure-item--inactive" : ""}`} key={section.id}>
                                <div className="report-structure-number">{section.sequence}</div>
                                <div className="report-structure-copy">
                                    <div className="report-structure-heading"><h3>{section.title}</h3><div><StatusBadge value={section.is_active ? "active" : "inactive"} /><span className={`report-required-label${section.is_required ? "" : " report-required-label--optional"}`}>{section.is_required ? "Required" : "Optional"}</span></div></div>
                                    {section.description && <p>{section.description}</p>}
                                    <div className="report-structure-meta"><span>{section.submission_count || 0} student submissions</span><span>{section.due_date ? `Due ${new Date(`${section.due_date}T00:00:00`).toLocaleDateString()}` : "No due date"}</span></div>
                                </div>
                                <div className="report-structure-actions"><button className="table-action table-action--primary" onClick={() => openEdit(section)} disabled={selectedSession?.status === "closed"}>Edit</button></div>
                            </article>
                        ))}
                    </div>
                </section>
            ) : (
                <EmptyState
                    title="No report structure defined"
                    description="Create the department's report sections manually or start with the suggested structure from preliminary pages through appendices."
                    action={<div className="report-structure-empty-actions"><button className="button button-primary" onClick={createStandardStructure} disabled={saving || selectedSession?.status === "closed"}>{saving ? "Creating…" : "Create standard structure"}</button><button className="button button-secondary" onClick={openCreate} disabled={selectedSession?.status === "closed"}>Add first section</button></div>}
                />
            )}
            {modalOpen && (
                <Modal title={editing ? "Edit report section" : "Add report section"} description={`${selectedSession?.name || "Selected session"} · Shared by all students`} onClose={() => setModalOpen(false)}>
                    <form className="modal-form" onSubmit={saveSection}>
                        {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
                        {editing && sessionHasSubmissions && <Alert type="info">The report structure is already in use. Only the due date can be changed.</Alert>}
                        <Field label="Section title"><input required maxLength="200" disabled={editing && sessionHasSubmissions} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="e.g. Chapter One — Introduction" /></Field>
                        <Field label="Description"><textarea rows="3" disabled={editing && sessionHasSubmissions} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Describe the expected contents of this section…" /></Field>
                        <div className="form-grid-two">
                            <Field label="Order"><input required type="number" min="1" step="1" disabled={editing && sessionHasSubmissions} value={form.sequence} onChange={(event) => setForm({ ...form, sequence: event.target.value })} /></Field>
                            <Field label="Due date (optional)"><input type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} /></Field>
                        </div>
                        <label className="checkbox-field"><input type="checkbox" disabled={editing && sessionHasSubmissions} checked={form.is_required} onChange={(event) => setForm({ ...form, is_required: event.target.checked })} /> Required section</label>
                        {editing && !sessionHasSubmissions && <label className="checkbox-field"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /> Available to students</label>}
                        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setModalOpen(false)}>Cancel</button><button className="button button-primary" disabled={saving || selectedSession?.status === "closed"}>{saving ? "Saving…" : editing ? "Save changes" : "Add section"}</button></div>
                    </form>
                </Modal>
            )}
        </>
    );
}

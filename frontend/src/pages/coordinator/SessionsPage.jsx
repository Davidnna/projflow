import { useCallback, useEffect, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const emptyForm = { name: "" };

export default function SessionsPage() {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [form, setForm] = useState(emptyForm);
    const [saving, setSaving] = useState(false);

    const loadSessions = useCallback(async () => {
        setLoading(true);
        try {
            setSessions(getList(await apiRequest(endpoints.sessions)));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadSessions(); }, [loadSessions]);

    async function createSession(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        try {
            await apiRequest(endpoints.sessions, { method: "POST", body: form });
            setSuccess("Academic session created. Activate it when the department is ready to begin the project cycle.");
            setForm(emptyForm);
            setModalOpen(false);
            await loadSessions();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    async function changeSessionStatus(session, action) {
        const label = action === "activate" ? "activate" : "close";
        if (!window.confirm(`Are you sure you want to ${label} ${session.name}?`)) {
            return;
        }
        setError("");
        setSuccess("");
        try {
            await apiRequest(`${endpoints.sessions}${session.id}/${action}/`, { method: "POST", body: {} });
            setSuccess(`${session.name} has been ${action === "activate" ? "activated" : "closed"}.`);
            await loadSessions();
        } catch (requestError) {
            setError(requestError.message);
        }
    }

    return (
        <>
            <PageHeader eyebrow="ACADEMIC ADMINISTRATION" title="Academic sessions" description="Create and manage departmental project cycles. Only one session can be active at a time." actions={<button className="button button-primary" onClick={() => setModalOpen(true)}>＋ Create session</button>} />
            {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <div className="info-callout"><span>i</span><p>Session activation and closure are controlled manually. Previous sessions remain available for historical records. Close the active session before activating another session.</p></div>
            {loading ? <LoadingState /> : sessions.length ? (
                <div className="surface-card dashboard-table-card">
                    <div className="surface-card-heading"><div><span className="panel-eyebrow">SESSION REGISTER</span><h2>{sessions.length} academic session{sessions.length === 1 ? "" : "s"}</h2></div></div>
                    <div className="table-scroll"><table className="data-table"><thead><tr><th>Session</th><th>Status</th><th>Actions</th></tr></thead><tbody>
                        {sessions.map((session) => (
                            <tr key={session.id}>
                                <td><strong>{session.name}</strong><small>Created {new Date(session.created_at).toLocaleDateString()}</small></td>
                                <td><StatusBadge value={session.status} /></td>
                                <td><div className="table-actions">
                                    {session.status === "planned" && <button className="table-action table-action--primary" onClick={() => changeSessionStatus(session, "activate")}>Activate</button>}
                                    {session.status === "active" && <button className="table-action table-action--danger" onClick={() => changeSessionStatus(session, "close")}>Close session</button>}
                                    {session.status === "closed" && <span className="table-muted">Archived</span>}
                                </div></td>
                            </tr>
                        ))}
                    </tbody></table></div>
                </div>
            ) : <EmptyState title="No academic sessions yet" description="Create the first academic session to establish the departmental project cycle." action={<button className="button button-primary" onClick={() => setModalOpen(true)}>Create first session</button>} />}

            {modalOpen && <Modal title="Create academic session" description="Create a project cycle. You can activate or close it manually when the department is ready." onClose={() => setModalOpen(false)}>
                <form className="modal-form" onSubmit={createSession}>
                    <Field label="Academic session name"><input required maxLength="100" placeholder="e.g. 2026/2027" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field>
                    <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setModalOpen(false)}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Creating…" : "Create session"}</button></div>
                </form>
            </Modal>}
        </>
    );
}

import { useCallback, useEffect, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge, getInitials } from "../../components/dashboard/WorkspaceUI.jsx";

const emptyLecturer = { email: "", first_name: "", last_name: "", password: "", staff_number: "", designation: "", phone: "", office: "", is_active: true };

export default function LecturersPage() {
    const [lecturers, setLecturers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [modalOpen, setModalOpen] = useState(false);
    const [form, setForm] = useState(emptyLecturer);
    const [saving, setSaving] = useState(false);

    const loadLecturers = useCallback(async () => {
        setLoading(true);
        try {
            setLecturers(getList(await apiRequest(endpoints.lecturers)));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadLecturers(); }, [loadLecturers]);

    async function createLecturer(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        try {
            await apiRequest(endpoints.lecturers, { method: "POST", body: form });
            setSuccess("Lecturer account created successfully.");
            setForm(emptyLecturer);
            setModalOpen(false);
            await loadLecturers();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    return (
        <>
            <PageHeader eyebrow="STAFF ADMINISTRATION" title="Lecturer directory" description="Create lecturer accounts and maintain the staff profiles used for supervisor allocation." actions={<button className="button button-primary" onClick={() => setModalOpen(true)}>＋ Add lecturer</button>} />
            {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <div className="info-callout"><span>i</span><p>Share the lecturer's sign-in details through an approved, secure channel.</p></div>
            {loading ? <LoadingState /> : lecturers.length ? <div className="lecturer-grid">{lecturers.map((lecturer) => <article className="lecturer-card" key={lecturer.id}>
                <div className="lecturer-card-top"><div className="lecturer-avatar">{getInitials(`${lecturer.first_name} ${lecturer.last_name}`)}</div><StatusBadge value={lecturer.is_active ? "active" : "inactive"}>{lecturer.is_active ? "Active" : "Inactive"}</StatusBadge></div>
                <h2>{lecturer.first_name} {lecturer.last_name}</h2><p>{lecturer.designation || "Lecturer"}</p>
                <div className="lecturer-meta"><span>✉ {lecturer.email}</span>{lecturer.staff_number && <span>№ {lecturer.staff_number}</span>}{lecturer.office && <span>⌖ {lecturer.office}</span>}</div>
            </article>)}</div> : <EmptyState title="No lecturer accounts yet" description="Create lecturer accounts before assigning supervisors to students." action={<button className="button button-primary" onClick={() => setModalOpen(true)}>Add first lecturer</button>} />}
            {modalOpen && <Modal title="Create lecturer account" description="Create a staff account and lecturer profile." onClose={() => setModalOpen(false)} size="wide">
                <form className="modal-form" onSubmit={createLecturer}>
                    <div className="form-grid-two"><Field label="First name"><input required value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></Field><Field label="Last name"><input required value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></Field></div>
                    <Field label="Email address"><input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></Field>
                    <Field label="Initial password" hint="Use a strong password and share it securely with the lecturer."><input type="password" required minLength="12" autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></Field>
                    <div className="form-grid-two"><Field label="Staff number"><input value={form.staff_number} onChange={(event) => setForm({ ...form, staff_number: event.target.value })} /></Field><Field label="Designation"><input placeholder="e.g. Lecturer I" value={form.designation} onChange={(event) => setForm({ ...form, designation: event.target.value })} /></Field></div>
                    <div className="form-grid-two"><Field label="Phone number"><input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></Field><Field label="Office"><input value={form.office} onChange={(event) => setForm({ ...form, office: event.target.value })} /></Field></div>
                    <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setModalOpen(false)}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Creating…" : "Create lecturer"}</button></div>
                </form>
            </Modal>}
        </>
    );
}

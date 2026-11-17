import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

const blankStudent = { session: "", matric_number: "", first_name: "", last_name: "", other_names: "", email: "", phone: "", is_eligible: true };

export default function StudentsPage() {
    const [sessions, setSessions] = useState([]);
    const [roster, setRoster] = useState([]);
    const [selectedSession, setSelectedSession] = useState("");
    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [studentModal, setStudentModal] = useState(false);
    const [editingRecord, setEditingRecord] = useState(null);
    const [studentForm, setStudentForm] = useState(blankStudent);
    const [saving, setSaving] = useState(false);
    const [importFile, setImportFile] = useState(null);
    const [importBatch, setImportBatch] = useState(null);
    const [importing, setImporting] = useState(false);
    const fileRef = useRef(null);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [sessionData, rosterData] = await Promise.all([
                apiRequest(endpoints.sessions),
                apiRequest(endpoints.roster),
            ]);
            const nextSessions = getList(sessionData);
            setSessions(nextSessions);
            setRoster(getList(rosterData));
            const active = nextSessions.find((item) => item.status === "active");
            setSelectedSession((current) => current || active?.id || nextSessions[0]?.id || "");
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const visibleRoster = useMemo(() => {
        const query = search.trim().toLowerCase();
        return roster.filter((record) => (!selectedSession || record.session === selectedSession)
            && (!query || `${record.first_name} ${record.last_name} ${record.other_names} ${record.matric_number} ${record.email}`.toLowerCase().includes(query)));
    }, [roster, selectedSession, search]);

    async function saveStudent(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        try {
            if (editingRecord) {
                await apiRequest(`${endpoints.roster}${editingRecord.id}/`, { method: "PATCH", body: studentForm });
                setSuccess("Student roster record updated.");
            } else {
                await apiRequest(endpoints.roster, { method: "POST", body: studentForm });
                setSuccess("Student record added to the departmental roster.");
            }
            setStudentModal(false);
            setEditingRecord(null);
            setStudentForm({ ...blankStudent, session: selectedSession });
            await loadData();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    function openEdit(record) {
        setEditingRecord(record);
        setStudentForm({
            session: record.session,
            matric_number: record.matric_number,
            first_name: record.first_name,
            last_name: record.last_name,
            other_names: record.other_names || "",
            email: record.email || "",
            phone: record.phone || "",
            is_eligible: record.is_eligible,
        });
        setStudentModal(true);
    }

    async function previewImport(event) {
        event.preventDefault();
        if (!importFile || !selectedSession) {
            setError("Select an academic session and a CSV or XLSX file before previewing the import.");
            return;
        }
        setImporting(true);
        setError("");
        setSuccess("");
        const body = new FormData();
        body.append("session", selectedSession);
        body.append("file", importFile);
        try {
            const batch = await apiRequest(endpoints.rosterImportPreview, { method: "POST", body, formData: true });
            setImportBatch(batch);
            setSuccess("Your file is ready. Review the student details before importing.");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setImporting(false);
        }
    }

    async function commitImport() {
        if (!importBatch) {
            return;
        }
        setImporting(true);
        setError("");
        try {
            const result = await apiRequest(`${endpoints.rosterImports}${importBatch.id}/commit/`, { method: "POST", body: {} });
            setSuccess(`${result.imported_rows} student records added successfully.`);
            setImportBatch(null);
            setImportFile(null);
            if (fileRef.current) {
                fileRef.current.value = "";
            }
            await loadData();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setImporting(false);
        }
    }

    return (
        <>
            <PageHeader eyebrow="STUDENT ADMINISTRATION" title="Student records" description="Maintain your department's student register." actions={<button className="button button-primary" onClick={() => { setStudentForm({ ...blankStudent, session: selectedSession }); setStudentModal(true); }}>＋ Add student</button>} />
            {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <div className="surface-card import-card">
                <div className="import-card-copy"><span className="panel-eyebrow">BULK IMPORT</span><h2>Upload a student register</h2><p>Upload a departmental register and review the student details before adding them to the selected session.</p><div className="import-format-note"><span>CSV</span><span>XLSX</span></div></div>
                <form className="import-form" onSubmit={previewImport}>
                    <Field label="Academic session"><select required value={selectedSession} onChange={(event) => { setSelectedSession(event.target.value); setImportBatch(null); }}><option value="">Select a session</option>{sessions.map((session) => <option key={session.id} value={session.id}>{session.name} · {session.status}</option>)}</select></Field>
                    <Field label="Student register file"><input ref={fileRef} type="file" accept=".csv,.xlsx" onChange={(event) => { setImportFile(event.target.files?.[0] || null); setImportBatch(null); }} required /></Field>
                    <button className="button button-primary" disabled={importing || !selectedSession || !importFile}>{importing ? "Preparing…" : "Review file"}</button>
                </form>
            </div>
            {importBatch && <section className="surface-card import-preview-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">REVIEW STUDENT RECORDS</span><h2>{importBatch.original_file_name}</h2></div><StatusBadge value={importBatch.status} /></div>
                <div className="import-summary-grid"><div><strong>{importBatch.total_rows}</strong><span>Total students</span></div><div><strong>{importBatch.valid_rows}</strong><span>Ready to add</span></div><div><strong>{importBatch.invalid_rows}</strong><span>Need attention</span></div><div><strong>{importBatch.duplicate_rows}</strong><span>Already listed</span></div></div>
                <div className="table-scroll"><table className="data-table"><thead><tr><th>Row</th><th>Matriculation no.</th><th>Student</th><th>Status</th><th>Details</th></tr></thead><tbody>{(importBatch.rows || []).slice(0, 8).map((row) => <tr key={row.id}><td>{row.row_number}</td><td>{row.matric_number || "—"}</td><td>{`${row.first_name} ${row.last_name}`.trim() || "—"}</td><td><StatusBadge value={row.status} /></td><td>{row.errors?.join(" ") || "—"}</td></tr>)}</tbody></table></div>
                {importBatch.rows?.length > 8 && <p className="table-footnote">Showing the first 8 of {importBatch.rows.length} records.</p>}
                <div className="preview-actions"><span>Only valid, new student records will be added.</span><button className="button button-primary" onClick={commitImport} disabled={importing || !importBatch.valid_rows}>{importing ? "Adding students…" : `Add ${importBatch.valid_rows} students`}</button></div>
            </section>}
            <section className="surface-card dashboard-table-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">DEPARTMENTAL REGISTER</span><h2>Student roster <span className="heading-count">{visibleRoster.length}</span></h2></div><div className="table-toolbar"><select aria-label="Filter by academic session" value={selectedSession} onChange={(event) => setSelectedSession(event.target.value)}><option value="">All sessions</option>{sessions.map((session) => <option key={session.id} value={session.id}>{session.name}</option>)}</select><input aria-label="Search student records" placeholder="Search students…" value={search} onChange={(event) => setSearch(event.target.value)} /></div></div>
                {loading ? <LoadingState /> : visibleRoster.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Student</th><th>Matriculation no.</th><th>Session</th><th>Contact</th><th>Eligibility</th><th>Action</th></tr></thead><tbody>{visibleRoster.map((record) => <tr key={record.id}><td><strong>{record.last_name}, {record.first_name}</strong><small>{record.other_names}</small></td><td>{record.matric_number}</td><td>{record.session_name}</td><td>{record.email || record.phone || "—"}</td><td><StatusBadge value={record.is_eligible ? "active" : "inactive"}>{record.is_eligible ? "Eligible" : "Not eligible"}</StatusBadge></td><td><button className="table-action table-action--primary" onClick={() => openEdit(record)}>Edit</button></td></tr>)}</tbody></table></div> : <EmptyState title="No student records found" description="Add a student manually or import a departmental register to begin." />}
            </section>

            {studentModal && <Modal title={editingRecord ? "Edit student record" : "Add student record"} description="Enter the student's details for the selected academic session." onClose={() => { setStudentModal(false); setEditingRecord(null); }} size="wide">
                <form className="modal-form" onSubmit={saveStudent}>
                    <Field label="Academic session"><select required value={studentForm.session} onChange={(event) => setStudentForm({ ...studentForm, session: event.target.value })}><option value="">Select a session</option>{sessions.map((session) => <option key={session.id} value={session.id}>{session.name}</option>)}</select></Field>
                    <div className="form-grid-two"><Field label="First name"><input required value={studentForm.first_name} onChange={(event) => setStudentForm({ ...studentForm, first_name: event.target.value })} /></Field><Field label="Last name"><input required value={studentForm.last_name} onChange={(event) => setStudentForm({ ...studentForm, last_name: event.target.value })} /></Field></div>
                    <div className="form-grid-two"><Field label="Other names"><input value={studentForm.other_names} onChange={(event) => setStudentForm({ ...studentForm, other_names: event.target.value })} /></Field><Field label="Matriculation number"><input required value={studentForm.matric_number} onChange={(event) => setStudentForm({ ...studentForm, matric_number: event.target.value })} /></Field></div>
                    <div className="form-grid-two"><Field label="Email address"><input type="email" value={studentForm.email} onChange={(event) => setStudentForm({ ...studentForm, email: event.target.value })} /></Field><Field label="Phone number"><input value={studentForm.phone} onChange={(event) => setStudentForm({ ...studentForm, phone: event.target.value })} /></Field></div>
                    <label className="checkbox-field"><input type="checkbox" checked={studentForm.is_eligible} onChange={(event) => setStudentForm({ ...studentForm, is_eligible: event.target.checked })} /><span>Eligible for final-year project</span></label>
                    <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => { setStudentModal(false); setEditingRecord(null); }}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : editingRecord ? "Save changes" : "Add student record"}</button></div>
                </form>
            </Modal>}
        </>
    );
}

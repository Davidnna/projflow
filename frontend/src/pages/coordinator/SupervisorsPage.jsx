import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatusBadge, getInitials } from "../../components/dashboard/WorkspaceUI.jsx";

export default function SupervisorsPage() {
    const [sessions, setSessions] = useState([]);
    const [enrollments, setEnrollments] = useState([]);
    const [assignments, setAssignments] = useState([]);
    const [workloads, setWorkloads] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [studentId, setStudentId] = useState("");
    const [lecturerId, setLecturerId] = useState("");
    const [saving, setSaving] = useState(false);
    const [reassignment, setReassignment] = useState(null);
    const [reassignmentLecturer, setReassignmentLecturer] = useState("");
    const [reason, setReason] = useState("");
    const [sessionFilter, setSessionFilter] = useState("active");

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [sessionData, enrollmentData, assignmentData, workloadData] = await Promise.all([
                apiRequest(endpoints.sessions),
                apiRequest(endpoints.enrollments),
                apiRequest(endpoints.assignments),
                apiRequest(endpoints.lecturerWorkloads),
            ]);
            const nextSessions = getList(sessionData);
            setSessions(nextSessions);
            setEnrollments(getList(enrollmentData));
            setAssignments(getList(assignmentData));
            setWorkloads(getList(workloadData));
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const activeSession = sessions.find((session) => session.status === "active");
    const selectedSession = sessionFilter === "active" ? activeSession?.id : sessionFilter;
    const matchesSession = (sessionId) => sessionFilter === "" || Boolean(selectedSession && sessionId === selectedSession);
    const currentAssignments = useMemo(() => assignments.filter((item) => {
        if (!item.is_current) {
            return false;
        }
        const enrollment = enrollments.find((record) => record.id === item.student_enrollment);
        return enrollment ? matchesSession(enrollment.session) : false;
    }), [assignments, enrollments, selectedSession, sessionFilter]);
    const verifiedEnrollments = enrollments.filter((item) => ["auto_verified", "manually_approved"].includes(item.verification_status) && matchesSession(item.session));
    const unassigned = verifiedEnrollments.filter((enrollment) => !currentAssignments.some((assignment) => assignment.student_enrollment === enrollment.id));

    async function assignSupervisor(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        try {
            await apiRequest(`${endpoints.assignments}assign/`, { method: "POST", body: { student_enrollment: studentId, lecturer: lecturerId } });
            setSuccess("Supervisor assigned successfully.");
            setStudentId("");
            setLecturerId("");
            await loadData();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    async function reassignSupervisor(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        try {
            await apiRequest(`${endpoints.assignments}${reassignment.id}/reassign/`, {
                method: "POST",
                body: { lecturer: reassignmentLecturer, reason },
            });
            setSuccess(`Supervisor reassigned for ${reassignment.student_name}.`);
            setReassignment(null);
            setReason("");
            setReassignmentLecturer("");
            await loadData();
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    return (
        <>
            <PageHeader eyebrow="SUPERVISION ADMINISTRATION" title="Supervisor allocation" description="Assign supervisors and review lecturer workloads." />
            {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <div className="allocation-summary"><div><strong>{unassigned.length}</strong><span>Students awaiting allocation</span></div><div><strong>{currentAssignments.length}</strong><span>Current supervisor assignments</span></div><div><strong>{workloads.length}</strong><span>Available lecturers</span></div></div>
            <section className="surface-card allocation-form-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">NEW ALLOCATION</span><h2>Assign a supervisor</h2></div><span className="panel-icon">⇄</span></div>
                <p className="card-description">Choose a student and a lecturer. Current workloads are shown to help you distribute students fairly.</p>
                <form className="allocation-form" onSubmit={assignSupervisor}>
                    <Field label="Student"><select required value={studentId} onChange={(event) => setStudentId(event.target.value)}><option value="">Select a student</option>{unassigned.map((item) => <option key={item.id} value={item.id}>{item.student_name} · {item.matric_number}</option>)}</select></Field>
                    <Field label="Supervisor"><select required value={lecturerId} onChange={(event) => setLecturerId(event.target.value)}><option value="">Select a lecturer</option>{workloads.map((item) => <option key={item.lecturer_id} value={item.lecturer_id}>{item.name} · {item.active_supervisee_count} current supervisees</option>)}</select></Field>
                    <button className="button button-primary" disabled={saving || !unassigned.length || !workloads.length}>{saving ? "Assigning…" : "Assign supervisor"}</button>
                </form>
                {!activeSession && <Alert type="warning">There is no active academic session. Activate a session before assigning supervisors.</Alert>}
                {activeSession && !unassigned.length && <p className="field-hint allocation-hint">All eligible students in the active session have a supervisor.</p>}
            </section>
            <section className="surface-card dashboard-panel">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">SUPERVISION DISTRIBUTION</span><h2>Lecturer workload</h2></div></div>
                {workloads.length ? <div className="workload-list">{workloads.map((lecturer) => <div className="workload-item" key={lecturer.lecturer_id}><div className="workload-avatar">{getInitials(lecturer.name)}</div><div className="workload-person"><strong>{lecturer.name}</strong><small>{lecturer.designation || "Lecturer"}</small></div><div className="workload-count"><strong>{lecturer.active_supervisee_count}</strong><small>students</small></div></div>)}</div> : <EmptyState title="No lecturers available" description="Add lecturer accounts before assigning supervisors." />}
            </section>
            <section className="surface-card dashboard-table-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">CURRENT ALLOCATIONS</span><h2>Supervisor assignments <span className="heading-count">{currentAssignments.length}</span></h2></div><div className="table-toolbar"><select aria-label="Filter assignments by academic session" value={sessionFilter} onChange={(event) => setSessionFilter(event.target.value)}><option value="active">Active session</option><option value="">All sessions</option>{sessions.map((session) => <option key={session.id} value={session.id}>{session.name}</option>)}</select></div></div>
                {loading ? <LoadingState /> : currentAssignments.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Student</th><th>Matriculation no.</th><th>Supervisor</th><th>Session</th><th>Assigned</th><th>Action</th></tr></thead><tbody>{currentAssignments.map((item) => <tr key={item.id}><td><strong>{item.student_name}</strong></td><td>{item.matric_number}</td><td><strong>{item.lecturer_name}</strong><small>{item.lecturer_email}</small></td><td>{item.session_name}</td><td>{new Date(item.assigned_at).toLocaleDateString()}</td><td><button className="table-action table-action--primary" onClick={() => { setReassignment(item); setReassignmentLecturer(""); setReason(""); }}>Reassign</button></td></tr>)}</tbody></table></div> : <EmptyState title="No supervisor assignments" description="Student supervisor assignments will appear here." />}
            </section>
            {reassignment && <Modal title="Reassign supervisor" description={`${reassignment.student_name} · ${reassignment.matric_number}`} onClose={() => setReassignment(null)}>
                <form className="modal-form" onSubmit={reassignSupervisor}>
                    <div className="review-student-summary"><span className="review-avatar">{reassignment.student_name?.slice(0, 1).toUpperCase()}</span><div><strong>{reassignment.student_name}</strong><small>Current supervisor: {reassignment.lecturer_name}</small></div></div>
                    <Field label="New supervisor"><select required value={reassignmentLecturer} onChange={(event) => setReassignmentLecturer(event.target.value)}><option value="">Select another lecturer</option>{workloads.filter((item) => item.lecturer_id !== reassignment.lecturer).map((item) => <option key={item.lecturer_id} value={item.lecturer_id}>{item.name} · {item.active_supervisee_count} supervisees</option>)}</select></Field>
                    <Field label="Reason for reassignment" hint="Enter a reason for this change."><textarea rows="4" required value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Explain why the supervisor is being changed…" /></Field>
                    <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setReassignment(null)}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : "Confirm reassignment"}</button></div>
                </form>
            </Modal>}
        </>
    );
}

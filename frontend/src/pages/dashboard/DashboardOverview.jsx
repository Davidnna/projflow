import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext.jsx";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, LoadingState, PageHeader, StatCard, StatusBadge, getInitials } from "../../components/dashboard/WorkspaceUI.jsx";

const coordinatorRoles = ["administrator", "project_coordinator"];

function CoordinatorOverview() {
    const [data, setData] = useState(null);
    const [error, setError] = useState("");

    useEffect(() => {
        let active = true;
        Promise.all([
            apiRequest(endpoints.sessions),
            apiRequest(endpoints.roster),
            apiRequest(endpoints.enrollments),
            apiRequest(endpoints.lecturers),
            apiRequest(endpoints.assignments),
            apiRequest(endpoints.lecturerWorkloads),
        ]).then(([sessions, roster, enrollments, lecturers, assignments, workloads]) => {
            if (active) {
                setData({
                    sessions: getList(sessions),
                    roster: getList(roster),
                    enrollments: getList(enrollments),
                    lecturers: getList(lecturers),
                    assignments: getList(assignments),
                    workloads: getList(workloads),
                });
            }
        }).catch((requestError) => {
            if (active) {
                setError(requestError.message);
            }
        });
        return () => {
            active = false;
        };
    }, []);

    const activeSession = data?.sessions.find((session) => session.status === "active");
    const sessionEnrollments = useMemo(() => data?.enrollments.filter((item) => activeSession && item.session === activeSession.id) || [], [data, activeSession]);
    const sessionRoster = useMemo(() => data?.roster.filter((item) => activeSession && item.session === activeSession.id) || [], [data, activeSession]);
    const verified = sessionEnrollments.filter((item) => ["auto_verified", "manually_approved"].includes(item.verification_status));
    const pending = sessionEnrollments.filter((item) => item.verification_status === "pending_review");
    const currentAssignments = data?.assignments.filter((item) => item.is_current && activeSession && item.session_name === activeSession.name) || [];
    const unassigned = verified.filter((enrollment) => !currentAssignments.some((assignment) => assignment.student_enrollment === enrollment.id));

    if (!data && !error) {
        return <LoadingState label="Preparing your departmental overview…" />;
    }

    return (
        <>
            <PageHeader
                eyebrow="DEPARTMENTAL OVERVIEW"
                title="Good to see you."
                description="A summary of project administration in your department."
                actions={<Link className="button button-primary" to="/app/sessions">Manage sessions <span>→</span></Link>}
            />
            {error && <Alert type="error">We couldn't load your dashboard. Refresh the page and try again.</Alert>}
            {data && !activeSession && (
                <Alert type="warning">There is no active academic session. Create a session and activate it before adding students or allocating supervisors.</Alert>
            )}
            <div className="active-session-banner">
                <div className="active-session-mark">▦</div>
                <div><span>ACTIVE ACADEMIC SESSION</span><strong>{activeSession?.name || "No active session"}</strong><small>{activeSession ? "Current academic session" : "Activate a session when your department is ready."}</small></div>
                <StatusBadge value={activeSession?.status || "planned"}>{activeSession ? "Active" : "Not started"}</StatusBadge>
            </div>
            {data && (
                <div className="metric-grid">
                    <StatCard label="Eligible students" value={verified.length} detail={`${sessionRoster.length} roster records in this session`} icon="♙" tone="blue" />
                    <StatCard label="Registrations awaiting review" value={pending.length} detail="Require your attention" icon="◷" tone="amber" />
                    <StatCard label="Active supervisors" value={data.lecturers.filter((item) => item.is_active).length} detail="Lecturer accounts available" icon="♧" tone="teal" />
                    <StatCard label="Students allocated" value={currentAssignments.length} detail={`${unassigned.length} students awaiting allocation`} icon="⇄" tone="violet" />
                </div>
            )}
            <div className="dashboard-columns">
                <section className="surface-card dashboard-panel">
                    <div className="surface-card-heading"><div><span className="panel-eyebrow">NEXT ACTIONS</span><h2>Departmental operations</h2></div><span className="panel-icon">⌁</span></div>
                    <div className="action-list">
                        <Link to="/app/registrations" className="action-list-item"><span className="action-list-icon action-icon-amber">✓</span><span><strong>Review student registrations</strong><small>{pending.length} awaiting review</small></span><b>→</b></Link>
                        <Link to="/app/students" className="action-list-item"><span className="action-list-icon action-icon-blue">♙</span><span><strong>Manage student records</strong><small>Maintain the departmental student register</small></span><b>→</b></Link>
                        <Link to="/app/supervisors" className="action-list-item"><span className="action-list-icon action-icon-teal">⇄</span><span><strong>Allocate supervisors</strong><small>{unassigned.length} students awaiting allocation</small></span><b>→</b></Link>
                        <Link to="/app/lecturers" className="action-list-item"><span className="action-list-icon action-icon-violet">♧</span><span><strong>Manage lecturers</strong><small>Create and maintain lecturer accounts</small></span><b>→</b></Link>
                    </div>
                </section>
                <section className="surface-card dashboard-panel">
                    <div className="surface-card-heading"><div><span className="panel-eyebrow">SUPERVISION DISTRIBUTION</span><h2>Lecturer workload</h2></div><Link className="text-link" to="/app/supervisors">View all</Link></div>
                    {data?.workloads.length ? (
                        <div className="workload-list">
                            {data.workloads.slice(0, 5).map((lecturer) => (
                                <div className="workload-item" key={lecturer.lecturer_id}>
                                    <div className="workload-avatar">{getInitials(lecturer.name)}</div>
                                    <div className="workload-person"><strong>{lecturer.name}</strong><small>{lecturer.designation || "Lecturer"}</small></div>
                                    <div className="workload-count"><strong>{lecturer.active_supervisee_count}</strong><small>students</small></div>
                                </div>
                            ))}
                        </div>
                    ) : <EmptyState title="No lecturer workload yet" description="Add lecturer accounts to begin supervisor allocation." action={<Link className="text-link" to="/app/lecturers">Manage lecturers →</Link>} />}
                </section>
            </div>
            <div className="surface-card dashboard-table-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">RECENT REGISTRATIONS</span><h2>Registrations requiring attention</h2></div><Link className="text-link" to="/app/registrations">Open queue →</Link></div>
                {pending.length ? (
                    <div className="table-scroll"><table className="data-table"><thead><tr><th>Student</th><th>Matriculation no.</th><th>Academic session</th><th>Registration status</th></tr></thead><tbody>
                        {pending.slice(0, 5).map((item) => <tr key={item.id}><td><strong>{item.student_name}</strong><small>{item.student_email}</small></td><td>{item.matric_number}</td><td>{item.session_name}</td><td><StatusBadge value={item.verification_status} /></td></tr>)}
                    </tbody></table></div>
                ) : <EmptyState title="No registrations require review" description="There are no outstanding student registrations." />}
            </div>
        </>
    );
}

function LecturerOverview() {
    const [assignments, setAssignments] = useState([]);
    const [profile, setProfile] = useState(null);
    const [error, setError] = useState("");
    useEffect(() => {
        let active = true;
        Promise.all([apiRequest(endpoints.assignments), apiRequest(endpoints.lecturers)])
            .then(([assignmentData, profileData]) => {
                if (active) {
                    setAssignments(getList(assignmentData).filter((item) => item.is_current));
                    setProfile(getList(profileData)[0] || null);
                }
            })
            .catch((requestError) => active && setError(requestError.message));
        return () => { active = false; };
    }, []);
    return (
        <>
            <PageHeader eyebrow="LECTURER WORKSPACE" title="Your supervision overview" description="Review the students currently assigned to you and keep track of your supervision responsibilities." />
            {error && <Alert type="error">{error}</Alert>}
            <div className="metric-grid metric-grid--two">
                <StatCard label="Current supervisees" value={assignments.length} detail="Students assigned to you" icon="♙" tone="blue" />
                <StatCard label="Account status" value={profile?.is_active ? "Active" : profile ? "Inactive" : "—"} detail="Lecturer account" icon="♧" tone="teal" />
            </div>
            <section className="surface-card dashboard-table-card">
                <div className="surface-card-heading"><div><span className="panel-eyebrow">MY STUDENTS</span><h2>Current supervisees</h2></div><Link className="text-link" to="/app/topics/review">Review project topics →</Link></div>
                {assignments.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Student</th><th>Matriculation no.</th><th>Academic session</th><th>Assigned</th></tr></thead><tbody>{assignments.map((item) => <tr key={item.id}><td><strong>{item.student_name}</strong></td><td>{item.matric_number}</td><td>{item.session_name}</td><td>{new Date(item.assigned_at).toLocaleDateString()}</td></tr>)}</tbody></table></div> : <EmptyState title="No students assigned yet" description="Your assigned students will appear here." />}
            </section>
        </>
    );
}

function StudentOverview() {
    const [enrollment, setEnrollment] = useState(null);
    const [assignment, setAssignment] = useState(null);
    const [error, setError] = useState("");
    useEffect(() => {
        let active = true;
        Promise.all([
            apiRequest(`${endpoints.enrollments}mine/`),
            apiRequest(endpoints.assignments),
        ]).then(([enrollmentData, assignmentData]) => {
            if (active) {
                setEnrollment(enrollmentData);
                setAssignment(getList(assignmentData).find((item) => item.is_current) || null);
            }
        }).catch((requestError) => active && setError(requestError.message));
        return () => { active = false; };
    }, []);
    const verified = ["auto_verified", "manually_approved"].includes(enrollment?.verification_status);
    const rejected = enrollment?.verification_status === "rejected";
    return (
        <>
            <PageHeader eyebrow="STUDENT WORKSPACE" title="Welcome to your project workspace." description="View your registration details and assigned supervisor here." />
            {error && <Alert type="error">{error}</Alert>}
            {enrollment ? (
                <div className="student-status-card">
                    <div className="student-status-top"><div><span className="panel-eyebrow">REGISTRATION STATUS</span><h2>{enrollment.session_name}</h2></div><StatusBadge value={enrollment.verification_status} /></div>
                    <div className="student-status-details"><div><small>Matriculation number</small><strong>{enrollment.matric_number}</strong></div><div><small>Supervisor</small><strong>{assignment?.lecturer_name || "Not yet assigned"}</strong></div></div>
                    {!verified && !rejected && <Alert type="warning">Your registration is being reviewed. You will be able to continue once it has been approved.</Alert>}
                    {rejected && <Alert type="error">Your registration could not be approved. Please contact your department for assistance.</Alert>}
                    {verified && !assignment && <Alert type="info">Your registration is complete. The department will assign your supervisor.</Alert>}
                    {assignment && <Alert type="success">Your supervisor is {assignment.lecturer_name}.</Alert>}
                </div>
            ) : <EmptyState title="Registration details unavailable" description="We couldn't retrieve your registration details. Please contact your department for assistance." />}
            <div className="surface-card upcoming-card"><span className="panel-eyebrow">PROJECT INFORMATION</span><h2>Your project workspace</h2><p>Submit your proposed topic and follow your supervisor’s feedback.</p><Link className="button button-primary" to="/app/topics">Open my project topic</Link></div>
        </>
    );
}

export default function DashboardOverview() {
    const { hasAnyRole } = useAuth();
    if (hasAnyRole(coordinatorRoles)) {
        return <CoordinatorOverview />;
    }
    if (hasAnyRole(["lecturer"])) {
        return <LecturerOverview />;
    }
    return <StudentOverview />;
}

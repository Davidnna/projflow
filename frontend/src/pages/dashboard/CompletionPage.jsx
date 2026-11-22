import { useEffect, useState } from "react";
import { apiRequest } from "../../api.js";
import { Alert, EmptyState, Field, LoadingState, Modal, PageHeader, StatCard } from "../../components/dashboard/WorkspaceUI.jsx";
import { triggerDownload } from "../../utils/download.js";

const URL = "/api/projects/completion/";
const labels = {
    submitted: "Awaiting supervisor recommendation", revision_requested: "Revision requested", recommended: "Awaiting departmental clearance", clearance_denied: "Clearance withheld", cleared: "Cleared for defence", scheduled: "Defence scheduled", scoring: "Awaiting examiner scores", correction: "Score correction", approved: "Result approved", published: "Result published",
    submit: "Submit complete project", recommend: "Recommend for defence", decline: "Request final report revision", clear: "Grant clearance", deny_clearance: "Withhold clearance", schedule: "Allocate / schedule defence", score: "Submit my scores", approve_result: "Approve result", return_result: "Return result for correction", publish: "Publish result", appeal: "Submit appeal", review_appeal: "Record panel review", accept_appeal: "Accept appeal and reopen scoring", reject_appeal: "Reject appeal",
    set_deadline: "Set deadline", request_extension: "Request extension", approve_extension: "Approve extension", reject_extension: "Reject extension", save_scheme: "Save assessment structure", create_panel: "Create panel", update_panel: "Edit panel",
};
const noteRequired = ["decline", "deny_clearance", "return_result", "review_appeal", "accept_appeal", "reject_appeal", "reject_extension"];
const noNote = ["submit", "score", "schedule", "set_deadline", "request_extension", "save_scheme", "create_panel", "update_panel", "appeal"];
const display = (value) => labels[value] || String(value || "").replaceAll("_", " ");
const dateTime = (value) => value ? new Date(value).toLocaleString() : "Not scheduled";

function ActionForm({ modal, workspace, onClose, onSaved }) {
    const { action, project, kind, extension, panel, appeal } = modal;
    const [form, setForm] = useState({ kind: kind || "topic", note: "", panel: project?.panel || "", name: panel?.name || "", venue: project?.venue || "", members: panel?.members.map((m) => m.id) || [], components: workspace.scheme.length ? workspace.scheme.map((c) => ({ ...c })) : [{ name: "Project report", maximum: 60 }, { name: "Defence presentation", maximum: 40 }], marks: project?.components.map((c, i) => project.my_marks?.[i] ?? "") || [] });
    const [file, setFile] = useState(null);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));
    const fields = [{ kind: "topic", label: "Project topic" }, { kind: "final", label: "Final submission" }, { kind: "defence", label: "Defence" }, ...(workspace.sections || [])];
    async function submit(event) {
        event.preventDefault();
        setSaving(true);
        setError("");
        const payload = { ...form, action, session: workspace.session, project: project?.id, extension: extension?.id, appeal: appeal?.id };
        if (action === "update_panel") payload.panel = panel.id;
        
        if (action === "save_scheme") payload.components = form.components.map((c) => ({ name: c.name, maximum: Number(c.maximum) }));
        try {
            if (action === "schedule") payload.defence_at = new Date(form.defence_at).toISOString();
            if (action === "submit") {
                if (!file) throw new Error("Choose a PDF or DOCX document.");
                const body = new FormData();
                body.append("action", action); body.append("session", workspace.session); body.append("note", form.note); body.append("file", file);
                await apiRequest(URL, { method: "POST", body, formData: true, timeout: 120000 });
            } else {
                await apiRequest(URL, { method: "POST", body: payload });
            }
            onSaved();
        } catch (e) { setError(e.message); } finally { setSaving(false); }
    }
    return (
        <Modal title={display(action)} description={project ? `${project.student} · ${project.matric}` : undefined} onClose={() => !saving && onClose()} size="wide">
            <form className="modal-form" onSubmit={submit}>
                {error && <Alert type="error">{error}</Alert>}
                {action === "submit" && <><Field label="Complete project report" hint="PDF or DOCX; maximum 20 MB."><input required type="file" accept=".pdf,.docx" onChange={(e) => setFile(e.target.files[0])} /></Field><Field label="Submission note (optional)"><textarea value={form.note} maxLength={5000} onChange={(e) => set("note", e.target.value)} /></Field></>}
                {action === "set_deadline" && <><Field label="Activity"><select value={form.kind} onChange={(e) => set("kind", e.target.value)}>{fields.map((d) => <option key={d.kind} value={d.kind}>{d.label}</option>)}</select></Field><Field label="Due date"><input required type="date" onChange={(e) => set("due_date", e.target.value)} /></Field></>}
                {action === "request_extension" && <><p>Request an extension for {workspace.deadlines.find((d) => d.kind === kind)?.label}.</p><Field label="Proposed new date"><input type="date" required onChange={(e) => set("requested_date", e.target.value)} /></Field><Field label="Justification"><textarea required maxLength={5000} onChange={(e) => set("justification", e.target.value)} /></Field></>}
                {action === "save_scheme" && <><p>The component maximum marks must total exactly 100. This structure applies to all your supervisees in this session and is locked once a defence is allocated.</p>{form.components.map((component, index) => <div className="completion-component" key={index}><Field label={`Component ${index + 1}`}><input required maxLength={150} value={component.name} onChange={(e) => set("components", form.components.map((c, i) => i === index ? { ...c, name: e.target.value } : c))} /></Field><Field label="Maximum"><input required type="number" min="1" max="100" value={component.maximum} onChange={(e) => set("components", form.components.map((c, i) => i === index ? { ...c, maximum: e.target.value } : c))} /></Field><button type="button" className="button button-secondary" disabled={form.components.length === 1} onClick={() => set("components", form.components.filter((_, i) => i !== index))}>Remove</button></div>)}<div className="completion-actions"><button type="button" className="button button-secondary" disabled={form.components.length >= 30} onClick={() => set("components", [...form.components, { name: "", maximum: 1 }])}>Add component</button><strong>Total: {form.components.reduce((n, c) => n + Number(c.maximum || 0), 0)} / 100</strong></div></>}
                {["create_panel", "update_panel"].includes(action) && <><Field label="Panel name"><input required maxLength={150} value={form.name} onChange={(e) => set("name", e.target.value)} /></Field><fieldset className="completion-fieldset"><legend>Examination panel members</legend>{workspace.lecturers.map((l) => <label key={l.id}><input type="checkbox" checked={form.members.includes(l.id)} onChange={(e) => set("members", e.target.checked ? [...form.members, l.id] : form.members.filter((id) => id !== l.id))} /> {l.name}</label>)}</fieldset></>}
                {action === "schedule" && <><Field label="Examination panel"><select required value={form.panel} onChange={(e) => set("panel", e.target.value)}><option value="">Select panel</option>{workspace.panels.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.members.map((m) => m.name).join(", ")}</option>)}</select></Field><Field label="Defence date and time" hint="Time is interpreted in your device's local timezone."><input type="datetime-local" required onChange={(e) => set("defence_at", e.target.value)} /></Field><Field label="Venue"><input required maxLength={200} defaultValue={project.venue} onChange={(e) => set("venue", e.target.value)} /></Field></>}
                {action === "score" && <><p>Submit your independent marks. Other examiners cannot see your scores. Once submitted, marks are locked unless the Coordinator opens a correction round.</p>{project.components.map((c, i) => <Field key={i} label={`${c.name} (maximum ${c.maximum})`}><input type="number" required min="0" max={c.maximum} step="0.01" value={form.marks[i]} onChange={(e) => set("marks", form.marks.map((m, index) => index === i ? e.target.value : m))} /></Field>)}</>}
                {action === "appeal" && <Field label="Complaint and grounds for appeal"><textarea required maxLength={5000} rows={5} onChange={(e) => set("complaint", e.target.value)} /></Field>}
                {appeal && <p>{appeal.complaint}{appeal.panel_feedback && ` · Panel feedback: ${appeal.panel_feedback}`}</p>}
                {!noNote.includes(action) && <Field label={noteRequired.includes(action) ? "Reason / feedback (required)" : "Note (optional)"}><textarea required={noteRequired.includes(action)} maxLength={5000} rows={4} value={form.note} onChange={(e) => set("note", e.target.value)} /></Field>}
                <div className="modal-actions"><button type="button" className="button button-secondary" disabled={saving} onClick={onClose}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : display(action)}</button></div>
            </form>
        </Modal>
    );
}

function Result({ result, heading }) {
    if (!result?.components) return null;
    return <section className="completion-result"><h4>{heading}</h4><strong className="completion-total">{result.overall} / 100</strong><div className="completion-table-wrap"><table className="completion-table"><thead><tr><th>Component</th><th>Maximum</th><th>Average</th></tr></thead><tbody>{result.components.map((c, i) => <tr key={i}><td>{c.name}</td><td>{c.maximum}</td><td>{c.average}</td></tr>)}</tbody></table></div></section>;
}

export default function CompletionPage() {
    const [data, setData] = useState(null);
    const [session, setSession] = useState("");
    const [tab, setTab] = useState("projects");
    const [filter, setFilter] = useState("");
    const [modal, setModal] = useState(null);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [busy, setBusy] = useState(false);
    async function load(id = session) {
        setBusy(true);
        try { setData(await apiRequest(`${URL}${id ? `?session=${encodeURIComponent(id)}` : ""}`)); setError(""); } catch (e) { setError(e.message); } finally { setBusy(false); }
    }
    useEffect(() => { load(session); }, [session]);
    const w = data?.workspace;
    const active = w?.session_status === "active";
    function open(action, extra = {}) { setModal({ action, ...extra }); setSuccess(""); }
    async function download(doc) {
        try { const response = await apiRequest(`/api/projects/final-documents/${doc.id}/download/`); triggerDownload(response.url, doc.filename); } catch (e) { setError(e.message); }
    }
    return <>
        <PageHeader eyebrow="PROJECT COMPLETION" title="Final project and defence" description="Manage deadlines, final reports, examination panels, assessment, published results and appeals." />
        {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
        {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
        {busy && !data ? <LoadingState /> : <>
            <section className="surface-card completion-session"><Field label="Academic session"><select value={w?.session || ""} onChange={(e) => setSession(e.target.value)}>{data?.sessions.map((s) => <option key={s.id} value={s.id}>{s.name} · {display(s.status)}</option>)}</select></Field><button onClick={() => load()} className="button button-secondary" disabled={busy}>Refresh</button></section>
            {!w ? <EmptyState title="No academic session available" description="Your project workspace will appear once your academic registration or lecturer assignment is available." /> : <>
                {!active && <Alert type="warning">This session is not active. Historical records are read-only except permitted published-result appeals and corrections.</Alert>}
                <div className="metric-grid"><StatCard label="Final submissions" value={w.summary.final_submissions} detail="Visible to your role" icon="▤" tone="blue" /><StatCard label="Cleared for defence" value={w.summary.cleared} detail="Including scheduled and assessed" icon="✓" tone="teal" /><StatCard label="Published results" value={w.summary.published} detail="Official published results" icon="◫" tone="violet" /><StatCard label="Pending extensions" value={w.summary.pending_extensions} detail="Awaiting decision" icon="◷" tone="amber" /></div>
                <div className="topic-filter-tabs" role="tablist">{[["projects", "Final projects & results"], ["progress", "Progress register"], ["deadlines", "Deadlines & extensions"], ...(w.lecturer ? [["assessment", "My assessment structure"]] : []), ...(w.coordinator ? [["panels", "Examination panels"]] : [])].map(([id, label]) => <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)} className={`topic-filter-tab${tab === id ? " topic-filter-tab--active" : ""}`}>{label}</button>)}</div>
                {tab === "projects" && <>
                    {w.student && <section className="surface-card completion-card"><h2>Final report submission</h2><p>Topic: {w.topic_approved ? "Approved" : "Not approved"} · Required sections: {w.approved_count}/{w.required_count} approved · Supervisor: {w.supervisor_assigned ? "Assigned" : "Not assigned"}</p>{active && w.can_submit && !w.projects.some((p) => p.enrollment === w.enrollment) && <button className="button button-primary" onClick={() => open("submit")}>Submit complete project</button>}{!w.can_submit && <p>Obtain topic and required section approvals before submitting the complete report.</p>}</section>}
                    <section className="surface-card completion-card"><Field label="Search final projects"><input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Student name, matriculation number, status" /></Field></section>
                    {w.projects.filter((p) => `${p.student} ${p.matric} ${display(p.status)}`.toLowerCase().includes(filter.toLowerCase())).map((p) => <article className="surface-card completion-card" key={p.id}>
                        <div className="completion-heading"><div><h2>{p.student || p.matric}</h2><p>{p.matric} · {p.session}</p></div><span className="completion-state">{display(p.status)}</span></div>
                        {p.panel_name && <p><strong>Defence:</strong> {p.panel_name} · {dateTime(p.defence_at)} · {p.venue}</p>}
                        {p.documents.map((d) => <div className="completion-document" key={d.id}><div><strong>Version {d.version}: {d.filename}</strong><small>{dateTime(d.created_at)}</small>{d.note && <p>{d.note}</p>}</div><button className="button button-secondary" onClick={() => download(d)}>Download</button></div>)}
                        {p.score_count !== undefined && p.panel_size > 0 && <p>Examiners with recorded scores: {p.score_count}/{p.panel_size}</p>}
                        <Result result={p.published_result} heading="Published result" /><Result result={p.draft_result} heading="Coordinator review: calculated result" />
                        <div className="completion-actions">{p.actions.filter((a) => !["review_appeal", "accept_appeal", "reject_appeal"].includes(a)).map((a) => <button key={a} className={`button ${["publish", "approve_result", "clear", "recommend", "submit"].includes(a) ? "button-primary" : "button-secondary"}`} onClick={() => open(a, { project: p })}>{display(a)}</button>)}</div>
                        {p.appeals.length > 0 && <section><h3>Appeals</h3>{p.appeals.map((a) => <div key={a.id} className="completion-document"><div><strong>{display(a.status)} · {dateTime(a.created_at)}</strong><p>{a.complaint}</p>{a.panel_feedback && <p>Panel review: {a.panel_feedback}</p>}{a.decision_note && <p>Decision: {a.decision_note}</p>}</div><div className="completion-actions">{p.actions.filter((op) => (op === "review_appeal" && a.status === "pending") || (["accept_appeal", "reject_appeal"].includes(op) && a.status === "reviewed")).map((op) => <button key={op} className="button button-secondary" onClick={() => open(op, { project: p, appeal: a })}>{display(op)}</button>)}</div></div>)}</section>}
                        {p.events.length > 0 && <details><summary>Workflow history ({p.events.length})</summary>{p.events.map((e, i) => <div className="completion-history" key={i}><strong>{display(e.action)}</strong><small>{dateTime(e.created_at)}</small>{e.schedule && <p>{e.schedule.panel_name} · {dateTime(e.schedule.defence_at)} · {e.schedule.venue}</p>}{e.note && <p>{e.note}</p>}</div>)}</details>}
                    </article>)}
                    {!w.projects.length && <EmptyState title="No final project records yet" description="Submitted final reports and assigned examinations appear here." />}
                </>}
                {tab === "progress" && <section className="surface-card completion-card"><div className="completion-heading"><h2>Project progress register</h2><span>{w.summary.topics_approved} topics approved · {w.summary.overdue_students} students with overdue work</span></div><Field label="Search students"><input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Name, matriculation number, supervisor" /></Field><div className="completion-table-wrap"><table className="completion-table"><thead><tr><th>Student</th><th>Supervisor</th><th>Topic</th><th>Required report sections</th><th>Final project</th><th>Overdue activities</th></tr></thead><tbody>{w.progress.filter((p) => `${p.name} ${p.matric} ${p.supervisor}`.toLowerCase().includes(filter.toLowerCase())).map((p) => <tr key={p.id}><td><strong>{p.name}</strong><br />{p.matric}</td><td>{p.supervisor || "Not assigned"}</td><td>{display(p.topic_status)}</td><td>{p.sections_approved}/{p.sections_required} approved<br />{p.pending_reviews} awaiting review</td><td>{display(p.final_status)}</td><td>{p.overdue.length ? p.overdue.map((d) => <div key={d.label}>{d.label} · {d.due_date}</div>) : "None"}</td></tr>)}</tbody></table></div>{!w.progress.length && <p>No student records available for this role.</p>}</section>}
                {tab === "deadlines" && <section className="surface-card completion-card"><div className="completion-heading"><h2>Session deadlines</h2>{active && w.coordinator && <button className="button button-primary" onClick={() => open("set_deadline")}>Set deadline</button>}</div><p>Deadlines track timely submission and approved extensions. Late submissions remain available for review; deadlines do not close the academic session.</p>{w.deadlines.map((d) => <div className="completion-document" key={d.kind}><div><strong>{d.label}</strong><p>Due {d.due_date}{d.effective_date && d.effective_date !== d.due_date ? ` · Extended to ${d.effective_date}` : ""}{d.overdue ? " · Overdue" : d.completed ? " · Completed" : ""}</p></div>{active && w.student && <button className="button button-secondary" onClick={() => open("request_extension", { kind: d.kind })}>Request extension</button>}{active && w.coordinator && <button className="button button-secondary" onClick={() => open("set_deadline", { kind: d.kind })}>Change date</button>}</div>)}{!w.deadlines.length && <p>No deadlines configured yet. Chapter deadlines can also be set in Report structure.</p>}<h3>Extension requests</h3>{w.extensions.map((e) => <div className="completion-document" key={e.id}><div><strong>{e.student} · {e.label} · {display(e.status)}</strong><p>{e.original_due_date} → {e.requested_date}</p><p>{e.justification}</p>{e.decision_note && <p>{e.decision_note}</p>}</div>{active && w.coordinator && e.status === "pending" && <div className="completion-actions"><button className="button button-primary" onClick={() => open("approve_extension", { extension: e })}>Approve</button><button className="button button-secondary" onClick={() => open("reject_extension", { extension: e })}>Reject</button></div>}</div>)}{!w.extensions.length && <p>No extension requests.</p>}</section>}
                {tab === "assessment" && w.lecturer && <section className="surface-card completion-card"><div className="completion-heading"><h2>Assessment structure</h2>{active && <button className="button button-primary" onClick={() => open("save_scheme")}>{w.scheme.length ? "Edit structure" : "Configure structure"}</button>}</div><p>One structure per supervisor per session. Examiners, not the supervisor, award the marks.</p>{w.scheme.map((c, i) => <div className="completion-document" key={i}><strong>{c.name}</strong><span>{c.maximum} marks</span></div>)}</section>}
                {tab === "panels" && w.coordinator && <section className="surface-card completion-card"><div className="completion-heading"><h2>Examination panels</h2>{active && <button className="button button-primary" onClick={() => open("create_panel")}>Create panel</button>}</div>{w.panels.map((p) => <div className="completion-document" key={p.id}><div><strong>{p.name}</strong><p>{p.members.map((m) => m.name).join(", ")}</p></div>{active && <button className="button button-secondary" onClick={() => open("update_panel", { panel: p })}>Edit</button>}</div>)}{!w.panels.length && <p>No panels created.</p>}</section>}
            </>}
        </>}
        {modal && w && <ActionForm key={`${modal.action}-${modal.project?.id || modal.kind || ""}`} modal={modal} workspace={w} onClose={() => setModal(null)} onSaved={() => { setModal(null); setSuccess("Saved successfully."); load(); }} />}
    </>;
}

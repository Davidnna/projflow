import { Link } from "react-router-dom";

const modules = [
  { title: "Accounts and access", text: "A central account foundation with support for multiple global roles.", state: "Foundation included", ready: true },
  { title: "Student and project records", text: "Departmental student register, project cycles and individual project records.", state: "Planned" },
  { title: "Supervision and topic review", text: "Supervisor allocation, topic proposals, revisions and approval history.", state: "Planned" },
  { title: "Submissions and feedback", text: "Chapter versions, complete project submissions and supervisor reviews.", state: "Planned" },
  { title: "Examination management", text: "Examination groups, flexible panels, memberships and schedules.", state: "Planned" },
  { title: "Assessment and results", text: "Individual examiner marks, collective criterion scores, grading and controlled publication.", state: "Planned" },
];

export default function PlatformPage() {
  return (
    <section className="inner-page">
      <div className="inner-page-heading">
        <div className="eyebrow eyebrow-light">PLATFORM OVERVIEW</div>
        <h1>A connected process for final-year projects.</h1>
        <p>ProjFlow is being developed as a single-department platform. Its modules will follow the approved project workflow and permission rules.</p>
      </div>
      <div className="module-grid">
        {modules.map((module, index) => (
          <article className="module-card" key={module.title}>
            <div className="module-card-head"><span className="module-index">{String(index + 1).padStart(2, "0")}</span><span className={`module-state${module.ready ? " module-state-ready" : ""}`}>{module.state}</span></div>
            <h2>{module.title}</h2><p>{module.text}</p>
          </article>
        ))}
      </div>
      <div className="scope-note"><div className="scope-icon">i</div><div><strong>Development status</strong><p>Only the initial application foundation and account data models are included in this release. The remaining modules are not yet available for operational use.</p></div></div>
      <div className="page-back-link"><Link to="/">← Back to overview</Link></div>
    </section>
  );
}

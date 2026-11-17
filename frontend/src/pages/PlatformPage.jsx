import { Link } from "react-router-dom";

const modules = [
    { title: "Accounts and access", text: "Email and password authentication, student self-registration, JWT sessions and role-aware workspace access.", state: "Available", ready: true },
    { title: "Academic administration", text: "Academic session management, departmental student records, spreadsheet import, registration review and lecturer accounts.", state: "Available", ready: true },
    { title: "Supervisor allocation", text: "Coordinator-managed student allocation, lecturer workload visibility and traceable supervisor reassignment.", state: "Available", ready: true },
    { title: "Project topics and supervision", text: "Independent topic proposals, supervisor decisions and local topic-similarity analysis.", state: "Planned" },
    { title: "Submissions and feedback", text: "Chapter versions, private document storage, annotated feedback and final project submissions.", state: "Planned" },
    { title: "Examination and results", text: "Defence panels, schedules, assessment components, examiner scoring, result approval and appeals.", state: "Planned" },
];

export default function PlatformPage() {
    return (
        <section className="inner-page">
            <div className="inner-page-heading">
                <div className="eyebrow eyebrow-light">PLATFORM OVERVIEW</div>
                <h1>A connected process for final-year projects.</h1>
                <p>ProjFlow is a single-department platform. The authenticated workspace now supports academic administration, student onboarding, lecturer management and supervisor allocation. Additional project lifecycle modules will follow.</p>
            </div>
            <div className="module-grid">
                {modules.map((module, index) => (
                    <article className="module-card" key={module.title}>
                        <div className="module-card-head"><span className="module-index">{String(index + 1).padStart(2, "0")}</span><span className={`module-state${module.ready ? " module-state-ready" : ""}`}>{module.state}</span></div>
                        <h2>{module.title}</h2><p>{module.text}</p>
                    </article>
                ))}
            </div>
            <div className="scope-note"><div className="scope-icon">i</div><div><strong>Release 0.3.1</strong><p>Authentication and the first academic administration interfaces are available. Topic proposals, project submissions, progress monitoring, examinations and results remain planned modules and are not yet operational.</p></div></div>
            <div className="page-back-link"><Link to="/">← Back to overview</Link></div>
        </section>
    );
}

import { Link } from "react-router-dom";

const capabilities = [
    {
        number: "01",
        title: "Academic session management",
        description: "Create academic sessions and manage when each project cycle becomes active or closes.",
    },
    {
        number: "02",
        title: "Departmental student records",
        description: "Maintain the eligible student register, add records individually or import a spreadsheet.",
    },
    {
        number: "03",
        title: "Student registration",
        description: "Allow students to register online and have their details checked against the departmental register.",
    },
    {
        number: "04",
        title: "Lecturer management",
        description: "Maintain lecturer profiles and provide access to the lecturers who support the project process.",
    },
    {
        number: "05",
        title: "Supervisor allocation",
        description: "Assign verified students to supervisors while keeping lecturer workloads visible.",
    },
    {
        number: "06",
        title: "Role-based workspaces",
        description: "Give students, lecturers and departmental administrators access to the tools relevant to their responsibilities.",
    },
];

const workflow = [
    ["01", "Set up the session", "The Project Coordinator creates and activates the academic session when the department is ready."],
    ["02", "Prepare the student register", "Eligible student records are entered individually or imported from a CSV or Excel file."],
    ["03", "Students register", "Students submit their details through the public registration page."],
    ["04", "Details are checked", "Matching eligible records are verified automatically. Exceptions are referred for staff review."],
    ["05", "Supervisors are assigned", "The Coordinator assigns verified students and lecturers can view their supervision responsibilities."],
];

const audiences = [
    { title: "Students", description: "Register using your departmental details and access your student workspace." },
    { title: "Lecturers", description: "View your assigned students and the supervision responsibilities recorded for you." },
    { title: "Project Coordinators", description: "Manage academic sessions, student records, registrations, lecturer accounts and supervisor assignments." },
];

const faqs = [
    {
        question: "Who can use ProjFlow?",
        answer: "ProjFlow provides separate workspaces for students, lecturers, Project Coordinators and Administrators within a participating academic department.",
    },
    {
        question: "Can a student register without being on the departmental register?",
        answer: "Students should be included in the department's eligible student register. If a record is missing or the submitted details do not match, the registration is referred for staff review.",
    },
    {
        question: "Does an academic session need start and end dates?",
        answer: "No. The Project Coordinator creates, activates and closes academic sessions manually. Session changes are not triggered by calendar dates.",
    },
];

export default function HomePage() {
    return (
        <>
            <section className="public-hero">
                <div className="public-container public-hero-grid">
                    <div className="public-hero-copy">
                        <div className="public-eyebrow"><span /> FINAL-YEAR PROJECT COORDINATION</div>
                        <h1>Bring your department's project work into <span>one clear process.</span></h1>
                        <p>
                            ProjFlow helps academic departments organise academic sessions, student records,
                            student registration, lecturer information and supervisor assignments in one place.
                        </p>
                        <div className="public-hero-actions">
                            <Link className="public-button public-button-primary" to="/features">Explore the features <span aria-hidden="true">→</span></Link>
                            <Link className="public-button public-button-secondary" to="/register">Student registration</Link>
                        </div>
                        <div className="public-hero-footnote"><span>✓</span> One organised workspace for students and departmental project teams.</div>
                    </div>
                    <div className="public-hero-art" aria-label="Illustration of ProjFlow's academic coordination workspace">
                        <div className="public-art-ring public-art-ring-one" />
                        <div className="public-art-ring public-art-ring-two" />
                        <div className="public-dashboard-card">
                            <div className="public-dashboard-top">
                                <div>
                                    <span className="public-dashboard-label">DEPARTMENT WORKSPACE</span>
                                    <h2>Academic coordination</h2>
                                </div>
                                <span className="public-dashboard-mark">PF</span>
                            </div>
                            <div className="public-dashboard-session">
                                <span>Academic session</span>
                                <strong>Managed by your department</strong>
                            </div>
                            <div className="public-dashboard-list">
                                <div><span className="public-dashboard-icon">01</span><span><strong>Student records</strong><small>Individual entry and spreadsheet import</small></span><b>↗</b></div>
                                <div><span className="public-dashboard-icon public-dashboard-icon-teal">02</span><span><strong>Student registration</strong><small>Departmental record verification</small></span><b>↗</b></div>
                                <div><span className="public-dashboard-icon public-dashboard-icon-violet">03</span><span><strong>Supervisor allocation</strong><small>Assignments and workload visibility</small></span><b>↗</b></div>
                            </div>
                            <div className="public-dashboard-bottom"><span /> Information organised around clear responsibilities</div>
                        </div>
                        <div className="public-floating-note public-floating-note-top"><span className="public-floating-symbol">✓</span><span><strong>Clear records</strong><small>One departmental register</small></span></div>
                        <div className="public-floating-note public-floating-note-bottom"><span className="public-floating-symbol public-floating-symbol-blue">↗</span><span><strong>Connected roles</strong><small>Relevant workspace access</small></span></div>
                    </div>
                </div>
            </section>

            <section className="public-value-strip">
                <div className="public-container public-value-grid">
                    <span>BUILT AROUND DEPARTMENTAL PROJECT ADMINISTRATION</span>
                    <div><b>01</b> Organisation</div>
                    <div><b>02</b> Accountability</div>
                    <div><b>03</b> Coordination</div>
                    <div><b>04</b> Continuity</div>
                </div>
            </section>

            <section className="public-section public-section-white" id="features">
                <div className="public-container">
                    <div className="public-section-heading">
                        <div>
                            <div className="public-eyebrow">WHAT PROJFLOW PROVIDES</div>
                            <h2>Departmental project administration, brought together.</h2>
                        </div>
                        <p>
                            The current platform focuses on the administrative work that helps a department
                            organise its students, lecturers and supervision responsibilities.
                        </p>
                    </div>
                    <div className="public-capability-grid">
                        {capabilities.map((item) => (
                            <article className="public-capability-card" key={item.number}>
                                <span className="public-card-number">{item.number}</span>
                                <span className="public-card-arrow" aria-hidden="true">↗</span>
                                <h3>{item.title}</h3>
                                <p>{item.description}</p>
                            </article>
                        ))}
                    </div>
                    <div className="public-inline-link"><Link to="/features">View all platform features <span aria-hidden="true">→</span></Link></div>
                </div>
            </section>

            <section className="public-section public-section-soft">
                <div className="public-container">
                    <div className="public-section-heading public-section-heading-centered">
                        <div>
                            <div className="public-eyebrow">HOW THE PROCESS WORKS</div>
                            <h2>From departmental setup to supervisor allocation.</h2>
                        </div>
                        <p>ProjFlow brings the main onboarding and coordination steps into a consistent departmental workflow.</p>
                    </div>
                    <div className="public-workflow-grid">
                        {workflow.map(([number, title, description], index) => (
                            <article className="public-workflow-step" key={number}>
                                <div className="public-workflow-step-top"><span>{number}</span>{index < workflow.length - 1 && <i aria-hidden="true" />}</div>
                                <h3>{title}</h3>
                                <p>{description}</p>
                            </article>
                        ))}
                    </div>
                    <div className="public-centered-link"><Link to="/how-it-works">See how ProjFlow works <span aria-hidden="true">→</span></Link></div>
                </div>
            </section>

            <section className="public-section public-section-white">
                <div className="public-container">
                    <div className="public-section-heading">
                        <div>
                            <div className="public-eyebrow">A WORKSPACE FOR EACH ROLE</div>
                            <h2>Everyone sees the work relevant to them.</h2>
                        </div>
                        <p>ProjFlow organises access around the responsibilities each person has in the departmental project process.</p>
                    </div>
                    <div className="public-audience-grid">
                        {audiences.map((item, index) => (
                            <article className="public-audience-card" key={item.title}>
                                <span>0{index + 1}</span>
                                <h3>{item.title}</h3>
                                <p>{item.description}</p>
                            </article>
                        ))}
                    </div>
                </div>
            </section>

            <section className="public-section public-section-soft" id="faq">
                <div className="public-container public-faq-layout">
                    <div className="public-faq-intro">
                        <div className="public-eyebrow">COMMON QUESTIONS</div>
                        <h2>Before you get started.</h2>
                        <p>Find out how registration and departmental access work.</p>
                        <Link to="/how-it-works#faq">More questions and answers <span aria-hidden="true">→</span></Link>
                    </div>
                    <div className="public-faq-list">
                        {faqs.map((item) => (
                            <details className="public-faq-item" key={item.question}>
                                <summary>{item.question}<span aria-hidden="true">+</span></summary>
                                <p>{item.answer}</p>
                            </details>
                        ))}
                    </div>
                </div>
            </section>

            <section className="public-cta-section">
                <div className="public-container public-cta-panel">
                    <div>
                        <div className="public-eyebrow public-eyebrow-light">GET STARTED WITH PROJFLOW</div>
                        <h2>Ready to access your project workspace?</h2>
                        <p>Students can register using their departmental details. Existing users can sign in to continue.</p>
                    </div>
                    <div className="public-cta-actions">
                        <Link className="public-button public-button-light" to="/register">Student registration <span aria-hidden="true">→</span></Link>
                        <Link className="public-cta-signin" to="/login">Already registered? Sign in</Link>
                    </div>
                </div>
            </section>
        </>
    );
}

import { Link } from "react-router-dom";

const features = [
    { number: "01", title: "Academic coordination", description: "Keep academic sessions and departmental project records organised." },
    { number: "02", title: "Student and lecturer management", description: "Maintain student records, support registration and manage lecturer accounts." },
    { number: "03", title: "Supervisor coordination", description: "Assign supervisors, review lecturer workloads and manage changes when needed." },
];
const stages = [
    ["01", "Propose", "Topic submission and review"],
    ["02", "Develop", "Supervision and project work"],
    ["03", "Submit", "Final project submission"],
    ["04", "Defend", "Examination and assessment"],
];

export default function HomePage() {
    return (
        <>
            <section className="hero-section">
                <div className="hero-grid">
                    <div className="hero-copy">
                        <div className="eyebrow"><span className="eyebrow-dot" />FINAL-YEAR PROJECT MANAGEMENT</div>
                        <h1>A clearer way to manage <span>final-year projects.</span></h1>
                        <p className="hero-description">ProjFlow brings students, lecturers and project coordinators together to keep departmental project activities organised.</p>
                        <div className="hero-actions">
                            <Link className="button button-primary" to="/login">Sign in to ProjFlow <span aria-hidden="true">→</span></Link>
                            <Link className="button button-secondary" to="/register">Student registration</Link>
                        </div>
                        <div className="hero-note"><span className="note-check">✓</span>One organised workspace for your department.</div>
                    </div>
                    <div className="hero-visual" aria-label="Illustration of the project workflow">
                        <div className="visual-orbit orbit-one" /><div className="visual-orbit orbit-two" />
                        <div className="visual-card-main">
                            <div className="visual-card-top"><span className="visual-kicker">PROJECT JOURNEY</span><span className="visual-menu">•••</span></div>
                            <div className="visual-heading">From proposal to defence</div>
                            <div className="visual-progress-track"><div className="visual-progress-fill" /></div>
                            <div className="visual-progress-label"><span>Project stages</span><strong>4 stages</strong></div>
                            <div className="visual-stage-list">
                                {stages.map(([number, title, description], index) => (
                                    <div className="visual-stage" key={number}>
                                        <span className={`stage-number${index === 0 ? " stage-number-active" : ""}`}>{number}</span>
                                        <span className="stage-copy"><strong>{title}</strong><small>{description}</small></span>
                                        <span className="stage-arrow">↗</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="floating-chip chip-top"><span className="chip-icon">↗</span><span><strong>One workspace</strong><small>Connected activities</small></span></div>
                        <div className="floating-chip chip-bottom"><span className="chip-icon chip-icon-teal">✓</span><span><strong>Well organised</strong><small>Clear responsibilities</small></span></div>
                    </div>
                </div>
            </section>

            <section className="principles-strip">
                <div className="principles-inner">
                    <span>DESIGNED FOR BETTER PROJECT COORDINATION</span>
                    <div><b>01</b> Organisation</div><div><b>02</b> Accountability</div><div><b>03</b> Collaboration</div><div><b>04</b> Progress</div>
                </div>
            </section>

            <section className="content-section">
                <div className="section-heading">
                    <div><div className="eyebrow eyebrow-light">A BETTER WAY TO WORK</div><h2>Keep every important detail organised.</h2></div>
                    <p>ProjFlow gives your department a shared place to manage the people, records and responsibilities involved in final-year projects.</p>
                </div>
                <div className="feature-grid">
                    {features.map((feature) => (
                        <article className="feature-card" key={feature.number}>
                            <div className="feature-card-top"><span className="feature-number">{feature.number}</span><span className="feature-arrow">↗</span></div>
                            <h3>{feature.title}</h3><p>{feature.description}</p>
                        </article>
                    ))}
                </div>
            </section>

            <section className="closing-section">
                <div className="closing-panel">
                    <div>
                        <div className="eyebrow eyebrow-on-dark">PROJFLOW</div>
                        <h2>Bring your department's project activities together.</h2>
                        <p>Manage academic sessions, student records, lecturer accounts and supervisor assignments in one organised workspace.</p>
                    </div>
                    <Link className="button button-light" to="/login">Sign in to ProjFlow <span aria-hidden="true">→</span></Link>
                </div>
            </section>
        </>
    );
}

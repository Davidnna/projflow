import { Link } from "react-router-dom";

const principles = [
    {
        title: "A shared departmental record",
        description: "Keep academic sessions, eligible student records, lecturer profiles and supervision assignments in one organised place.",
    },
    {
        title: "Clear responsibilities",
        description: "Give students, lecturers and departmental administrators workspaces that reflect their roles in the project process.",
    },
    {
        title: "Consistent student onboarding",
        description: "Use the departmental register as the basis for student registration checks, with staff review when details need attention.",
    },
];

export default function PlatformPage() {
    return (
        <div className="public-page">
            <section className="public-page-hero">
                <div className="public-container public-page-hero-inner">
                    <div className="public-eyebrow">ABOUT PROJFLOW</div>
                    <h1>A clearer way to coordinate the departmental project process.</h1>
                    <p>
                        ProjFlow is a web-based final-year project management platform for academic departments.
                        It brings together academic session management, student onboarding, lecturer records,
                        supervisor allocation and project-topic proposal review.
                    </p>
                    <div className="public-page-actions">
                        <Link className="public-button public-button-primary" to="/features">Explore platform features <span aria-hidden="true">→</span></Link>
                        <Link className="public-text-link" to="/how-it-works">How it works</Link>
                    </div>
                </div>
            </section>

            <section className="public-section public-section-white">
                <div className="public-container public-about-intro">
                    <div>
                        <div className="public-eyebrow">THE PURPOSE</div>
                        <h2>Bring the people and records behind project coordination together.</h2>
                    </div>
                    <div>
                        <p>
                            Final-year project administration involves more than the project document itself.
                            Departments also need to maintain student records, organise academic sessions,
                            onboard students, manage lecturer information, allocate supervisors and review project topics.
                        </p>
                        <p>
                            ProjFlow provides a shared digital workspace for these responsibilities, helping
                            the department keep information organised and accessible to the people who need it.
                        </p>
                    </div>
                </div>
            </section>

            <section className="public-section public-section-soft">
                <div className="public-container">
                    <div className="public-section-heading">
                        <div>
                            <div className="public-eyebrow">HOW PROJFLOW IS DESIGNED</div>
                            <h2>Built around practical departmental needs.</h2>
                        </div>
                        <p>Its working principles focus on clarity, consistent records and role-appropriate access.</p>
                    </div>
                    <div className="public-principle-grid">
                        {principles.map((item, index) => (
                            <article className="public-principle-card" key={item.title}>
                                <span>0{index + 1}</span>
                                <h3>{item.title}</h3>
                                <p>{item.description}</p>
                            </article>
                        ))}
                    </div>
                </div>
            </section>

            <section className="public-section public-section-white">
                <div className="public-container public-scope-panel">
                    <div>
                        <div className="public-eyebrow">DEPARTMENTAL SCOPE</div>
                        <h2>Designed for a department's project cycle.</h2>
                        <p>
                            ProjFlow is configured around one academic department. It can retain records across
                            academic sessions while the department manages one active project cycle at a time.
                        </p>
                    </div>
                    <div className="public-scope-points">
                        <div><span>✓</span><p>Academic sessions are activated and closed by the Project Coordinator.</p></div>
                        <div><span>✓</span><p>Student records can be entered individually or imported in a spreadsheet.</p></div>
                        <div><span>✓</span><p>Verified students can be assigned to a project supervisor.</p></div>
                        <div><span>✓</span><p>Students submit proposals to their assigned supervisor for review and approval.</p></div>
                    </div>
                </div>
            </section>

            <section className="public-cta-section">
                <div className="public-container public-cta-panel">
                    <div>
                        <div className="public-eyebrow public-eyebrow-light">EXPLORE THE PLATFORM</div>
                        <h2>See what ProjFlow can help your department manage.</h2>
                        <p>Explore the current platform features or continue to student registration.</p>
                    </div>
                    <div className="public-cta-actions">
                        <Link className="public-button public-button-light" to="/features">Explore features <span aria-hidden="true">→</span></Link>
                        <Link className="public-cta-signin" to="/register">Student registration</Link>
                    </div>
                </div>
            </section>
        </div>
    );
}

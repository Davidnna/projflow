import { Link } from "react-router-dom";

const featureGroups = [
    {
        number: "01",
        title: "Academic session management",
        intro: "Manage the academic project cycle according to departmental decisions.",
        points: [
            "Create academic sessions using a session name.",
            "Activate or close a session manually when the department is ready.",
            "Keep previous sessions available for historical reference.",
        ],
    },
    {
        number: "02",
        title: "Departmental student records",
        intro: "Maintain the eligible student register for the active academic session.",
        points: [
            "Add or update student records individually.",
            "Import student lists from CSV or Excel files.",
            "Review imported records and validation results before confirming an import.",
        ],
    },
    {
        number: "03",
        title: "Student registration and verification",
        intro: "Give students a direct way to register while keeping the departmental register central to the process.",
        points: [
            "Students submit their details through the public registration page.",
            "Eligible records with matching details are verified automatically.",
            "Missing, ineligible or inconsistent records are referred for staff review.",
        ],
    },
    {
        number: "04",
        title: "Lecturer records",
        intro: "Keep lecturer information organised for departmental project coordination.",
        points: [
            "Create lecturer accounts from the administrative workspace.",
            "Maintain a departmental lecturer directory.",
            "Provide lecturers with access to their assigned supervision information.",
        ],
    },
    {
        number: "05",
        title: "Supervisor allocation",
        intro: "Coordinate which lecturer is responsible for each verified student.",
        points: [
            "Assign a supervisor to a verified student.",
            "View lecturer supervision workloads when making assignments.",
            "Reassign a student when necessary and retain the reason and assignment history.",
        ],
    },
    {
        number: "06",
        title: "Project topic submission and review",
        intro: "Move the first academic approval stage into a clear student-supervisor workflow.",
        points: [
            "Students submit a title, abstract, problem statement, research objectives and keywords.",
            "The assigned supervisor approves the proposal, requests revision or rejects it.",
            "Students can revise and resubmit when changes are requested, with submission history retained.",
        ],
    },
    {
        number: "07",
        title: "Project topic similarity review",
        intro: "Help supervisors identify proposals that may overlap with work submitted in previous academic sessions.",
        points: [
            "Compare project titles, abstracts, problem statements, research objectives and keywords.",
            "Combine keyword matching with meaning-based comparison to identify potentially related proposals.",
            "Show potential matches and relevant sections to the assigned supervisor only; academic decisions remain with the supervisor.",
        ],
    },
    {
        number: "08",
        title: "Project milestones and progress monitoring",
        intro: "Keep project work moving through common departmental milestones and supervisor feedback.",
        points: [
            "The Project Coordinator defines the milestone structure for each academic session.",
            "Students submit progress reports describing completed activities, challenges and next steps.",
            "Supervisors review reports, provide feedback and record progress assessments.",
            "Submission and assessment history remains available to the student and assigned supervisor.",
        ],
    },
    {
        number: "09",
        title: "Role-based workspaces",
        intro: "Present relevant information and actions according to each person's role.",
        points: [
            "Students submit proposals and follow supervisor feedback.",
            "Lecturers review proposals from their assigned students.",
            "Project Coordinators and Administrators manage departmental records and assignments.",
        ],
    },
];

export default function FeaturesPage() {
    return (
        <div className="public-page">
            <section className="public-page-hero">
                <div className="public-container public-page-hero-inner">
                    <div className="public-eyebrow">PROJFLOW FEATURES</div>
                    <h1>The essential tools for organised project administration.</h1>
                    <p>
                        ProjFlow brings together academic sessions, student onboarding, supervisor allocation,
                        project-topic review, historical topic similarity checks and milestone-based progress monitoring.
                    </p>
                    <div className="public-page-actions">
                        <Link className="public-button public-button-primary" to="/how-it-works">See how it works <span aria-hidden="true">→</span></Link>
                        <Link className="public-text-link" to="/register">Student registration</Link>
                    </div>
                </div>
            </section>

            <section className="public-section public-section-white">
                <div className="public-container">
                    <div className="public-feature-list">
                        {featureGroups.map((feature) => (
                            <article className="public-feature-detail" key={feature.number}>
                                <div className="public-feature-detail-number">{feature.number}</div>
                                <div className="public-feature-detail-content">
                                    <h2>{feature.title}</h2>
                                    <p className="public-feature-detail-intro">{feature.intro}</p>
                                    <ul>
                                        {feature.points.map((point) => <li key={point}>{point}</li>)}
                                    </ul>
                                </div>
                            </article>
                        ))}
                    </div>
                    <p className="public-feature-note">
                        ProjFlow's available features cover academic administration, student onboarding, supervisor
                        coordination, project-topic review, supervisor-only similarity findings and milestone-based progress monitoring. Access to each workspace depends on the user's role.
                    </p>
                </div>
            </section>

            <section className="public-cta-section">
                <div className="public-container public-cta-panel">
                    <div>
                        <div className="public-eyebrow public-eyebrow-light">START HERE</div>
                        <h2>Are you a student in the department?</h2>
                        <p>Use your departmental details to create your ProjFlow account.</p>
                    </div>
                    <div className="public-cta-actions">
                        <Link className="public-button public-button-light" to="/register">Student registration <span aria-hidden="true">→</span></Link>
                        <Link className="public-cta-signin" to="/login">Already registered? Sign in</Link>
                    </div>
                </div>
            </section>
        </div>
    );
}

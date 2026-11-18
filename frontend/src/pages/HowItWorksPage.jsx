import { Link } from "react-router-dom";

const steps = [
    {
        number: "01",
        title: "The Project Coordinator creates an academic session",
        description: "The session is created by name and activated manually when the department is ready. The department does not need to set start or end dates.",
        owner: "Project Coordinator",
    },
    {
        number: "02",
        title: "The departmental student register is prepared",
        description: "Eligible student records are entered individually or imported from a CSV or Excel spreadsheet. The import can be reviewed before records are saved.",
        owner: "Project Coordinator",
    },
    {
        number: "03",
        title: "Students create their accounts",
        description: "Students register with their matriculation number and the identity and contact details requested by the department.",
        owner: "Student",
    },
    {
        number: "04",
        title: "Registration details are checked",
        description: "ProjFlow compares the submitted details with the active session's eligible student register. Matching records are verified automatically; records that need attention are referred for staff review.",
        owner: "ProjFlow and departmental staff",
    },
    {
        number: "05",
        title: "The Coordinator assigns supervisors",
        description: "Verified students can be assigned to lecturers. The Coordinator can review supervision workloads and retain a record when an assignment changes.",
        owner: "Project Coordinator",
    },
    {
        number: "06",
        title: "Users access their role-based workspace",
        description: "Students can view their registration information, lecturers can view assigned students, and departmental administrators manage the records and assignments under their responsibility.",
        owner: "Students, lecturers and administrators",
    },
];

const questions = [
    {
        question: "What information should a student have before registering?",
        answer: "Students should use the matriculation number, names and contact details recorded by the department. Where details are present in the departmental register, they should match the registration form.",
    },
    {
        question: "What happens if a student's details do not match?",
        answer: "The registration is referred for staff review. The student should contact the department if their official record needs correction.",
    },
    {
        question: "Does registration automatically assign a supervisor?",
        answer: "No. The student must first be verified. The Project Coordinator then assigns a supervisor.",
    },
    {
        question: "Can academic sessions be managed without fixed dates?",
        answer: "Yes. The Project Coordinator controls session activation and closure manually, according to the department's operations.",
    },
    {
        question: "Is ProjFlow intended for multiple departments?",
        answer: "The current ProjFlow setup is designed for one academic department, with records maintained across academic sessions.",
    },
    {
        question: "Who should I contact if I cannot register?",
        answer: "Contact your department's Project Coordinator to confirm that your student record is present, eligible and up to date.",
    },
];

export default function HowItWorksPage() {
    return (
        <div className="public-page">
            <section className="public-page-hero">
                <div className="public-container public-page-hero-inner">
                    <div className="public-eyebrow">HOW PROJFLOW WORKS</div>
                    <h1>A clear process for students and the department.</h1>
                    <p>
                        ProjFlow starts with departmental setup and student onboarding, then brings lecturer
                        records and supervisor assignments into the same organised workspace.
                    </p>
                    <div className="public-page-actions">
                        <Link className="public-button public-button-primary" to="/register">Student registration <span aria-hidden="true">→</span></Link>
                        <Link className="public-text-link" to="/features">Explore features</Link>
                    </div>
                </div>
            </section>

            <section className="public-section public-section-white">
                <div className="public-container public-how-layout">
                    <div className="public-how-intro">
                        <div className="public-eyebrow">THE DEPARTMENTAL WORKFLOW</div>
                        <h2>Six steps to organise student onboarding and supervision.</h2>
                        <p>Each step has a clear owner, so students and staff know what happens next.</p>
                    </div>
                    <div className="public-how-steps">
                        {steps.map((step) => (
                            <article className="public-how-step" key={step.number}>
                                <div className="public-how-step-number">{step.number}</div>
                                <div className="public-how-step-body">
                                    <div className="public-how-step-owner">{step.owner}</div>
                                    <h3>{step.title}</h3>
                                    <p>{step.description}</p>
                                </div>
                            </article>
                        ))}
                    </div>
                </div>
            </section>

            <section className="public-section public-section-soft" id="faq">
                <div className="public-container public-faq-layout">
                    <div className="public-faq-intro">
                        <div className="public-eyebrow">FREQUENTLY ASKED QUESTIONS</div>
                        <h2>Questions about using ProjFlow.</h2>
                        <p>Information for students and departmental users getting started with the platform.</p>
                    </div>
                    <div className="public-faq-list">
                        {questions.map((item) => (
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
                        <div className="public-eyebrow public-eyebrow-light">NEED ACCESS?</div>
                        <h2>Continue to your ProjFlow workspace.</h2>
                        <p>Students can register with their departmental details. Existing users can sign in.</p>
                    </div>
                    <div className="public-cta-actions">
                        <Link className="public-button public-button-light" to="/register">Student registration <span aria-hidden="true">→</span></Link>
                        <Link className="public-cta-signin" to="/login">Sign in to ProjFlow</Link>
                    </div>
                </div>
            </section>
        </div>
    );
}

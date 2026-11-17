import { Link } from "react-router-dom";

const audiences = [
    { title: "Students", text: "Register with your academic details and keep track of your registration and assigned supervisor." },
    { title: "Lecturers", text: "View the students assigned to you and keep your supervision responsibilities organised." },
    { title: "Project Coordinators", text: "Manage academic sessions, departmental student records, lecturer accounts and supervisor assignments." },
];

export default function PlatformPage() {
    return (
        <section className="inner-page">
            <div className="inner-page-heading">
                <div className="eyebrow eyebrow-light">ABOUT PROJFLOW</div>
                <h1>One workspace for your department's final-year projects.</h1>
                <p>ProjFlow helps students, lecturers and project coordinators stay organised throughout the final-year project process.</p>
            </div>
            <div className="module-grid">
                {audiences.map((audience, index) => (
                    <article className="module-card" key={audience.title}>
                        <div className="module-card-head"><span className="module-index">{String(index + 1).padStart(2, "0")}</span></div>
                        <h2>{audience.title}</h2>
                        <p>{audience.text}</p>
                    </article>
                ))}
            </div>
            <div className="page-back-link"><Link to="/">← Back to overview</Link></div>
        </section>
    );
}

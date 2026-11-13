import { Link } from "react-router-dom";

const features = [
  { number: "01", title: "Project coordination", description: "A structured view of student projects, project cycles and departmental activity." },
  { number: "02", title: "Academic supervision", description: "Supervisor allocation, topic review, chapter submissions and documented feedback." },
  { number: "03", title: "Examination and assessment", description: "Flexible examination groups, panel assignments and transparent assessment records." },
];
const stages = [
  ["01", "Propose", "Topic submission and review"],
  ["02", "Develop", "Supervision and document progress"],
  ["03", "Submit", "Final project submission"],
  ["04", "Defend", "Panel examination and assessment"],
];

export default function HomePage() {
  return (
    <>
      <section className="hero-section">
        <div className="hero-grid">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-dot" />FINAL-YEAR PROJECT MANAGEMENT</div>
            <h1>A clearer way to manage <span>final-year projects.</span></h1>
            <p className="hero-description">ProjFlow brings project coordination, academic supervision, submissions and examination into one organised platform.</p>
            <div className="hero-actions">
              <Link className="button button-primary" to="/platform">Explore the platform <span aria-hidden="true">→</span></Link>
              <Link className="button button-secondary" to="/status">Check system status</Link>
            </div>
            <div className="hero-note"><span className="note-check">✓</span>Designed for clear academic workflows and accountable decisions.</div>
          </div>
          <div className="hero-visual" aria-label="Illustration of the project workflow">
            <div className="visual-orbit orbit-one" /><div className="visual-orbit orbit-two" />
            <div className="visual-card-main">
              <div className="visual-card-top"><span className="visual-kicker">PROJECT JOURNEY</span><span className="visual-menu">•••</span></div>
              <div className="visual-heading">From proposal to defence</div>
              <div className="visual-progress-track"><div className="visual-progress-fill" /></div>
              <div className="visual-progress-label"><span>Structured milestones</span><strong>4 stages</strong></div>
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
            <div className="floating-chip chip-top"><span className="chip-icon">↗</span><span><strong>One workflow</strong><small>Connected processes</small></span></div>
            <div className="floating-chip chip-bottom"><span className="chip-icon chip-icon-teal">✓</span><span><strong>Accountable</strong><small>Traceable decisions</small></span></div>
          </div>
        </div>
      </section>

      <section className="principles-strip">
        <div className="principles-inner">
          <span>BUILT AROUND FOUR PRINCIPLES</span>
          <div><b>01</b> Organisation</div><div><b>02</b> Accountability</div><div><b>03</b> Transparency</div><div><b>04</b> Progress</div>
        </div>
      </section>

      <section className="content-section">
        <div className="section-heading">
          <div><div className="eyebrow eyebrow-light">THE PLATFORM</div><h2>Every stage. One coordinated system.</h2></div>
          <p>A single departmental workspace designed to connect the people, decisions and records involved in final-year project management.</p>
        </div>
        <div className="feature-grid">
          {features.map((feature) => (
            <article className="feature-card" key={feature.number}>
              <div className="feature-card-top"><span className="feature-number">{feature.number}</span><span className="feature-arrow">↗</span></div>
              <h3>{feature.title}</h3><p>{feature.description}</p>
              <span className="feature-status"><span />In development</span>
            </article>
          ))}
        </div>
      </section>

      <section className="closing-section">
        <div className="closing-panel">
          <div>
            <div className="eyebrow eyebrow-on-dark">PROJFLOW 0.1.0</div>
            <h2>The foundation is online. The platform is taking shape.</h2>
            <p>This is the initial deployment of ProjFlow. Academic management modules will be introduced and verified in planned releases.</p>
          </div>
          <Link className="button button-light" to="/status">View deployment status <span aria-hidden="true">→</span></Link>
        </div>
      </section>
    </>
  );
}

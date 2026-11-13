import { Link } from "react-router-dom";

export default function BrandLogo({ compact = false }) {
  return (
    <Link className={`brand-link${compact ? " brand-link--compact" : ""}`} to="/" aria-label="ProjFlow home">
      <img className="brand-logo" src="/brand/projflow-logo-primary.svg" alt="ProjFlow — From Proposal to Final Defence" />
    </Link>
  );
}

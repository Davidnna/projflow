import { useCallback, useEffect, useState } from "react";
import { API_BASE_URL, checkPlatformStatus } from "../api.js";

function StatusValue({ value }) {
  const labels = {
    checking: "Checking", online: "Online", connected: "Connected",
    unavailable: "Unavailable", "not-configured": "Not configured", "not-checked": "Not checked",
  };
  const positive = value === "online" || value === "connected";
  const neutral = value === "checking" || value === "not-checked";
  return <span className={`status-value${positive ? " status-positive" : ""}${neutral ? " status-neutral" : ""}`}><span className="status-dot" />{labels[value] || value}</span>;
}

export default function StatusPage() {
  const [result, setResult] = useState({ configured: Boolean(API_BASE_URL), api: "checking", database: "checking" });
  const [loading, setLoading] = useState(false);
  const [lastChecked, setLastChecked] = useState(null);

  const runCheck = useCallback(async () => {
    setLoading(true);
    setResult({ configured: Boolean(API_BASE_URL), api: "checking", database: "checking" });
    try {
      setResult(await checkPlatformStatus());
    } catch {
      setResult({ configured: Boolean(API_BASE_URL), api: "unavailable", database: "unavailable" });
    } finally {
      setLastChecked(new Date());
      setLoading(false);
    }
  }, []);

  useEffect(() => { runCheck(); }, [runCheck]);

  return (
    <section className="inner-page status-page">
      <div className="inner-page-heading">
        <div className="eyebrow eyebrow-light">SERVICE MONITORING</div>
        <h1>System status</h1>
        <p>Check whether the ProjFlow API is responding and whether its PostgreSQL database is reachable.</p>
      </div>
      <div className="status-panel">
        <div className="status-panel-heading">
          <div><span className="status-panel-kicker">LIVE CHECK</span><h2>Platform services</h2></div>
          <button className="button button-secondary refresh-button" onClick={runCheck} disabled={loading}><span aria-hidden="true">↻</span>{loading ? "Checking…" : "Check again"}</button>
        </div>
        <div className="service-row">
          <div className="service-info"><span className="service-symbol">API</span><span><strong>ProjFlow API</strong><small>Django REST Framework</small></span></div>
          <StatusValue value={result.api} />
        </div>
        <div className="service-row">
          <div className="service-info"><span className="service-symbol service-symbol-db">DB</span><span><strong>Database</strong><small>Supabase PostgreSQL</small></span></div>
          <StatusValue value={result.database} />
        </div>
        {!result.configured && <div className="status-notice">The frontend has not yet been configured with the Render API address. Set <code>VITE_API_BASE_URL</code> in Cloudflare Pages after the backend has been deployed.</div>}
        <div className="status-panel-footer"><span>{lastChecked ? `Last checked: ${lastChecked.toLocaleTimeString()}` : "Waiting for first check"}</span><span>ProjFlow v0.1.0</span></div>
      </div>
      <div className="status-help">
        <strong>What do these checks mean?</strong>
        <p><b>API online</b> means the Django service is responding. <b>Database connected</b> means the API can execute a basic query against its configured database.</p>
        <p>A free hosting service may take time to wake after a period of inactivity. If the first check fails, wait briefly and check again.</p>
      </div>
    </section>
  );
}

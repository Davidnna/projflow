import { useEffect, useState } from "react";
import { apiRequest } from "../../api.js";
import { Alert, LoadingState, PageHeader } from "../../components/dashboard/WorkspaceUI.jsx";

const URL = "/api/projects/notifications/";
export default function NotificationsPage() {
    const [data, setData] = useState(null);
    const [preferences, setPreferences] = useState(null);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [busy, setBusy] = useState(false);
    async function load(body) {
        setBusy(true); setError(""); setSuccess("");
        try {
            const response = await apiRequest(URL, body ? { method: "POST", body } : {});
            setData(response); setPreferences(response.preferences);
            if (body) setSuccess("Saved successfully.");
        } catch (e) { setError(e.message); } finally { setBusy(false); }
    }
    useEffect(() => { load(); }, []);
    return <><PageHeader eyebrow="YOUR ACCOUNT" title="Notifications" description="Review academic updates and choose how you receive them." />
        {error && <Alert type="error">{error}</Alert>}{success && <Alert type="success">{success}</Alert>}
        {!data ? (busy ? <LoadingState /> : <button className="button button-secondary" onClick={() => load()}>Try again</button>) : <>
            <section className="surface-card completion-card"><div className="completion-heading"><h2>Inbox · {data.unread} unread</h2><button className="button button-secondary" disabled={busy || !data.unread} onClick={() => load({ action: "mark_read" })}>Mark all as read</button></div>{data.notifications.map((n) => <div className="completion-document" key={n.id}><div><strong>{n.message}</strong><small>{n.category} · {new Date(n.created_at).toLocaleString()} · {n.read_at ? "Read" : "Unread"}</small></div>{!n.read_at && <button disabled={busy} className="button button-secondary" onClick={() => load({ action: "mark_read", id: n.id })}>Mark read</button>}</div>)}{!data.notifications.length && <p>No notifications yet.</p>}</section>
            <section className="surface-card completion-card"><h2>Notification preferences</h2><p>Email delivery requires your department to configure its mail service. In-app notifications are available immediately.</p><table className="completion-table"><thead><tr><th>Category</th><th>In-app</th><th>Email</th></tr></thead><tbody>{Object.entries(preferences).map(([category, preference]) => <tr key={category}><td>{category}</td>{["in_app", "email"].map((channel) => <td key={channel}><input aria-label={`${category} ${channel}`} type="checkbox" checked={preference[channel]} onChange={(e) => setPreferences((p) => ({ ...p, [category]: { ...p[category], [channel]: e.target.checked } }))} /></td>)}</tr>)}</tbody></table><button disabled={busy} className="button button-primary" onClick={() => load({ action: "preferences", preferences })}>Save preferences</button></section>
        </>}
    </>;
}

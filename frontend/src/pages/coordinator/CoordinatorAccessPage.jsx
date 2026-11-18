import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext.jsx";
import { apiRequest, endpoints, getList } from "../../api.js";
import { Alert, EmptyState, LoadingState, PageHeader, StatusBadge } from "../../components/dashboard/WorkspaceUI.jsx";

export default function CoordinatorAccessPage() {
    const { user } = useAuth();
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const loadAccounts = useCallback(async () => {
        setLoading(true);
        try {
            setAccounts(getList(await apiRequest(endpoints.coordinatorAccess)));
            setError("");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadAccounts();
    }, [loadAccounts]);

    async function updateAccess(account) {
        const enabled = !account.has_coordinator_access;
        const action = enabled ? "grant Project Coordinator access to" : "remove Project Coordinator access from";
        if (!window.confirm(`Are you sure you want to ${action} ${account.name}?`)) {
            return;
        }
        setSavingId(account.id);
        setError("");
        setSuccess("");
        try {
            const result = await apiRequest(endpoints.coordinatorAccess, {
                method: "POST",
                body: { user_id: account.id, enabled },
            });
            setAccounts((current) => current.map((item) => (
                item.id === account.id ? result.account : item
            )));
            const isCurrentUser = account.id === user?.id;
            setSuccess(
                `${result.message} ${isCurrentUser ? "Sign out and sign in again to refresh your workspace access." : "The staff member should sign in again to use the updated access."}`
            );
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSavingId("");
        }
    }

    return (
        <>
            <PageHeader
                eyebrow="ACCOUNT ADMINISTRATION"
                title="Coordinator access"
                description="Manage which staff accounts can configure project milestones for academic sessions."
            />
            {error && <Alert type="error" onClose={() => setError("")}>{error}</Alert>}
            {success && <Alert type="success" onClose={() => setSuccess("")}>{success}</Alert>}
            <div className="info-callout">
                <span>i</span>
                <p>Project Coordinator access can be assigned to an Administrator or Lecturer. The role is separate from ordinary system administration and can be removed at any time.</p>
            </div>
            <section className="surface-card dashboard-table-card">
                <div className="surface-card-heading">
                    <div>
                        <span className="panel-eyebrow">STAFF ACCOUNTS</span>
                        <h2>Project Coordinator permissions <span className="heading-count">{accounts.filter((item) => item.has_coordinator_access).length}</span></h2>
                    </div>
                </div>
                {loading ? <LoadingState /> : accounts.length ? (
                    <div className="table-scroll">
                        <table className="data-table">
                            <thead>
                                <tr><th>Staff member</th><th>Account type</th><th>Coordinator access</th><th>Action</th></tr>
                            </thead>
                            <tbody>
                                {accounts.map((account) => {
                                    const accountType = account.roles.includes("administrator") ? "Administrator" : account.roles.includes("lecturer") ? "Lecturer" : "Project Coordinator";
                                    return (
                                        <tr key={account.id}>
                                            <td><strong>{account.name}</strong><small>{account.email}</small>{account.id === user?.id && <small className="table-muted">Your account</small>}</td>
                                            <td>{accountType}</td>
                                            <td><StatusBadge value={account.has_coordinator_access ? "active" : "inactive"}>{account.has_coordinator_access ? "Enabled" : "Not assigned"}</StatusBadge></td>
                                            <td>
                                                {account.can_receive_coordinator_access || account.has_coordinator_access ? (
                                                    <button
                                                        className={`table-action ${account.has_coordinator_access ? "table-action--danger" : "table-action--primary"}`}
                                                        onClick={() => updateAccess(account)}
                                                        disabled={savingId === account.id}
                                                    >
                                                        {savingId === account.id ? "Saving…" : account.has_coordinator_access ? "Remove access" : "Grant access"}
                                                    </button>
                                                ) : <span className="table-muted">Not eligible</span>}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <EmptyState title="No eligible staff accounts" description="Create an Administrator or Lecturer account before assigning Project Coordinator access." />
                )}
            </section>
        </>
    );
}

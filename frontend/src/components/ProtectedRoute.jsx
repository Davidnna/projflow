import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function ProtectedRoute({ roles }) {
    const { user, loading, hasAnyRole } = useAuth();
    const location = useLocation();

    if (loading) {
        return <div className="route-loading"><span className="loading-spinner" />Preparing your workspace…</div>;
    }
    if (!user) {
        return <Navigate to="/login" replace state={{ from: location }} />;
    }
    if (roles && !hasAnyRole(roles)) {
        return <Navigate to="/app/overview" replace />;
    }
    return <Outlet />;
}

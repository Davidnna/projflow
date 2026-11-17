import { Navigate, Route, Routes } from "react-router-dom";
import SiteLayout from "./components/SiteLayout.jsx";
import DashboardLayout from "./components/dashboard/DashboardLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import HomePage from "./pages/HomePage.jsx";
import PlatformPage from "./pages/PlatformPage.jsx";
import LoginPage from "./pages/auth/LoginPage.jsx";
import RegisterPage from "./pages/auth/RegisterPage.jsx";
import DashboardOverview from "./pages/dashboard/DashboardOverview.jsx";
import SessionsPage from "./pages/coordinator/SessionsPage.jsx";
import StudentsPage from "./pages/coordinator/StudentsPage.jsx";
import RegistrationsPage from "./pages/coordinator/RegistrationsPage.jsx";
import LecturersPage from "./pages/coordinator/LecturersPage.jsx";
import SupervisorsPage from "./pages/coordinator/SupervisorsPage.jsx";

const coordinatorRoles = ["administrator", "project_coordinator"];

export default function App() {
    return (
        <Routes>
            <Route element={<SiteLayout />}>
                <Route path="/" element={<HomePage />} />
                <Route path="/platform" element={<PlatformPage />} />
            </Route>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/setup/administrator" element={<Navigate to="/login" replace />} />
            <Route path="/status" element={<Navigate to="/" replace />} />
            <Route element={<ProtectedRoute />}>
                <Route path="/app" element={<DashboardLayout />}>
                    <Route index element={<Navigate to="/app/overview" replace />} />
                    <Route path="overview" element={<DashboardOverview />} />
                    <Route element={<ProtectedRoute roles={coordinatorRoles} />}>
                        <Route path="sessions" element={<SessionsPage />} />
                        <Route path="students" element={<StudentsPage />} />
                        <Route path="registrations" element={<RegistrationsPage />} />
                        <Route path="lecturers" element={<LecturersPage />} />
                        <Route path="supervisors" element={<SupervisorsPage />} />
                    </Route>
                </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}

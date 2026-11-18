import { Navigate, Route, Routes } from "react-router-dom";
import SiteLayout from "./components/SiteLayout.jsx";
import DashboardLayout from "./components/dashboard/DashboardLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import HomePage from "./pages/HomePage.jsx";
import PlatformPage from "./pages/PlatformPage.jsx";
import FeaturesPage from "./pages/FeaturesPage.jsx";
import HowItWorksPage from "./pages/HowItWorksPage.jsx";
import LoginPage from "./pages/auth/LoginPage.jsx";
import RegisterPage from "./pages/auth/RegisterPage.jsx";
import DashboardOverview from "./pages/dashboard/DashboardOverview.jsx";
import SessionsPage from "./pages/coordinator/SessionsPage.jsx";
import StudentsPage from "./pages/coordinator/StudentsPage.jsx";
import RegistrationsPage from "./pages/coordinator/RegistrationsPage.jsx";
import LecturersPage from "./pages/coordinator/LecturersPage.jsx";
import SupervisorsPage from "./pages/coordinator/SupervisorsPage.jsx";
import ProjectTopicPage from "./pages/student/ProjectTopicPage.jsx";
import TopicReviewPage from "./pages/lecturer/TopicReviewPage.jsx";
import ProgressReviewPage from "./pages/lecturer/ProgressReviewPage.jsx";
import MilestonesPage from "./pages/coordinator/MilestonesPage.jsx";
import ProgressPage from "./pages/student/ProgressPage.jsx";

const coordinatorRoles = ["administrator", "project_coordinator"];

export default function App() {
    return (
        <Routes>
            <Route element={<SiteLayout />}>
                <Route path="/" element={<HomePage />} />
                <Route path="/about" element={<PlatformPage />} />
                <Route path="/platform" element={<Navigate to="/about" replace />} />
                <Route path="/features" element={<FeaturesPage />} />
                <Route path="/how-it-works" element={<HowItWorksPage />} />
            </Route>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/setup/administrator" element={<Navigate to="/login" replace />} />
            <Route path="/status" element={<Navigate to="/" replace />} />
            <Route element={<ProtectedRoute />}>
                <Route path="/app" element={<DashboardLayout />}>
                    <Route index element={<Navigate to="/app/overview" replace />} />
                    <Route path="overview" element={<DashboardOverview />} />
                    <Route element={<ProtectedRoute roles={["student"]} />}>
                        <Route path="topics" element={<ProjectTopicPage />} />
                    </Route>
                    <Route element={<ProtectedRoute roles={["lecturer"]} />}>
                        <Route path="topics/review" element={<TopicReviewPage />} />
                        <Route path="progress" element={<ProgressReviewPage />} />
                    </Route>
                    <Route element={<ProtectedRoute roles={["student"]} />}>
                        <Route path="my-progress" element={<ProgressPage />} />
                    </Route>
                    <Route element={<ProtectedRoute roles={["project_coordinator"]} />}>
                        <Route path="milestones" element={<MilestonesPage />} />
                    </Route>
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

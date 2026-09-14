import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { AppLayout } from "./layouts/AppLayout";
import { LandingPage } from "./pages/LandingPage";
import { EventsPage } from "./pages/EventsPage";
import { EventDetailsPage } from "./pages/EventDetailsPage";
import { MyRegistrationsPage } from "./pages/MyRegistrationsPage";
import { AdminEventsPage } from "./pages/AdminEventsPage";
import { AdminAttendeesPage } from "./pages/AdminAttendeesPage";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AdminReportsPage } from "./pages/AdminReportsPage";
import { AdminRegistrationRequestsPage } from "./pages/AdminRegistrationRequestsPage";
import { SignInPage } from "./pages/SignInPage";
import { SignUpPage } from "./pages/SignUpPage";

export default function App() {
  return <BrowserRouter><AuthProvider><Routes>
    <Route path="/" element={<LandingPage />} />
    <Route path="/sign-in" element={<SignInPage />} />
    <Route path="/sign-up" element={<SignUpPage />} />
    <Route element={<ProtectedRoute allowedRole="attendee" />}><Route element={<AppLayout />}>
      <Route path="/events" element={<EventsPage />} />
      <Route path="/events/:eventId" element={<EventDetailsPage />} />
      <Route path="/my-registrations" element={<MyRegistrationsPage />} />
    </Route></Route>
    <Route element={<ProtectedRoute allowedRole="admin" />}><Route element={<AppLayout />}>
      <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
      <Route path="/admin/events" element={<AdminEventsPage />} />
      <Route path="/admin/events/:eventId/attendees" element={<AdminAttendeesPage />} />
      <Route path="/admin/reports" element={<AdminReportsPage />} />
      <Route path="/admin/registration-requests" element={<AdminRegistrationRequestsPage />} />
    </Route></Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></AuthProvider></BrowserRouter>;
}

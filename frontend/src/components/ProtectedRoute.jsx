import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function ProtectedRoute({ allowedRole }) {
  const { session, profile, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="page-loader" role="status">Loading your account…</div>;
  if (!session || !profile) return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  if (allowedRole && profile.role !== allowedRole) {
    return <Navigate to={profile.role === "admin" ? "/admin/dashboard" : "/events"} replace />;
  }
  return <Outlet />;
}

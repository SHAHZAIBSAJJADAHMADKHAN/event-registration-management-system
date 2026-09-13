import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const linksFor = (role) => role === "admin"
  ? [["/admin/dashboard", "Dashboard"], ["/admin/events", "Events"], ["/admin/reports", "Reports"]]
  : [["/events", "Events"], ["/my-registrations", "My registrations"]];

export function AppLayout() {
  const { profile, signOut } = useAuth();
  const navigate = useNavigate();
  const links = linksFor(profile.role);
  const handleSignOut = async () => { await signOut(); navigate("/sign-in", { replace: true }); };
  return <div className="app-shell">
    <header className="app-header">
      <NavLink className="brand" to={profile.role === "admin" ? "/admin/dashboard" : "/events"}>N<span>•</span> Events</NavLink>
      <nav aria-label="Primary navigation">{links.map(([path, label]) => <NavLink key={path} to={path}>{label}</NavLink>)}</nav>
      <div className="account-menu">
        <span className="account-name">{profile.full_name}</span>
        <span className="role-badge">{profile.role}</span>
        <button className="button button--text" onClick={handleSignOut}>Sign out</button>
      </div>
    </header>
    <main className="app-content"><Outlet /></main>
  </div>;
}

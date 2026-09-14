import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminDashboard, getAdminRegistrationRequests } from "../services/api";
import { useApi } from "../hooks/useApi";
import { AsyncState } from "../components/AsyncState";

export function AdminDashboardPage() {
  const call = useApi();
  const [data, setData] = useState(null);
  const [pending, setPending] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => { Promise.all([call(getAdminDashboard), call((token) => getAdminRegistrationRequests({ status: "pending" }, token))]).then(([dashboard, requests]) => { setData(dashboard); setPending(requests); }).catch((e) => setError(e.message)); }, [call]);
  return <section><div className="section-heading"><p className="eyebrow">Administration</p><h1>Operational dashboard</h1><p>Live totals from your event operations.</p></div><AsyncState loading={!data && !error} error={error}>{data && <><div className="metric-grid"><article><span>Total events</span><strong>{data.total_events}</strong></article><article><span>Total registrations</span><strong>{data.total_registrations}</strong></article><article><span>Available capacity</span><strong>{data.available_capacity}</strong></article><article><span>Active registrations</span><strong>{data.active_registrations}</strong></article></div><div className="dashboard-pending"><div><p className="eyebrow">Pending registration requests</p><h2>{pending.length} awaiting review</h2><p>Recent attendee requests requiring an event decision.</p></div><Link className="button button--secondary" to="/admin/registration-requests">View all requests</Link>{pending.length > 0 && <ul>{pending.slice(0, 5).map((request) => <li key={request.registration_id}><strong>{request.attendee_name || "Unnamed attendee"}</strong><span>{request.event_title || "Untitled event"} · {request.created_at ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(request.created_at)) : "Requested recently"}</span></li>)}</ul>}</div>{data.total_events === 0 && <div className="state-card">No events have been created yet. Create an event to begin tracking operations.</div>}</>}</AsyncState></section>;
}

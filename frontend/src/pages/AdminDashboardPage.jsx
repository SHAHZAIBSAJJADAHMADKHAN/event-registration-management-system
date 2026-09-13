import { useEffect, useState } from "react";
import { getAdminDashboard } from "../services/api";
import { useApi } from "../hooks/useApi";
import { AsyncState } from "../components/AsyncState";

export function AdminDashboardPage() {
  const call = useApi();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { call(getAdminDashboard).then(setData).catch((e) => setError(e.message)); }, [call]);
  return <section><div className="section-heading"><p className="eyebrow">Administration</p><h1>Operational dashboard</h1><p>Live totals from your event operations.</p></div><AsyncState loading={!data && !error} error={error}>{data && <><div className="metric-grid"><article><span>Total events</span><strong>{data.total_events}</strong></article><article><span>Total registrations</span><strong>{data.total_registrations}</strong></article><article><span>Available capacity</span><strong>{data.available_capacity}</strong></article><article><span>Active registrations</span><strong>{data.active_registrations}</strong></article></div>{data.total_events === 0 && <div className="state-card">No events have been created yet. Create an event to begin tracking operations.</div>}</>}</AsyncState></section>;
}

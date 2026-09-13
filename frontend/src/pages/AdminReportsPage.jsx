import { useEffect, useMemo, useState } from "react";
import { getAdminEventReport } from "../services/api";
import { useApi } from "../hooks/useApi";
import { AsyncState } from "../components/AsyncState";

const fmt = (date) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(date));
const csvValue = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
const exportRows = (rows) => {
  const header = ["Event", "Date and time", "Status", "Location", "Capacity", "Active registrations", "Cancelled registrations", "Remaining capacity"];
  const content = [header, ...rows.map((row) => [row.event_title, row.starts_at, row.status, row.location, row.capacity, row.active_registrations, row.cancelled_registrations, row.remaining_availability])].map((row) => row.map(csvValue).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a"); link.href = url; link.download = "nowshera-events-report.csv"; link.click(); URL.revokeObjectURL(url);
};

export function AdminReportsPage() {
  const call = useApi();
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  useEffect(() => { call(getAdminEventReport).then(setRows).catch((e) => setError(e.message)); }, [call]);
  const filtered = useMemo(() => (rows || []).filter((row) => row.event_title.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()) && (status === "all" || row.status === status)), [rows, search, status]);
  return <section><div className="section-heading"><p className="eyebrow">Administration</p><h1>Event reports</h1><p>Operational capacity and registration figures by event.</p></div><AsyncState loading={!rows && !error} error={error}>{rows && <><div className="report-controls"><label>Search events<input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Event title" /></label><label>Event status<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">All statuses</option><option value="draft">Draft</option><option value="published">Published</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></label><button className="button" onClick={() => exportRows(filtered)} disabled={filtered.length === 0}>Export CSV</button></div>{rows.length === 0 ? <div className="state-card">No event report data is available yet.</div> : filtered.length === 0 ? <div className="state-card">No events match this search or status filter.</div> : <div className="attendee-table-wrap"><table className="attendee-table"><caption className="sr-only">Operational event report</caption><thead><tr><th>Event</th><th>Status</th><th>Capacity</th><th>Registrations</th><th>Remaining</th></tr></thead><tbody>{filtered.map((row) => <tr key={row.event_id}><td data-label="Event"><strong>{row.event_title}</strong><span>{fmt(row.starts_at)} · {row.location}</span></td><td data-label="Status"><span className={`status-badge ${row.status}`}>{row.status}</span></td><td data-label="Capacity">{row.capacity}</td><td data-label="Registrations">{row.active_registrations} active · {row.cancelled_registrations} cancelled</td><td data-label="Remaining">{row.remaining_availability}</td></tr>)}</tbody></table></div>}</>}</AsyncState></section>;
}

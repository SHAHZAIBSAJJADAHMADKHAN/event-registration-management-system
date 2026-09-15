import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getAdminEventDetailedReport } from "../services/api";
import { useApi } from "../hooks/useApi";
import { AsyncState } from "../components/AsyncState";
import { createEventReportCsv, createEventReportPdf, downloadExport } from "../utils/eventReportExports";

const fmt = (date) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(date));
const labels = { all: "All", approved: "Approved", pending: "Pending", rejected: "Rejected", cancelled: "Cancelled" };

export function AdminEventReportPage() {
  const { eventId } = useParams(); const call = useApi();
  const [report, setReport] = useState(null); const [error, setError] = useState(""); const [filter, setFilter] = useState("all");
  useEffect(() => { setReport(null); setError(""); call((token) => getAdminEventDetailedReport(eventId, token)).then(setReport).catch((e) => setError(e.message)); }, [call, eventId]);
  const rows = useMemo(() => report?.registrations.filter((row) => filter === "all" || row.registration_status === filter) || [], [report, filter]);
  const filename = `event-${eventId}-${filter}`;
  return <section className="attendee-page"><Link className="back-link" to="/admin/reports">← Event reports</Link><div className="section-heading"><p className="eyebrow">Administration</p><h1>{report?.event_title || "Event registration report"}</h1>{report && <p className="lead">{fmt(report.starts_at)} · {report.location}</p>}</div><AsyncState loading={!report && !error} error={error}>{report && <><div className="attendee-summary" aria-label="Event report information"><div><span>Status</span><strong>{report.status}</strong></div><div><span>Capacity</span><strong>{report.capacity}</strong></div><div><span>Remaining</span><strong>{report.remaining_availability}</strong></div></div><div className="report-summary" aria-label="Registration summary">{["approved", "pending", "rejected", "cancelled"].map((status) => <div key={status}><span>{labels[status]}</span><strong>{report.registration_counts[status]}</strong></div>)}</div><div className="report-controls"><label>Registration status<select value={filter} onChange={(e) => setFilter(e.target.value)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><button className="button" onClick={() => downloadExport(createEventReportPdf(report, rows, filter), `${filename}.pdf`)}>Download PDF</button><button className="button" onClick={() => downloadExport(createEventReportCsv(report, rows, filter), `${filename}.csv`)}>Export CSV</button></div>{rows.length === 0 ? <div className="state-card">No {filter === "all" ? "" : `${labels[filter].toLocaleLowerCase()} `}registrations for this event.</div> : <div className="attendee-table-wrap"><table className="attendee-table"><caption className="sr-only">{labels[filter]} registrations for {report.event_title}</caption><thead><tr><th>Attendee</th><th>Status</th><th>Requested</th></tr></thead><tbody>{rows.map((row) => <tr key={row.registration_id}><td data-label="Attendee"><strong>{row.attendee_name || "Unnamed attendee"}</strong>{row.attendee_email && <span>{row.attendee_email}</span>}</td><td data-label="Status"><span className={`status-badge ${row.registration_status}`}>{row.registration_status}</span></td><td data-label="Requested">{fmt(row.registered_at)}</td></tr>)}</tbody></table></div>}</>}</AsyncState></section>;
}

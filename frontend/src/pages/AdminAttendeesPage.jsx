import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getAdminEvent, getAdminEventAttendees, getAdminEventSummary } from "../services/api";
import { useApi } from "../hooks/useApi";
import { AsyncState } from "../components/AsyncState";

const fmt = (date) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(date));

export function AdminAttendeesPage() {
  const { eventId } = useParams();
  const call = useApi();
  const [event, setEvent] = useState(null);
  const [summary, setSummary] = useState(null);
  const [attendees, setAttendees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  useEffect(() => {
    setLoading(true); setError("");
    Promise.all([call((token) => getAdminEvent(eventId, token)), call((token) => getAdminEventSummary(eventId, token)), call((token) => getAdminEventAttendees(eventId, token))])
      .then(([eventData, summaryData, attendeeData]) => { setEvent(eventData); setSummary(summaryData); setAttendees(attendeeData); })
      .catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [call, eventId]);
  const filtered = useMemo(() => attendees.filter((row) => {
    const haystack = `${row.attendee_name || ""} ${row.attendee_email || ""}`.toLocaleLowerCase();
    return (status === "all" || row.registration_status === status) && haystack.includes(search.trim().toLocaleLowerCase());
  }), [attendees, search, status]);
  return <section className="attendee-page"><Link className="back-link" to="/admin/events">← Event management</Link><div className="section-heading"><p className="eyebrow">Check-in list</p><h1>{event?.title || "Event attendees"}</h1>{event && <p className="lead">{fmt(event.starts_at)} · {event.location}</p>}</div><AsyncState loading={loading} error={error}><>{event && summary && <div className="attendee-summary" aria-label="Event capacity summary"><div><span>Capacity</span><strong>{summary.capacity}</strong></div><div><span>Active registrations</span><strong>{summary.active_registrations}</strong></div><div><span>Remaining capacity</span><strong>{summary.remaining_availability}</strong></div></div>}<div className="attendee-controls"><label>Search attendees<input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name or email" /></label><label>Registration status<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">All</option><option value="approved">Approved</option><option value="cancelled">Cancelled</option></select></label></div>{attendees.length === 0 ? <div className="state-card">No registrations yet.</div> : filtered.length === 0 ? <div className="state-card">No attendees match this search or filter.</div> : <div className="attendee-table-wrap"><table className="attendee-table"><caption className="sr-only">Attendees registered for {event?.title}</caption><thead><tr><th scope="col">Attendee</th><th scope="col">Registration status</th><th scope="col">Registered</th></tr></thead><tbody>{filtered.map((row) => <tr key={row.registration_id}><td data-label="Attendee"><strong>{row.attendee_name || "Unnamed attendee"}</strong>{row.attendee_email && <span>{row.attendee_email}</span>}</td><td data-label="Registration status"><span className={`status-badge ${row.registration_status}`}>{row.registration_status}</span></td><td data-label="Registered">{fmt(row.registered_at)}</td></tr>)}</tbody></table></div>}</></AsyncState></section>;
}

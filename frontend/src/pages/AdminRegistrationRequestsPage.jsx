import { useCallback, useEffect, useMemo, useState } from "react";
import { approveRegistrationRequest, getAdminRegistrationRequests, rejectRegistrationRequest } from "../services/api";
import { useApi } from "../hooks/useApi";
import { AsyncState } from "../components/AsyncState";

const statuses = ["all", "pending", "approved", "rejected", "cancelled"];
const labels = { all: "All", pending: "Pending", approved: "Approved", rejected: "Rejected", cancelled: "Cancelled" };
const emptyCopy = {
  all: "No registration requests have been received yet.",
  pending: "No registration requests are waiting for review.",
  approved: "No approved registration requests yet.",
  rejected: "No rejected requests.",
  cancelled: "No cancelled registration requests.",
};
const formatDate = (value) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
const actionError = (error) => ({
  event_full: "This event has reached its capacity. This request cannot be approved.",
  registration_not_pending: "This request has already been processed.",
  request_not_pending: "This request has already been processed.",
  event_unavailable: "This event is no longer accepting registrations.",
  event_not_eligible: "This event is no longer accepting registrations.",
  registration_not_found: "This registration request could not be found.",
  http_403: "You do not have permission to perform this action.",
}[error.code] || "We could not update this registration request. Please try again.");

export function AdminRegistrationRequestsPage() {
  const call = useApi();
  const [filter, setFilter] = useState("pending");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [processingId, setProcessingId] = useState("");
  const load = useCallback(async (nextFilter = filter) => {
    setLoading(true); setError("");
    try {
      const data = nextFilter === "all"
        ? (await Promise.all(statuses.slice(1).map((status) => call((token) => getAdminRegistrationRequests({ status }, token)))).then((results) => results.flat()))
        : await call((token) => getAdminRegistrationRequests({ status: nextFilter }, token));
      setRows(data);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  }, [call, filter]);
  useEffect(() => { load(filter); }, [filter, load]);
  const visibleRows = useMemo(() => {
    const term = search.trim().toLocaleLowerCase();
    if (!term) return rows;
    return rows.filter((row) => `${row.attendee_name || ""} ${row.attendee_email || ""} ${row.event_title || ""}`.toLocaleLowerCase().includes(term));
  }, [rows, search]);
  const decide = async (row, decision) => {
    if (decision === "reject" && !window.confirm(`Reject ${row.attendee_name || "this attendee"}'s request for ${row.event_title || "this event"}?`)) return;
    setProcessingId(row.registration_id); setError(""); setNotice("");
    try {
      await call((token) => (decision === "approve" ? approveRegistrationRequest : rejectRegistrationRequest)(row.registration_id, token));
      setNotice(decision === "approve" ? "Registration request approved." : "Registration request rejected.");
      await load(filter);
    } catch (requestError) { setError(actionError(requestError)); }
    finally { setProcessingId(""); }
  };
  return <section className="registration-requests-page">
    <div className="section-heading"><p className="eyebrow">Event operations</p><h1>Registration requests</h1><p>Review attendee requests and manage event approvals.</p></div>
    <div className="request-toolbar"><div className="pending-indicator"><span>Pending</span><strong>{filter === "pending" ? rows.length : "—"}</strong></div><label className="request-search">Search requests<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Attendee, email, or event" /></label></div>
    <div className="request-filters" role="tablist" aria-label="Registration request status filters">{statuses.map((status) => <button key={status} className={filter === status ? "active" : ""} role="tab" aria-selected={filter === status} onClick={() => { setFilter(status); setNotice(""); }}>{labels[status]}</button>)}</div>
    {error && <p className="message" role="alert">{error}</p>}{notice && <p className="message message--success" role="status">{notice}</p>}
    <AsyncState loading={loading} error=""><>{!loading && (rows.length === 0 ? <div className="state-card">{emptyCopy[filter]}</div> : visibleRows.length === 0 ? <div className="state-card">No registration requests match this search.</div> : <div className="request-table-wrap"><table className="request-table"><caption className="sr-only">{labels[filter]} registration requests</caption><thead><tr><th scope="col">Attendee</th><th scope="col">Event</th><th scope="col">Event date</th><th scope="col">Requested</th><th scope="col">Status</th><th scope="col">Actions</th></tr></thead><tbody>{visibleRows.map((row) => { const pending = row.status === "pending"; const processing = processingId === row.registration_id; return <tr key={row.registration_id}><td data-label="Attendee"><strong>{row.attendee_name || "Unnamed attendee"}</strong>{row.attendee_email && <span>{row.attendee_email}</span>}</td><td data-label="Event">{row.event_title || "Untitled event"}</td><td data-label="Event date">{formatDate(row.event_starts_at)}</td><td data-label="Requested">{formatDate(row.created_at)}</td><td data-label="Status"><span className={`status-badge ${row.status}`}>{row.status === "pending" ? "Pending approval" : labels[row.status] || row.status}</span></td><td data-label="Actions">{pending ? <div className="request-actions"><button className="button" disabled={processing} onClick={() => decide(row, "approve")}>{processing ? "Processing…" : "Approve"}</button><button className="button button--danger" disabled={processing} onClick={() => decide(row, "reject")}>Reject</button></div> : <span className="muted">No action needed</span>}</td></tr>; })}</tbody></table></div>)}</></AsyncState>
  </section>;
}

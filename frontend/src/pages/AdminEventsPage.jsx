import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createAdminEvent, deleteAdminEvent, getAdminEvents, transitionAdminEvent, updateAdminEvent } from "../services/api";
import { useApi } from "../hooks/useApi";
import { AsyncState } from "../components/AsyncState";

const blank = { title: "", description: "", starts_at: "", location: "", capacity: "", status: "draft" };
const fmt = (date) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(date));

export function AdminEventsPage() {
  const call = useApi();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState(blank);
  const [editing, setEditing] = useState(null);
  const load = () => { setLoading(true); call(getAdminEvents).then(setEvents).catch((e) => setError(e.message)).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, [call]);
  const move = (id, status) => { if (status === "cancelled" && !window.confirm("Cancel this event?")) return; call((token) => transitionAdminEvent(id, status, token)).then(load).catch((e) => setError(e.message)); };
  const remove = (item) => { const publishedWarning = item.status === "published" ? " This event is currently published. Existing attendee registrations will also be permanently removed." : ""; if (!window.confirm(`Delete "${item.title}"? This permanently deletes the event and all associated registration records and related notifications. This action cannot be undone.${publishedWarning}`)) return; call((token) => deleteAdminEvent(item.id, token)).then(load).catch((e) => setError(e.message)); };
  const submit = async (event) => {
    event.preventDefault();
    if (!form.title || !form.description || !form.starts_at || !form.location || !Number.isInteger(+form.capacity) || +form.capacity < 1) return setError("Complete all fields; capacity must be a positive whole number.");
    const payload = { title: form.title, description: form.description, starts_at: new Date(form.starts_at).toISOString(), location: form.location, capacity: +form.capacity };
    try { if (editing) await call((token) => updateAdminEvent(editing, payload, token)); else await call((token) => createAdminEvent({ ...payload, status: form.status }, token)); setForm(blank); setEditing(null); load(); } catch (e) { setError(e.message); }
  };
  return <section><div className="section-heading"><p className="eyebrow">Administration</p><h1>Event management</h1></div>{error && <p className="message message--error">{error}</p>}<form onSubmit={submit}><h2>{editing ? "Edit event" : "Create event"}</h2><label>Title<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label><label>Description<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label><label>Date and time<input type="datetime-local" value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })} /></label><label>Location<input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} /></label><label>Capacity<input type="number" min="1" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} /></label><label>Status<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option>draft</option><option>published</option></select></label><button className="button">{editing ? "Save changes" : "Create event"}</button></form><AsyncState loading={loading} error="" empty={events.length === 0 ? "No events have been created yet." : null}><div className="registration-list">{events.map((item) => <article className="registration-card" key={item.id}><div><span className="status-badge">{item.status}</span><h2>{item.title}</h2><p>{fmt(item.starts_at)} · {item.location} · Capacity {item.capacity}</p></div><div className="event-actions"><Link className="button button--secondary" to={`/admin/events/${item.id}/attendees`}>View attendees</Link><button className="button button--secondary" onClick={() => { setEditing(item.id); setForm({ ...item, starts_at: new Date(item.starts_at).toISOString().slice(0, 16), capacity: String(item.capacity) }); }}>Edit</button>{item.status === "draft" && <button className="button" onClick={() => move(item.id, "published")}>Publish</button>}{["draft", "published"].includes(item.status) && <button className="button button--secondary" onClick={() => move(item.id, "cancelled")}>Cancel</button>}{item.status === "published" && <button className="button button--secondary" onClick={() => move(item.id, "completed")}>Complete</button>}<button className="button button--danger" onClick={() => remove(item)}>Delete</button></div></article>)}</div></AsyncState></section>;
}

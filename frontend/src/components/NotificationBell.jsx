import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getNotifications, getUnreadNotificationCount, markAllNotificationsRead, markNotificationRead } from "../services/api";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../context/AuthContext";

const relativeTime = (value) => {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
};
const destinationFor = (notification, role) => {
  if (role === "admin" && notification.type === "new_registration_request") return "/admin/registration-requests";
  if (role === "attendee" && ["registration_request_submitted", "registration_approved", "registration_rejected", "registration_cancelled"].includes(notification.type)) return "/my-registrations";
  return null;
};

export function NotificationBell() {
  const call = useApi();
  const { profile } = useAuth();
  const navigate = useNavigate();
  const root = useRef(null);
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [updating, setUpdating] = useState(false);
  const refreshCount = useCallback(async () => {
    try { const result = await call(getUnreadNotificationCount); setCount(Math.max(0, result.unread_count || 0)); } catch { /* Notification failures must not affect navigation. */ }
  }, [call]);
  const loadNotifications = useCallback(async () => {
    setLoading(true); setError(false);
    try {
      const [items, unread] = await Promise.all([call(getNotifications), call(getUnreadNotificationCount)]);
      setNotifications(items); setCount(Math.max(0, unread.unread_count || 0));
    } catch { setError(true); }
    finally { setLoading(false); }
  }, [call]);
  useEffect(() => { refreshCount(); }, [refreshCount]);
  useEffect(() => {
    const closeOnOutsideClick = (event) => { if (root.current && !root.current.contains(event.target)) setOpen(false); };
    const closeOnEscape = (event) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", closeOnOutsideClick); document.addEventListener("keydown", closeOnEscape);
    return () => { document.removeEventListener("mousedown", closeOnOutsideClick); document.removeEventListener("keydown", closeOnEscape); };
  }, []);
  const toggle = () => { const next = !open; setOpen(next); if (next) loadNotifications(); };
  const openNotification = async (notification) => {
    if (!notification.is_read) {
      setUpdating(true);
      try {
        await call((token) => markNotificationRead(notification.id, token));
        setNotifications((items) => items.map((item) => item.id === notification.id ? { ...item, is_read: true } : item));
        setCount((current) => Math.max(0, current - 1));
      } catch { setError(true); }
      finally { setUpdating(false); }
    }
    const destination = destinationFor(notification, profile.role);
    if (destination) navigate(destination);
    setOpen(false);
  };
  const markAll = async () => {
    setUpdating(true); setError(false);
    try { await call(markAllNotificationsRead); setNotifications((items) => items.map((item) => ({ ...item, is_read: true }))); setCount(0); }
    catch { setError(true); }
    finally { setUpdating(false); }
  };
  return <div className="notification-bell" ref={root}>
    <button className="notification-trigger" type="button" aria-label={count ? `Notifications, ${count} unread` : "Notifications"} aria-expanded={open} aria-haspopup="dialog" onClick={toggle}>
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" strokeLinecap="round" strokeLinejoin="round" /></svg>
      {count > 0 && <span className="notification-count" aria-hidden="true">{count > 99 ? "99+" : count}</span>}
    </button>
    {open && <section className="notification-panel" role="dialog" aria-label="Notifications"><header><div><h2>Notifications</h2><p>{count ? `${count} unread` : "All caught up"}</p></div>{count > 0 && <button className="button button--text" type="button" disabled={updating} onClick={markAll}>Mark all as read</button>}</header><div className="notification-list">{loading ? <p className="notification-state" role="status">Loading notifications…</p> : error ? <div className="notification-state"><p>Notifications could not be loaded.</p><button className="button button--secondary" type="button" onClick={loadNotifications}>Retry</button></div> : notifications.length === 0 ? <p className="notification-state">No notifications yet.</p> : notifications.map((notification) => <button key={notification.id} className={`notification-item ${notification.is_read ? "is-read" : "is-unread"}`} type="button" disabled={updating} onClick={() => openNotification(notification)}><span className="notification-unread" aria-hidden="true" /><span><strong>{notification.title}</strong><span>{notification.message}</span><time dateTime={notification.created_at}>{relativeTime(notification.created_at)}</time>{!notification.is_read && <em className="sr-only">Unread</em>}</span></button>)}</div></section>}
  </div>;
}

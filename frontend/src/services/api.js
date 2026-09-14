const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export class ApiClientError extends Error {
  constructor(message, { status = 0, code = "network_error", details = null } = {}) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export async function apiRequest(path, { accessToken, method = "GET", body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch {
    throw new ApiClientError("Unable to reach the service. Please try again.");
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    const detail = payload?.error || payload?.detail;
    throw new ApiClientError(
      detail?.message || "The request could not be completed.",
      { status: response.status, code: detail?.code || `http_${response.status}`, details: detail },
    );
  }
  return payload;
}

export const getCurrentProfile = (accessToken) => apiRequest("/auth/me", { accessToken });
export const getEvents = (accessToken) => apiRequest("/events", { accessToken });
export const getEvent = (id, accessToken) => apiRequest(`/events/${id}`, { accessToken });
export const registerForEvent = (id, accessToken) => apiRequest(`/events/${id}/registrations`, { accessToken, method: "POST" });
export const getMyEventRegistration = (id, accessToken) => apiRequest(`/events/${id}/my-registration`, { accessToken });
export const getMyRegistrations = (accessToken) => apiRequest("/me/registrations", { accessToken });
export const cancelRegistration = (id, accessToken) => apiRequest(`/me/registrations/${id}/cancel`, { accessToken, method: "PATCH" });
export const getNotifications = (accessToken) => apiRequest("/me/notifications", { accessToken });
export const getUnreadNotificationCount = (accessToken) => apiRequest("/me/notifications/unread-count", { accessToken });
export const markNotificationRead = (id, accessToken) => apiRequest(`/me/notifications/${id}/read`, { accessToken, method: "PATCH" });
export const markAllNotificationsRead = (accessToken) => apiRequest("/me/notifications/read-all", { accessToken, method: "PATCH" });
export const getAdminEvents = (accessToken) => apiRequest("/admin/events", { accessToken });
export const getAdminEvent = (id, accessToken) => apiRequest(`/admin/events/${id}`, { accessToken });
export const createAdminEvent = (data, accessToken) => apiRequest("/admin/events", { accessToken, method:"POST", body:data });
export const updateAdminEvent = (id,data,accessToken) => apiRequest(`/admin/events/${id}`, {accessToken,method:"PATCH",body:data});
export const deleteAdminEvent = (id, accessToken) => apiRequest(`/admin/events/${id}`, { accessToken, method: "DELETE" });
export const transitionAdminEvent = (id,status,accessToken) => apiRequest(`/admin/events/${id}/status`, {accessToken,method:"PATCH",body:{status}});
export const getAdminEventAttendees = (id, accessToken) => apiRequest(`/admin/events/${id}/attendees`, { accessToken });
export const getAdminEventSummary = (id, accessToken) => apiRequest(`/admin/events/${id}/summary`, { accessToken });
export const getAdminDashboard = (accessToken) => apiRequest("/admin/dashboard", { accessToken });
export const getAdminEventReport = (accessToken) => apiRequest("/admin/reports/events", { accessToken });
export const getAdminRegistrationRequests = ({ status = "pending", eventId } = {}, accessToken) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (eventId) params.set("event_id", eventId);
  return apiRequest(`/admin/registration-requests${params.size ? `?${params}` : ""}`, { accessToken });
};
export const approveRegistrationRequest = (id, accessToken) => apiRequest(`/admin/registration-requests/${id}/approve`, { accessToken, method: "POST" });
export const rejectRegistrationRequest = (id, accessToken) => apiRequest(`/admin/registration-requests/${id}/reject`, { accessToken, method: "POST" });

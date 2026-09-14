import { afterEach, describe, expect, it, vi } from "vitest";
import { apiRequest, ApiClientError, getAdminRegistrationRequests, getMyEventRegistration, getNotifications, getUnreadNotificationCount, markAllNotificationsRead, markNotificationRead } from "./api";

afterEach(() => vi.restoreAllMocks());
describe("API client", () => {
  it("attaches the current Supabase JWT", async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "user" }), { headers: { "content-type": "application/json" } }));
    await apiRequest("/auth/me", { accessToken: "current-jwt" });
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/auth/me"), expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer current-jwt" }) }));
  });
  it("normalizes forbidden responses", async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "admin_required", message: "Administrator access is required." } }), { status: 403, headers: { "content-type": "application/json" } }));
    await expect(apiRequest("/admin/dashboard", { accessToken: "attendee" })).rejects.toMatchObject({ status: 403, code: "admin_required" });
  });
  it("normalizes network errors", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("offline"));
    await expect(apiRequest("/auth/me")).rejects.toBeInstanceOf(ApiClientError);
  });
  it("loads backend-authoritative event registration state", async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ registration_id: null, status: null }), { headers: { "content-type": "application/json" } }));
    await getMyEventRegistration("event-123", "current-jwt");
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/events/event-123/my-registration"), expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer current-jwt" }) }));
  });
  it("uses secured admin request filters", async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { headers: { "content-type": "application/json" } }));
    await getAdminRegistrationRequests({ status: "approved", eventId: "event-123" }, "current-jwt");
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/admin/registration-requests?status=approved&event_id=event-123"), expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer current-jwt" }) }));
  });
  it("uses the authenticated notification endpoints", async () => {
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify([]), { headers: { "content-type": "application/json" } })));
    await getNotifications("current-jwt"); await getUnreadNotificationCount("current-jwt"); await markNotificationRead("notice-123", "current-jwt"); await markAllNotificationsRead("current-jwt");
    expect(fetch.mock.calls.map(([url]) => url)).toEqual(expect.arrayContaining([expect.stringContaining("/me/notifications"), expect.stringContaining("/me/notifications/unread-count"), expect.stringContaining("/me/notifications/notice-123/read"), expect.stringContaining("/me/notifications/read-all")]));
  });
});

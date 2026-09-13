import { afterEach, describe, expect, it, vi } from "vitest";
import { apiRequest, ApiClientError } from "./api";

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
});

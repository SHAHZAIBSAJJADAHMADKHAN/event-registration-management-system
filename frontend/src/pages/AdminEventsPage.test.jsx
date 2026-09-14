import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AdminEventsPage } from "./AdminEventsPage";

const api = vi.hoisted(() => ({ getAdminEvents: vi.fn(), createAdminEvent: vi.fn(), updateAdminEvent: vi.fn(), transitionAdminEvent: vi.fn(), deleteAdminEvent: vi.fn() }));
vi.mock("../services/api", () => api);
vi.mock("../hooks/useApi", () => ({ useApi: () => (fn) => fn("token") }));
const draft = { id: "1", title: "Draft", description: "Desc", starts_at: "2030-01-01T10:00:00Z", location: "Hall", capacity: 3, status: "draft" };
const renderPage = () => render(<MemoryRouter><AdminEventsPage /></MemoryRouter>);
afterEach(cleanup);
beforeEach(() => { Object.values(api).forEach((mock) => mock.mockReset()); api.getAdminEvents.mockResolvedValue([draft]); api.createAdminEvent.mockResolvedValue({}); api.updateAdminEvent.mockResolvedValue({}); api.transitionAdminEvent.mockResolvedValue({}); api.deleteAdminEvent.mockResolvedValue({ deleted: true }); window.confirm = vi.fn(() => true); });

describe("AdminEventsPage", () => {
  it("keeps edit and lifecycle controls working", async () => { renderPage(); await screen.findByText("Draft"); fireEvent.click(screen.getByRole("button", { name: "Edit" })); expect(screen.getByLabelText("Title")).toHaveValue("Draft"); fireEvent.click(screen.getByRole("button", { name: "Save changes" })); await waitFor(() => expect(api.updateAdminEvent).toHaveBeenCalled()); fireEvent.click(screen.getByRole("button", { name: "Publish" })); await waitFor(() => expect(api.transitionAdminEvent).toHaveBeenCalledWith("1", "published", "token")); });
  it("shows Delete for every lifecycle state", async () => { api.getAdminEvents.mockResolvedValue([draft, { ...draft, id: "2", title: "Published", status: "published" }, { ...draft, id: "3", title: "Completed", status: "completed" }, { ...draft, id: "4", title: "Cancelled", status: "cancelled" }]); renderPage(); await screen.findByText("Cancelled"); expect(screen.getAllByRole("button", { name: "Delete" })).toHaveLength(4); });
  it("requires strong confirmation, warns for published events, and refreshes after deletion", async () => { const published = { ...draft, id: "2", title: "Published", status: "published" }; api.getAdminEvents.mockImplementation(() => Promise.resolve(api.deleteAdminEvent.mock.calls.length ? [] : [published])); renderPage(); await screen.findByText("Published"); window.confirm.mockReturnValueOnce(false); fireEvent.click(screen.getByRole("button", { name: "Delete" })); expect(api.deleteAdminEvent).not.toHaveBeenCalled(); expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("currently published")); fireEvent.click(screen.getByRole("button", { name: "Delete" })); await waitFor(() => expect(api.deleteAdminEvent).toHaveBeenCalledWith("2", "token")); await waitFor(() => expect(screen.queryByText("Published")).not.toBeInTheDocument()); });
  it("shows professional backend deletion failures", async () => { api.deleteAdminEvent.mockRejectedValue(new Error("This event could not be deleted.")); renderPage(); await screen.findByText("Draft"); fireEvent.click(screen.getByRole("button", { name: "Delete" })); expect((await screen.findAllByText("This event could not be deleted.")).length).toBe(1); });
  it("renders retrieval errors", async () => { api.getAdminEvents.mockRejectedValue(new Error("Admin required")); renderPage(); expect(await screen.findByText("Admin required")).toBeInTheDocument(); });
});

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AdminAttendeesPage } from "./AdminAttendeesPage";

const api = vi.hoisted(() => ({ getAdminEvent: vi.fn(), getAdminEventSummary: vi.fn(), getAdminEventAttendees: vi.fn() }));
const call = vi.hoisted(() => vi.fn((fn) => fn("token")));
vi.mock("../services/api", () => api);
vi.mock("../hooks/useApi", () => ({ useApi: () => call }));
const event = { id: "event-1", title: "Town Hall", starts_at: "2030-01-01T10:00:00Z", location: "Civic Centre", capacity: 3 };
const summary = { capacity: 3, active_registrations: 1, cancelled_registrations: 1, remaining_availability: 2 };
const rows = [{ registration_id: "reg-a", attendee_name: "Alice Attendee", attendee_email: "alice@example.test", registration_status: "approved", registered_at: "2030-01-01T09:00:00Z" }, { registration_id: "reg-b", attendee_name: "Bob Cancelled", attendee_email: "bob@example.test", registration_status: "cancelled", registered_at: "2030-01-01T09:30:00Z" }];
const renderPage = () => render(<MemoryRouter initialEntries={["/admin/events/event-1/attendees"]}><Routes><Route path="/admin/events/:eventId/attendees" element={<AdminAttendeesPage />} /></Routes></MemoryRouter>);
afterEach(cleanup);
beforeEach(() => { call.mockClear(); Object.values(api).forEach((mock) => mock.mockReset()); api.getAdminEvent.mockResolvedValue(event); api.getAdminEventSummary.mockResolvedValue(summary); api.getAdminEventAttendees.mockResolvedValue(rows); });
describe("AdminAttendeesPage", () => {
  it("renders the attendee check-in list and capacity summary", async () => { renderPage(); expect(await screen.findByText("Alice Attendee")).toBeInTheDocument(); expect(screen.getByText("Remaining capacity")).toBeInTheDocument(); expect(screen.getByText("bob@example.test")).toBeInTheDocument(); });
  it("shows a loading state", () => { api.getAdminEvent.mockReturnValue(new Promise(() => {})); renderPage(); expect(screen.getByText("Loading…")).toBeInTheDocument(); });
  it("supports search and approved-status filtering", async () => { renderPage(); await screen.findByText("Alice Attendee"); fireEvent.change(screen.getByLabelText("Search attendees"), { target: { value: "bob" } }); expect(screen.queryByText("Alice Attendee")).not.toBeInTheDocument(); await screen.findByText("Bob Cancelled"); fireEvent.change(screen.getByLabelText("Search attendees"), { target: { value: "" } }); fireEvent.change(screen.getByLabelText("Registration status"), { target: { value: "approved" } }); expect(await screen.findByText("Alice Attendee")).toBeInTheDocument(); expect(screen.queryByText("Bob Cancelled")).not.toBeInTheDocument(); });
  it("shows useful empty and API error states", async () => { api.getAdminEventAttendees.mockResolvedValue([]); const view = renderPage(); expect(await screen.findByText("No registrations yet.")).toBeInTheDocument(); view.unmount(); api.getAdminEvent.mockRejectedValue(new Error("Admin required")); renderPage(); expect(await screen.findByText("Admin required")).toBeInTheDocument(); });
});

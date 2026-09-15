import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AdminEventReportPage } from "./AdminEventReportPage";
import { AdminReportsPage } from "./AdminReportsPage";

const api = vi.hoisted(() => ({ getAdminEventReport: vi.fn(), getAdminEventDetailedReport: vi.fn() }));
const call = vi.hoisted(() => vi.fn((fn) => fn("token")));
vi.mock("../services/api", () => api);
vi.mock("../hooks/useApi", () => ({ useApi: () => call }));

const report = {
  event_id: "event-1", event_title: "AI Full Stack", starts_at: "2030-01-01T10:00:00Z", location: "Civic Centre", status: "published", capacity: 5, remaining_availability: 3,
  registration_counts: { approved: 1, pending: 1, rejected: 1, cancelled: 1 },
  registrations: [
    { registration_id: "approved", attendee_name: "Approved User", attendee_email: "approved@gmail.com", registered_at: "2030-01-01T09:00:00Z", registration_status: "approved" },
    { registration_id: "pending", attendee_name: "Pending User", attendee_email: "pending@gmail.com", registered_at: "2030-01-01T09:01:00Z", registration_status: "pending" },
    { registration_id: "rejected", attendee_name: "Rejected User", attendee_email: "rejected@gmail.com", registered_at: "2030-01-01T09:02:00Z", registration_status: "rejected" },
    { registration_id: "cancelled", attendee_name: "Cancelled User", attendee_email: "cancelled@gmail.com", registered_at: "2030-01-01T09:03:00Z", registration_status: "cancelled" },
  ],
};

beforeEach(() => { call.mockClear(); api.getAdminEventReport.mockReset(); api.getAdminEventDetailedReport.mockReset(); api.getAdminEventDetailedReport.mockResolvedValue(report); });
afterEach(cleanup);

describe("AdminEventReportPage", () => {
  it("opens the correct report from View Report", async () => {
    api.getAdminEventReport.mockResolvedValue([{ event_id: "event-1", event_title: "AI Full Stack", starts_at: report.starts_at, location: report.location, status: "published", capacity: 5, active_registrations: 1, cancelled_registrations: 1, remaining_availability: 3 }]);
    render(<MemoryRouter initialEntries={["/admin/reports"]}><Routes><Route path="/admin/reports" element={<AdminReportsPage />} /><Route path="/admin/reports/:eventId" element={<AdminEventReportPage />} /></Routes></MemoryRouter>);
    fireEvent.click(await screen.findByRole("link", { name: "View Report" }));
    expect(await screen.findByRole("heading", { name: "AI Full Stack" })).toBeInTheDocument();
    expect(api.getAdminEventDetailedReport).toHaveBeenCalledWith("event-1", "token");
  });

  it.each(["all", "approved", "pending", "rejected", "cancelled"])("filters registrations by %s", async (filter) => {
    render(<MemoryRouter initialEntries={["/admin/reports/event-1"]}><Routes><Route path="/admin/reports/:eventId" element={<AdminEventReportPage />} /></Routes></MemoryRouter>);
    await screen.findByText("Approved User");
    fireEvent.change(screen.getByLabelText("Registration status"), { target: { value: filter } });
    const visible = filter === "all" ? report.registrations : report.registrations.filter((row) => row.registration_status === filter);
    for (const row of visible) expect(screen.getByText(row.attendee_name)).toBeInTheDocument();
    for (const row of report.registrations.filter((row) => !visible.includes(row))) expect(screen.queryByText(row.attendee_name)).not.toBeInTheDocument();
  });

  it("shows an empty filtered state", async () => {
    api.getAdminEventDetailedReport.mockResolvedValue({ ...report, registration_counts: { ...report.registration_counts, rejected: 0 }, registrations: report.registrations.filter((row) => row.registration_status !== "rejected") });
    render(<MemoryRouter initialEntries={["/admin/reports/event-1"]}><Routes><Route path="/admin/reports/:eventId" element={<AdminEventReportPage />} /></Routes></MemoryRouter>);
    await screen.findByText("Approved User"); fireEvent.change(screen.getByLabelText("Registration status"), { target: { value: "rejected" } });
    expect(screen.getByText("No rejected registrations for this event.")).toBeInTheDocument();
  });
});

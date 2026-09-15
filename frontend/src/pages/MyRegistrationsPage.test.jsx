import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MyRegistrationsPage } from "./MyRegistrationsPage";

const api = vi.hoisted(() => ({ getMyRegistrations: vi.fn(), cancelRegistration: vi.fn() }));
vi.mock("../services/api", () => api);
vi.mock("../hooks/useApi", () => ({ useApi: () => (fn) => fn("token") }));

const registration = (id, eventStatus, endsAt = "2030-01-01T12:00:00Z") => ({
  id,
  status: "approved",
  event: { title: `${eventStatus} event`, starts_at: "2030-01-01T10:00:00Z", ends_at: endsAt, location: "Hall", status: eventStatus },
});

describe("MyRegistrationsPage cancellation lifecycle", () => {
  afterEach(cleanup);
  beforeEach(() => { api.getMyRegistrations.mockReset(); api.cancelRegistration.mockReset(); });

  it("shows lifecycle messages and no cancellation action for completed, cancelled, or ended events", async () => {
    api.getMyRegistrations.mockResolvedValue([
      registration("completed", "completed"),
      registration("cancelled", "cancelled"),
      registration("ended", "published", "2000-01-01T12:00:00Z"),
    ]);
    render(<MemoryRouter><MyRegistrationsPage /></MemoryRouter>);

    expect(await screen.findByText("Event Completed")).toBeInTheDocument();
    expect(screen.getByText("Event Cancelled")).toBeInTheDocument();
    expect(screen.getByText("Event Ended")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel Registration" })).not.toBeInTheDocument();
  });

  it("keeps cancellation available for a future published event", async () => {
    api.getMyRegistrations.mockResolvedValue([registration("future", "published")]);
    render(<MemoryRouter><MyRegistrationsPage /></MemoryRouter>);

    expect(await screen.findByRole("button", { name: "Cancel Registration" })).toBeInTheDocument();
  });
});

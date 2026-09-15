import { describe, expect, it } from "vitest";
import { createEventReportCsv, createEventReportPdf } from "./eventReportExports";

const report = { event_title: "AI Full Stack", starts_at: "2030-01-01T10:00:00Z", location: "Civic Centre", status: "published", capacity: 5, remaining_availability: 3, registration_counts: { approved: 1, pending: 1, rejected: 0, cancelled: 0 } };
const rows = [{ attendee_name: "Approved User", attendee_email: "approved@gmail.com", registered_at: "2030-01-01T09:00:00Z", registration_status: "approved" }, { attendee_name: "Pending User", attendee_email: "pending@gmail.com", registered_at: "2030-01-01T09:01:00Z", registration_status: "pending" }];
const readBlob = (blob) => new Promise((resolve) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.readAsText(blob); });

describe("event report exports", () => {
  it("creates a filtered CSV containing only selected attendee rows", async () => {
    const content = await readBlob(createEventReportCsv(report, [rows[0]], "approved"));
    expect(content).toContain("Approved User"); expect(content).not.toContain("Pending User"); expect(content).toContain("Current report filter");
  });

  it("creates a real filtered PDF containing only selected attendee rows", async () => {
    const pdf = createEventReportPdf(report, [rows[0]], "approved"); const content = await readBlob(pdf);
    expect(pdf.type).toBe("application/pdf"); expect(content.startsWith("%PDF-1.4")).toBe(true);
    expect(content).toContain("Approved User"); expect(content).not.toContain("Pending User"); expect(content).toContain("Current Report Filter: Approved");
  });
});

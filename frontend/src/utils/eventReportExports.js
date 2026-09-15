const fmt = (date) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(date));
const statusLabel = (status) => `${status.slice(0, 1).toUpperCase()}${status.slice(1)}`;
const csvCell = (value) => {
  const text = String(value ?? "");
  const safeText = text.startsWith("=") || text.startsWith("+") || text.startsWith("-") || text.startsWith("@") ? `'${text}` : text;
  return `"${safeText.replaceAll('"', '""')}"`;
};

export function createEventReportCsv(report, rows, filter) {
  const content = [
    ["Nowshera Events Co. - Event Registration Report"],
    ["Event", report.event_title], ["Date and time", fmt(report.starts_at)], ["Location", report.location],
    ["Status", report.status], ["Capacity", report.capacity], ["Remaining capacity", report.remaining_availability],
    ["Current report filter", statusLabel(filter)], [],
    ["Approved", report.registration_counts.approved], ["Pending", report.registration_counts.pending],
    ["Rejected", report.registration_counts.rejected], ["Cancelled", report.registration_counts.cancelled], [],
    ["Attendee name", "Attendee email", "Requested date", "Registration status"],
    ...rows.map((row) => [row.attendee_name || "Unnamed attendee", row.attendee_email || "", fmt(row.registered_at), statusLabel(row.registration_status)]),
  ].map((row) => row.map(csvCell).join(",")).join("\n");
  return new Blob([content], { type: "text/csv;charset=utf-8" });
}

const pdfText = (value) => String(value ?? "").normalize("NFKD").replace(/[^\x20-\x7E]/g, "?").replaceAll("\\", "\\\\").replaceAll("(", "\\(").replaceAll(")", "\\)");
const wrap = (text, width = 92) => {
  const words = pdfText(text).split(/\s+/); const lines = []; let line = "";
  for (const word of words) { if (`${line} ${word}`.trim().length > width && line) { lines.push(line); line = word; } else line = `${line} ${word}`.trim(); }
  return line ? [...lines, line] : [""];
};

export function createEventReportPdf(report, rows, filter) {
  const summary = report.registration_counts;
  const lines = [
    "NOWSHERA EVENTS CO.", "EVENT REGISTRATION REPORT", "", `Event: ${report.event_title}`,
    `Date: ${fmt(report.starts_at)}`, `Location: ${report.location}`, `Status: ${statusLabel(report.status)}`,
    `Capacity: ${report.capacity}`, `Remaining: ${report.remaining_availability}`, "", "REGISTRATION SUMMARY",
    `Approved: ${summary.approved}    Pending: ${summary.pending}    Rejected: ${summary.rejected}    Cancelled: ${summary.cancelled}`,
    `Current Report Filter: ${statusLabel(filter)}`, "", "ATTENDEE DETAILS", "Name | Email | Requested Date | Status",
    ...(rows.length ? rows.flatMap((row) => wrap(`${row.attendee_name || "Unnamed attendee"} | ${row.attendee_email || ""} | ${fmt(row.registered_at)} | ${statusLabel(row.registration_status)}`)) : ["No registrations match the selected filter."]),
    "", `Generated At: ${fmt(new Date())}`,
  ];
  const pages = []; for (let index = 0; index < lines.length; index += 44) pages.push(lines.slice(index, index + 44));
  const objects = ["<< /Type /Catalog /Pages 2 0 R >>", "", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"];
  const pageIds = [];
  for (const page of pages) {
    const pageId = objects.length + 1; const contentId = pageId + 1; pageIds.push(pageId);
    const stream = `BT\n/F1 10 Tf\n50 780 Td\n14 TL\n${page.map((line) => `(${pdfText(line)}) Tj\nT*`).join("\n")}\nET`;
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${contentId} 0 R >>`, `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
  }
  objects[1] = `<< /Type /Pages /Kids [${pageIds.map((id) => `${id} 0 R`).join(" ")}] /Count ${pageIds.length} >>`;
  let pdf = "%PDF-1.4\n"; const offsets = [0];
  objects.forEach((object, index) => { offsets.push(pdf.length); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`; });
  const xref = pdf.length; pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.slice(1).map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("")}trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return new Blob([pdf], { type: "application/pdf" });
}

export function downloadExport(blob, filename) {
  const url = URL.createObjectURL(blob); const link = document.createElement("a");
  link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
}

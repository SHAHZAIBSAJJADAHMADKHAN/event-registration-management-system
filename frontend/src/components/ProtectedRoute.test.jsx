import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthContext } from "../context/AuthContext";
import { ProtectedRoute } from "./ProtectedRoute";

function renderRoute(auth, path = "/admin/dashboard") {
  render(<AuthContext.Provider value={auth}><MemoryRouter initialEntries={[path]}><Routes>
    <Route element={<ProtectedRoute allowedRole="admin" />}><Route path="/admin/dashboard" element={<p>Admin area</p>} /></Route>
    <Route path="/events" element={<p>Attendee area</p>} /><Route path="/sign-in" element={<p>Sign in</p>} />
  </Routes></MemoryRouter></AuthContext.Provider>);
}

describe("ProtectedRoute", () => {
  const base = { loading: false, session: { access_token: "jwt" }, profile: { role: "admin" } };
  it("shows an admin route to an admin", () => { renderRoute(base); expect(screen.getByText("Admin area")).toBeInTheDocument(); });
  it("redirects an attendee away from an admin route", () => { renderRoute({ ...base, profile: { role: "attendee" } }); expect(screen.getByText("Attendee area")).toBeInTheDocument(); });
  it("redirects an unauthenticated visitor to sign in", () => { renderRoute({ ...base, session: null, profile: null }); expect(screen.getByText("Sign in")).toBeInTheDocument(); });
  it("does not flash content while the session loads", () => { renderRoute({ ...base, loading: true }); expect(screen.getByRole("status")).toHaveTextContent("Loading your account"); });
});

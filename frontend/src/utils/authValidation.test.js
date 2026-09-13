import { describe, expect, it } from "vitest";
import { validateSignIn, validateSignUp } from "./authValidation";

describe("authentication validation", () => {
  it("requires valid sign-in credentials", () => {
    expect(validateSignIn({ email: "bad", password: "" })).toEqual({
      email: "Enter a valid email address.", password: "Password is required.",
    });
  });
  it("validates attendee sign-up without accepting a role", () => {
    expect(validateSignUp({ fullName: "", email: "person@example.test", password: "short", confirmPassword: "different" })).toMatchObject({
      fullName: "Your name is required.", password: "Password must be at least 8 characters.", confirmPassword: "Passwords do not match.",
    });
  });
});

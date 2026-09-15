import { describe, expect, it } from "vitest";
import { isSupportedSignUpEmail, validateSignIn, validateSignUp } from "./authValidation";

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

  it.each([
    "shahzaibtigerking11@gmail.com",
    "shahzaib@yahoo.com",
    "user123@outlook.com",
    "test.user@hotmail.com",
    "person@icloud.com",
    "Shahzaib@GMAIL.COM",
  ])("accepts supported signup email %s", (email) => {
    expect(isSupportedSignUpEmail(email)).toBe(true);
  });

  it.each([
    "123",
    "shahzaib",
    "shahzaib@",
    "@gmail.com",
    "shahzaib @gmail.com",
    "shahzaib@@gmail.com",
    "shahzaib@gmil.com",
    "shahzaib@gmial.com",
    "shahzaib@gmai.com",
    "shahzaib@gmail.co",
    "shahzaib@gma.il.com",
    "shahzaib@yaho.com",
    "shahzaib@outlok.com",
    "shahzaib@random-domain.com",
  ])("rejects malformed or unsupported signup email %s", (email) => {
    expect(isSupportedSignUpEmail(email)).toBe(false);
    expect(validateSignUp({ fullName: "User", email, password: "password1", confirmPassword: "password1" }).email)
      .toBe("Please enter a valid email using Gmail, Yahoo, Outlook, Hotmail, or iCloud.");
  });
});

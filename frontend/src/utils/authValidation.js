const supportedEmailDomains = new Set([
  "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
]);

export const supportedEmailMessage = "Please enter a valid email using Gmail, Yahoo, Outlook, Hotmail, or iCloud.";

export function isSupportedSignUpEmail(email) {
  if (typeof email !== "string" || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return false;
  const domain = email.slice(email.lastIndexOf("@") + 1).toLowerCase();
  return supportedEmailDomains.has(domain);
}

export function validateSignIn({ email, password }) {
  const errors = {};
  if (!email?.trim()) errors.email = "Email is required.";
  else if (!/^\S+@\S+\.\S+$/.test(email)) errors.email = "Enter a valid email address.";
  if (!password) errors.password = "Password is required.";
  return errors;
}

export function validateSignUp({ fullName, email, password, confirmPassword }) {
  const errors = validateSignIn({ email, password });
  if (email?.trim() && !isSupportedSignUpEmail(email)) errors.email = supportedEmailMessage;
  if (!fullName?.trim()) errors.fullName = "Your name is required.";
  if (fullName?.trim().length > 200) errors.fullName = "Name must be 200 characters or fewer.";
  if (password && password.length < 8) errors.password = "Password must be at least 8 characters.";
  if (!confirmPassword) errors.confirmPassword = "Please confirm your password.";
  else if (password !== confirmPassword) errors.confirmPassword = "Passwords do not match.";
  return errors;
}

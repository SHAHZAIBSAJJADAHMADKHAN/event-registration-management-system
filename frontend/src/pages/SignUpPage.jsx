import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthCard } from "../components/AuthCard";
import { useAuth } from "../context/AuthContext";
import { validateSignUp } from "../utils/authValidation";

export function SignUpPage() {
  const { signUp, error: sessionError } = useAuth();
  const navigate = useNavigate();
  const [values, setValues] = useState({ fullName: "", email: "", password: "", confirmPassword: "" });
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const onChange = ({ target }) => setValues((current) => ({ ...current, [target.name]: target.value }));
  const submit = async (event) => {
    event.preventDefault(); setMessage("");
    const nextErrors = validateSignUp(values); setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setSubmitting(true);
    const result = await signUp(values);
    setSubmitting(false);
    if (result.error) { setMessage(result.error.message); return; }
    if (result.confirmationRequired) { setMessage("Check your email to confirm your account, then sign in."); return; }
    navigate(result.profile.role === "admin" ? "/admin/dashboard" : "/events", { replace: true });
  };
  return <AuthCard eyebrow="Create your account" title="Start joining events" description="Public accounts are created as attendees. Administrator access is provisioned separately.">
    <form onSubmit={submit} noValidate>
      {sessionError && <p className="message message--error" role="alert">{sessionError}</p>}
      {message && <p className={`message ${message.startsWith("Check") ? "message--success" : "message--error"}`} role="alert">{message}</p>}
      <label>Your name<input name="fullName" autoComplete="name" value={values.fullName} onChange={onChange} aria-invalid={Boolean(errors.fullName)} />{errors.fullName && <small>{errors.fullName}</small>}</label>
      <label>Email<input name="email" type="email" autoComplete="email" value={values.email} onChange={onChange} aria-invalid={Boolean(errors.email)} />{errors.email && <small>{errors.email}</small>}</label>
      <label>Password<input name="password" type="password" autoComplete="new-password" value={values.password} onChange={onChange} aria-invalid={Boolean(errors.password)} />{errors.password && <small>{errors.password}</small>}</label>
      <label>Confirm password<input name="confirmPassword" type="password" autoComplete="new-password" value={values.confirmPassword} onChange={onChange} aria-invalid={Boolean(errors.confirmPassword)} />{errors.confirmPassword && <small>{errors.confirmPassword}</small>}</label>
      <button className="button button--full" disabled={submitting}>{submitting ? "Creating account…" : "Create attendee account"}</button>
    </form>
    <p className="auth-footnote">Already have an account? <Link to="/sign-in">Sign in</Link></p>
  </AuthCard>;
}

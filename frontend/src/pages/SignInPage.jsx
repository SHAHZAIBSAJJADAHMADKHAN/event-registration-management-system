import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AuthCard } from "../components/AuthCard";
import { useAuth } from "../context/AuthContext";
import { validateSignIn } from "../utils/authValidation";

export function SignInPage() {
  const { signIn, error: sessionError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [values, setValues] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const onChange = ({ target }) => setValues((current) => ({ ...current, [target.name]: target.value }));
  const submit = async (event) => {
    event.preventDefault(); setMessage("");
    const nextErrors = validateSignIn(values); setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setSubmitting(true);
    const result = await signIn(values);
    setSubmitting(false);
    if (result.error) { setMessage(result.error.message === "Invalid login credentials" ? "Email or password is incorrect." : result.error.message); return; }
    navigate(location.state?.from || (result.profile.role === "admin" ? "/admin/dashboard" : "/events"), { replace: true });
  };
  return <AuthCard eyebrow="Welcome back" title="Sign in to your account" description="Use your Nowshera Events account to continue.">
    <form onSubmit={submit} noValidate>
      {sessionError && <p className="message message--error" role="alert">{sessionError}</p>}
      {message && <p className="message message--error" role="alert">{message}</p>}
      <label>Email<input name="email" type="email" autoComplete="email" value={values.email} onChange={onChange} aria-invalid={Boolean(errors.email)} />{errors.email && <small>{errors.email}</small>}</label>
      <label>Password<input name="password" type="password" autoComplete="current-password" value={values.password} onChange={onChange} aria-invalid={Boolean(errors.password)} />{errors.password && <small>{errors.password}</small>}</label>
      <button className="button button--full" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
    </form>
    <p className="auth-footnote">New to Nowshera Events? <Link to="/sign-up">Create an attendee account</Link></p>
  </AuthCard>;
}

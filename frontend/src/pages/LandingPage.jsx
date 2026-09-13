import { Link } from "react-router-dom";
import { EventOperationsVisual } from "../components/EventOperationsVisual";

export function LandingPage() {
  return <main className="landing-page">
    <header className="public-header">
      <Link className="brand" to="/">N<span>•</span> Events</Link>
      <div><Link className="button button--text" to="/sign-in">Sign in</Link><Link className="button" to="/sign-up">Create account</Link></div>
    </header>
    <section className="hero">
      <div>
        <p className="eyebrow">Nowshera Events Co.</p>
        <h1>A better way to bring people together.</h1>
        <p className="hero-copy">Discover upcoming events, reserve your place, and manage your registrations in one calm, dependable space.</p>
        <div className="hero-actions"><Link className="button" to="/events">Browse events</Link><Link className="button button--secondary" to="/sign-in">Sign in</Link></div>
      </div>
      <EventOperationsVisual />
    </section>
    <section className="value-grid" aria-label="What you can do">
      <article><h2>Discover</h2><p>Find upcoming workshops, seminars, and community events in one place.</p></article>
      <article><h2>Register</h2><p>Secure your spot with clear availability and straightforward confirmation.</p></article>
      <article><h2>Stay organised</h2><p>Keep track of your registrations and manage changes with confidence.</p></article>
    </section>
  </main>;
}

export function AuthCard({ eyebrow, title, description, children }) {
  return <main className="auth-layout">
    <section className="auth-intro" aria-label="Nowshera Events Co.">
      <a className="brand brand--light" href="/">N<span>•</span> Events</a>
      <div>
        <p className="eyebrow">Nowshera Events Co.</p>
        <h1>Events, made easier to join.</h1>
        <p>Discover meaningful gatherings, reserve your place, and keep your plans organised.</p>
      </div>
    </section>
    <section className="auth-panel">
      <div className="auth-card">
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p className="muted">{description}</p>
        {children}
      </div>
    </section>
  </main>;
}

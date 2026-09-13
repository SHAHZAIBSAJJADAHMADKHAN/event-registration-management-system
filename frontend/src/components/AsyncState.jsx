export function AsyncState({ loading, error, empty, children }) {
  if (loading) return <div className="state-card" role="status">Loading…</div>;
  if (error) return <div className="state-card state-card--error" role="alert">{error}</div>;
  if (empty) return <div className="state-card">{empty}</div>;
  return children;
}

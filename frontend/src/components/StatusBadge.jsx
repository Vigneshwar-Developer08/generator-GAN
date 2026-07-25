export function StatusBadge({ health, checked }) {
  if (!checked) {
    return (
      <span className="status-badge status-badge--pending">
        <span className="status-badge__dot" />
        connecting…
      </span>
    );
  }

  if (!health || !health.model_loaded) {
    return (
      <span className="status-badge status-badge--offline">
        <span className="status-badge__dot" />
        {health ? "model not loaded" : "backend unreachable"}
      </span>
    );
  }

  return (
    <span className="status-badge status-badge--online">
      <span className="status-badge__dot" />
      {health.device}
    </span>
  );
}

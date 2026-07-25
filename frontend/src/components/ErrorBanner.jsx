export function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="banner banner--error" role="alert">
      <span className="banner__icon" aria-hidden="true">
        !
      </span>
      <p>{message}</p>
    </div>
  );
}

import { useId, useState } from "react";
import { StatusBadge } from "./StatusBadge.jsx";

export function Console({
  baseUrl,
  onBaseUrlChange,
  health,
  healthChecked,
  status,
  result,
  onGenerate,
}) {
  const [seedText, setSeedText] = useState("");
  const [showConnection, setShowConnection] = useState(false);
  const seedFieldId = useId();
  const urlFieldId = useId();

  const disabled = status === "loading" || (healthChecked && health && !health.model_loaded);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (disabled) return;
    const trimmed = seedText.trim();
    const seed = trimmed === "" ? undefined : Number(trimmed);
    onGenerate(seed);
  };

  return (
    <aside className="console">
      <div className="console__eyebrow">DCGAN INFERENCE CONSOLE</div>
      <h1 className="console__title">Latent Faces</h1>
      <p className="console__lede">
        Draw a random vector from the generator's latent space and render it as a face.
        Set a seed to reproduce the same draw later.
      </p>

      <form className="console__form" onSubmit={handleSubmit}>
        <label className="field" htmlFor={seedFieldId}>
          <span className="field__label">Seed (optional)</span>
          <input
            id={seedFieldId}
            className="field__input field__input--mono"
            type="number"
            inputMode="numeric"
            placeholder="random"
            value={seedText}
            onChange={(event) => setSeedText(event.target.value)}
            min="0"
            max="4294967295"
          />
        </label>

        <button type="submit" className="button button--primary" disabled={disabled}>
          {status === "loading" ? "Sampling…" : "Generate"}
        </button>
      </form>

      <div className="console__divider" />

      <button
        type="button"
        className="disclosure"
        onClick={() => setShowConnection((v) => !v)}
        aria-expanded={showConnection}
      >
        <span>Connection</span>
        <StatusBadge health={health} checked={healthChecked} />
      </button>

      {showConnection && (
        <div className="connection">
          <label className="field" htmlFor={urlFieldId}>
            <span className="field__label">API base URL</span>
            <input
              id={urlFieldId}
              className="field__input field__input--mono"
              type="text"
              value={baseUrl}
              onChange={(event) => onBaseUrlChange(event.target.value)}
              placeholder="http://localhost:8000"
              spellCheck="false"
            />
          </label>
        </div>
      )}

      {result && (
        <dl className="stats">
          <div className="stats__row">
            <dt>filename</dt>
            <dd>{result.filename}</dd>
          </div>
          <div className="stats__row">
            <dt>seed</dt>
            <dd>{result.seed ?? "random"}</dd>
          </div>
          <div className="stats__row">
            <dt>latency</dt>
            <dd>{result.generationTimeMs.toFixed(1)} ms</dd>
          </div>
          <div className="stats__row">
            <dt>device</dt>
            <dd>{health?.device ?? "—"}</dd>
          </div>
        </dl>
      )}

      {result && (
        <a
          className="button button--ghost"
          href={result.imageUrl}
          download={result.filename}
        >
          Download PNG
        </a>
      )}
    </aside>
  );
}

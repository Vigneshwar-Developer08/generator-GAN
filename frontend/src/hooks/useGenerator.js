import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client.js";

const BASE_URL_STORAGE_KEY = "latent-faces:base-url";
const DEFAULT_BASE_URL = "http://localhost:8000";
const HEALTH_POLL_MS = 15_000;

function readStoredBaseUrl() {
  try {
    return window.localStorage.getItem(BASE_URL_STORAGE_KEY) ?? DEFAULT_BASE_URL;
  } catch {
    return DEFAULT_BASE_URL;
  }
}

function describeError(err) {
  if (!(err instanceof ApiError)) return "Something went wrong generating the image.";
  switch (err.status) {
    case 0:
      return err.message;
    case 503:
      return "The model isn't loaded on the server. Start the API with a valid generator_final.pth checkpoint, then try again.";
    case 429:
      return "Too many requests in a row. Wait a few seconds before generating again.";
    case 400:
      return err.message || "That seed value was rejected. Use a whole number and try again.";
    default:
      return err.message;
  }
}

/**
 * Owns the connection to the backend, the last generation result, and
 * request lifecycle state ("idle" | "loading" | "success" | "error").
 */
export function useGenerator() {
  const [baseUrl, setBaseUrlState] = useState(readStoredBaseUrl);
  const [health, setHealth] = useState(null);
  const [healthChecked, setHealthChecked] = useState(false);
  const [status, setStatus] = useState("idle");
  const [errorMessage, setErrorMessage] = useState(null);
  const [result, setResult] = useState(null); // { imageUrl, filename, generationTimeMs, seed }
  const pollRef = useRef(null);

  const setBaseUrl = useCallback((next) => {
    setBaseUrlState(next);
    try {
      window.localStorage.setItem(BASE_URL_STORAGE_KEY, next);
    } catch {
      // localStorage unavailable (private browsing) — fine, it just won't persist.
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const data = await api.health(baseUrl);
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setHealthChecked(true);
    }
  }, [baseUrl]);

  useEffect(() => {
    setHealthChecked(false);
    checkHealth();
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(checkHealth, HEALTH_POLL_MS);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [checkHealth]);

  const generate = useCallback(
    async (seed) => {
      setStatus("loading");
      setErrorMessage(null);
      try {
        const data = await api.generate(baseUrl, seed);
        setResult({
          imageUrl: api.resolveImageUrl(baseUrl, data.image_url),
          filename: data.filename,
          generationTimeMs: data.generation_time_ms,
          seed: data.seed ?? null,
        });
        setStatus("success");
        checkHealth();
      } catch (err) {
        setErrorMessage(describeError(err));
        setStatus("error");
      }
    },
    [baseUrl, checkHealth]
  );

  return {
    baseUrl,
    setBaseUrl,
    health,
    healthChecked,
    status,
    errorMessage,
    result,
    generate,
    checkHealth,
  };
}

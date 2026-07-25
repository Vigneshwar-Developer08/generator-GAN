import { Console } from "./components/Console.jsx";
import { ErrorBanner } from "./components/ErrorBanner.jsx";
import { Stage } from "./components/Stage.jsx";
import { useGenerator } from "./hooks/useGenerator.js";

export default function App() {
  const {
    baseUrl,
    setBaseUrl,
    health,
    healthChecked,
    status,
    errorMessage,
    result,
    generate,
  } = useGenerator();

  return (
    <div className="layout">
      <Stage status={status} result={result} />

      <div className="layout__console-col">
        <Console
          baseUrl={baseUrl}
          onBaseUrlChange={setBaseUrl}
          health={health}
          healthChecked={healthChecked}
          status={status}
          result={result}
          onGenerate={generate}
        />
        <ErrorBanner message={status === "error" ? errorMessage : null} />
      </div>
    </div>
  );
}

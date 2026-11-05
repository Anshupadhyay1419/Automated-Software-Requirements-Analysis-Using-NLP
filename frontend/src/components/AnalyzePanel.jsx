import { useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { Play, TriangleAlert } from "lucide-react";
import { api } from "../api";
import { ErrorBanner } from "./ui";

// The button that starts the analysis, plus any error or warnings from the last run.
export default function AnalyzePanel({ hasSource }) {
  const { project, reloadProject } = useOutletContext();
  const [error, setError] = useState("");
  const running = project.analysis_status === "running";

  async function start() {
    setError("");
    try {
      await api.analyze(project.id);
      await reloadProject();
    } catch (problem) {
      setError(problem.message);
    }
  }

  const warnings = project.analysis_warnings || [];
  return (
    <>
      <ErrorBanner message={error} onClose={() => setError("")} />
      {project.analysis_status === "failed" && (
        <ErrorBanner message={`The analysis did not finish. ${project.analysis_error}\nResults saved so far have been kept. Fix the problem and run it again.`} />
      )}
      <div className="card mb-5 flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="text-sm text-slate-600">
          {hasSource
            ? "Runs extraction, classification, duplicate detection, quality checks and user story drafting on this computer. Your reviews and edits are kept when you run it again."
            : <>Add source text first on the <Link className="underline" to={`/projects/${project.id}/source`}>Source text</Link> page.</>}
        </div>
        <button className="btn btn-primary" onClick={start} disabled={running || !hasSource}>
          <Play className="h-4 w-4" /> {running ? "Analysing" : project.analysis_status === "idle" ? "Run analysis" : "Run analysis again"}
        </button>
      </div>
      {warnings.length > 0 && (
        <details className="mb-5 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <summary className="flex cursor-pointer items-center gap-2 font-medium">
            <TriangleAlert className="h-4 w-4" /> {warnings.length} item{warnings.length > 1 ? "s" : ""} from the last run need your attention
          </summary>
          <ul className="mt-2 space-y-2">
            {warnings.map((warning, index) => (
              <li key={index} className="border-t border-amber-200 pt-2">
                {warning.source && <p className="font-medium">"{warning.source}"</p>}
                <p className="break-words">{warning.message}</p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

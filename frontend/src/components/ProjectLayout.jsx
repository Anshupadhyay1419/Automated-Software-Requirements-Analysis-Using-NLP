import { useEffect } from "react";
import { Link, Outlet, useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { api } from "../api";
import { useLoad } from "../useLoad";
import { EmptyState, ErrorBanner, Spinner } from "./ui";

// Loads the project for all its pages. While an analysis runs, it checks progress
// every 2 seconds, and a progress bar stays visible on every page of the project.
export default function ProjectLayout() {
  const { projectId } = useParams();
  const { data: project, error, loading, reload, setData } = useLoad(() => api.getProject(projectId), [projectId]);
  const running = project?.analysis_status === "running";

  useEffect(() => {
    if (!running) return undefined;
    const timer = setInterval(reload, 2000);
    return () => clearInterval(timer);
  }, [running, reload]);

  if (loading && !project) return <Spinner />;
  if (error && !project) {
    return (
      <>
        <ErrorBanner message={error} />
        <EmptyState title="This project could not be opened"><Link className="btn" to="/">Back to projects</Link></EmptyState>
      </>
    );
  }

  return (
    <>
      <div className="mb-4 flex items-center gap-2 text-sm text-slate-500">
        <Link to="/" className="hover:text-slate-800">Projects</Link>
        <span>/</span>
        <span className="truncate font-medium text-slate-800">{project.name}</span>
      </div>
      {running && (
        <div className="card mb-4 px-4 py-3" role="status">
          <div className="mb-1.5 flex items-center justify-between text-sm">
            <span className="flex items-center gap-2 font-medium text-slate-700">
              <Loader2 className="h-4 w-4 animate-spin" /> {project.analysis_step || "Starting"}
            </span>
            <span className="tabular-nums text-slate-500">{project.analysis_progress}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded bg-slate-100">
            <div className="h-full rounded bg-slate-700 transition-all" style={{ width: `${project.analysis_progress}%` }} />
          </div>
        </div>
      )}
      {/* The key reloads a page's lists when an analysis finishes. */}
      <Outlet key={`${projectId}-${project.analysis_status}`} context={{ project, reloadProject: reload, setProject: setData }} />
    </>
  );
}

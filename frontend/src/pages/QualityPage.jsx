import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { CheckCircle2, HelpCircle } from "lucide-react";
import { api } from "../api";
import { useLoad } from "../useLoad";
import { KIND_LABELS } from "../labels";
import { Badge, EmptyState, ErrorBanner, Notice, OriginBadge, PageHeader, ReviewButtons, Spinner, StatusBadge } from "../components/ui";

function IssueCard({ issue, onChange }) {
  return (
    <div className={`card p-4 ${issue.status === "dismissed" ? "opacity-60" : ""}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge tone="blue">{KIND_LABELS[issue.kind] || issue.kind}</Badge>
          <OriginBadge origin={issue.origin} />
          <StatusBadge status={issue.status} />
        </div>
        <ReviewButtons status={issue.status} rejectValue="dismissed" rejectLabel="Dismiss" onChange={onChange} />
      </div>
      <p className="mt-2 text-xs text-slate-500">Stated requirement, REQ-{issue.requirement_id}</p>
      <p className="text-sm font-medium text-slate-900">{issue.requirement_text}</p>
      {issue.other_requirement_text && (
        <>
          <p className="mt-2 text-xs text-slate-500">May conflict with REQ-{issue.other_requirement_id}</p>
          <p className="text-sm font-medium text-slate-900">{issue.other_requirement_text}</p>
        </>
      )}
      <p className="mt-2 text-sm text-slate-700">{issue.message}</p>
      {issue.question && (
        <p className="mt-2 flex items-start gap-1.5 rounded bg-slate-50 px-2.5 py-1.5 text-sm text-slate-700">
          <HelpCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span><span className="font-medium">Inferred question:</span> {issue.question}</span>
        </p>
      )}
    </div>
  );
}

export default function QualityPage() {
  const { project, reloadProject } = useOutletContext();
  const { data: issues, setData, error, setError, loading } = useLoad(() => api.listIssues(project.id), [project.id]);
  const [kind, setKind] = useState("all");
  const visible = (issues || []).filter((issue) => kind === "all" || issue.kind === kind);

  async function setStatus(issue, status) {
    try {
      const updated = await api.updateIssue(issue.id, status);
      setData((current) => current.map((row) => (row.id === issue.id ? { ...row, status: updated.status } : row)));
      reloadProject();
    } catch (problem) {
      setError(problem.message);
    }
  }

  return (
    <>
      <PageHeader title="Quality analysis" subtitle="Possible vague wording, missing measures, unclear actors, unspecified behaviour and contradictions." />
      <Notice>These are suggestions, and this check cannot find every problem. The requirement text is what the source states. The questions are inferred by this tool and were not stated by the client.</Notice>
      <ErrorBanner message={error} onClose={() => setError("")} />
      {loading ? <Spinner /> : !issues?.length ? (
        <EmptyState icon={CheckCircle2} title="No quality warnings" text="None were found. That does not prove the requirements are free of problems. If the analysis has not run yet, start it from Overview." />
      ) : (
        <>
          <div className="mb-3 flex items-center gap-2">
            <select className="input w-auto" aria-label="Filter by kind" value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="all">All kinds</option>
              {Object.entries(KIND_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <span className="text-sm text-slate-500">{visible.length} shown</span>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            {visible.map((issue) => <IssueCard key={issue.id} issue={issue} onChange={(status) => setStatus(issue, status)} />)}
          </div>
        </>
      )}
    </>
  );
}

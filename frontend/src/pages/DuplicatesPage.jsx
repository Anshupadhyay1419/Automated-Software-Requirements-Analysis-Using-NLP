import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Copy, RefreshCw } from "lucide-react";
import { api } from "../api";
import { useLoad } from "../useLoad";
import { EmptyState, ErrorBanner, Notice, PageHeader, ReviewButtons, Spinner, StatusBadge } from "../components/ui";

export default function DuplicatesPage() {
  const { project, reloadProject } = useOutletContext();
  const { data: pairs, setData, error, setError, loading, reload } = useLoad(() => api.listDuplicates(project.id), [project.id]);
  const { data: requirements } = useLoad(() => api.listRequirements(project.id), [project.id]);
  const [threshold, setThreshold] = useState(project.similarity_threshold);
  const [manual, setManual] = useState({ a: "", b: "" });
  const running = project.analysis_status === "running";
  useEffect(() => setThreshold(project.similarity_threshold), [project.similarity_threshold]);

  async function attempt(action) {
    setError("");
    try {
      await action();
    } catch (problem) {
      setError(problem.message);
    }
  }

  const rerun = () => attempt(async () => {
    await api.updateProject(project.id, { similarity_threshold: Number(threshold) });
    await api.analyze(project.id, ["duplicates"]);
    await reloadProject();
  });
  const setStatus = (pair, status) => attempt(async () => {
    const updated = await api.updateDuplicate(pair.id, status);
    setData((current) => current.map((row) => (row.id === pair.id ? { ...row, status: updated.status } : row)));
    reloadProject();
  });
  const mark = (event) => {
    event.preventDefault();
    attempt(async () => {
      await api.markDuplicate(project.id, { req_a_id: Number(manual.a), req_b_id: Number(manual.b) });
      setManual({ a: "", b: "" });
      await reload();
      reloadProject();
    });
  };
  const active = (requirements || []).filter((row) => row.status !== "rejected");
  const options = active.map((row) => <option key={row.id} value={row.id}>REQ-{row.id}: {row.text}</option>);

  return (
    <>
      <PageHeader title="Potential duplicates" subtitle="Pairs with similar meaning, based on sentence embeddings and cosine similarity." />
      <Notice>High similarity does not prove duplication, and two requirements with similar wording can mean opposite things. Nothing is merged or deleted automatically, so please decide for each pair.</Notice>
      <ErrorBanner message={error} onClose={() => setError("")} />

      <div className="card mb-4 flex flex-wrap items-end gap-4 p-4">
        <div className="min-w-[14rem] flex-1">
          <label htmlFor="threshold" className="mb-1 flex justify-between text-sm font-medium">
            Similarity threshold <span className="tabular-nums text-slate-600">{Number(threshold).toFixed(2)}</span>
          </label>
          <input id="threshold" type="range" min="0.3" max="1" step="0.01" className="w-full accent-slate-700" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
          <p className="mt-1 text-xs text-slate-500">A lower value finds more pairs but gives more false alarms.</p>
        </div>
        <button className="btn" onClick={rerun} disabled={running}><RefreshCw className="h-4 w-4" /> Apply threshold</button>
      </div>

      {loading ? <Spinner /> : !pairs?.length ? (
        <EmptyState icon={Copy} title="No potential duplicates" text="None were found at this threshold. This does not guarantee that the requirements are all different. If the analysis has not run yet, start it from Overview." />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[860px]">
            <thead className="border-b border-slate-200">
              <tr><th className="th">Requirement A</th><th className="th">Requirement B</th><th className="th">Score</th><th className="th">Reason for review</th><th className="th">Decision</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {pairs.map((pair) => (
                <tr key={pair.id} className={pair.status === "dismissed" ? "opacity-60" : ""}>
                  <td className="td"><span className="block text-xs text-slate-500">REQ-{pair.req_a_id}</span>{pair.text_a}</td>
                  <td className="td"><span className="block text-xs text-slate-500">REQ-{pair.req_b_id}</span>{pair.text_b}</td>
                  <td className="td font-medium tabular-nums">{pair.score.toFixed(2)}</td>
                  <td className="td text-slate-600">{pair.reason}</td>
                  <td className="td w-44 space-y-1.5">
                    <StatusBadge status={pair.status} />
                    <ReviewButtons status={pair.status} acceptValue="confirmed" rejectValue="dismissed" acceptLabel="Duplicate" rejectLabel="Different" onChange={(status) => setStatus(pair, status)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {active.length >= 2 && (
        <form className="card mt-4 p-4" onSubmit={mark}>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Mark a duplicate that was missed</h3>
          <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
            <select className="input" aria-label="First requirement" value={manual.a} onChange={(e) => setManual({ ...manual, a: e.target.value })}>
              <option value="">Choose a requirement</option>{options}
            </select>
            <select className="input" aria-label="Second requirement" value={manual.b} onChange={(e) => setManual({ ...manual, b: e.target.value })}>
              <option value="">Choose a requirement</option>{options}
            </select>
            <button className="btn" disabled={!manual.a || !manual.b || manual.a === manual.b}>Mark as duplicate</button>
          </div>
        </form>
      )}
    </>
  );
}

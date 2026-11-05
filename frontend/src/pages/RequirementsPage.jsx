import { useMemo, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { ClipboardList, ExternalLink, Pencil, Plus, Save, X } from "lucide-react";
import { api } from "../api";
import { useLoad } from "../useLoad";
import { CATEGORIES, capitalize, TYPE_LABELS } from "../labels";
import { Badge, EmptyState, ErrorBanner, PageHeader, ReviewButtons, Spinner, StatusBadge } from "../components/ui";

const LOW_CONFIDENCE = 0.65;

function TypeEditor({ row, onChange }) {
  return (
    <div className="space-y-1">
      <select className="input py-1 text-xs" aria-label="Requirement type" value={row.req_type || ""}
        onChange={(e) => onChange({ req_type: e.target.value, nfr_category: e.target.value === "functional" ? null : row.nfr_category || "other" })}>
        {!row.req_type && <option value="">Unclassified</option>}
        <option value="functional">Functional</option>
        <option value="non_functional">Non-functional</option>
      </select>
      {row.req_type === "non_functional" && (
        <select className="input py-1 text-xs" aria-label="Category" value={row.nfr_category || "other"} onChange={(e) => onChange({ nfr_category: e.target.value })}>
          {CATEGORIES.map((category) => <option key={category} value={category}>{capitalize(category)}</option>)}
        </select>
      )}
    </div>
  );
}

function ClassifierNote({ row }) {
  if (row.confidence == null) return null;
  const percent = Math.round(row.confidence * 100);
  const predicted = TYPE_LABELS[row.predicted_type];
  if (row.type_overridden && row.predicted_type !== row.req_type) {
    return <p className="mt-1 text-xs text-slate-500">Changed by you. The classifier said {predicted} ({percent}%).</p>;
  }
  return <p className={`mt-1 text-xs ${row.confidence < LOW_CONFIDENCE ? "font-medium text-amber-700" : "text-slate-500"}`}>
    Classifier: {percent}%{row.confidence < LOW_CONFIDENCE ? ", please check" : ""}
  </p>;
}

function RequirementRow({ row, projectId, onSave }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(row.text);

  const saveText = async () => {
    if (await onSave(row.id, { text })) setEditing(false);
  };
  const sourceLink = row.document_id
    ? `/projects/${projectId}/source?document=${row.document_id}&start=${row.source_start}&end=${row.source_end}`
    : null;

  return (
    <tr className={row.status === "rejected" ? "bg-slate-50 opacity-60" : ""}>
      <td className="td whitespace-nowrap text-xs tabular-nums text-slate-500">REQ-{row.id}</td>
      <td className="td min-w-[18rem]">
        {editing ? (
          <div className="space-y-2">
            <textarea className="input" rows={2} autoFocus aria-label="Requirement text" value={text} onChange={(e) => setText(e.target.value)} />
            <div className="flex gap-1">
              <button className="btn btn-sm btn-primary" onClick={saveText} disabled={text.trim().length < 3}><Save className="h-3 w-3" /> Save</button>
              <button className="btn btn-sm" onClick={() => { setEditing(false); setText(row.text); }}><X className="h-3 w-3" /> Cancel</button>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-1.5">
            <span className="flex-1 text-slate-900">{row.text}</span>
            <button className="shrink-0 text-slate-400 hover:text-slate-700" onClick={() => setEditing(true)} aria-label={`Edit requirement ${row.id}`}><Pencil className="h-3.5 w-3.5" /></button>
          </div>
        )}
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
          {row.origin === "human" && <Badge>Added by you</Badge>}
          {row.edited && <Badge title={`AI wording: ${row.original_text}`}>Edited</Badge>}
          {sourceLink && (
            <Link to={sourceLink} title={row.source_sentence} className="inline-flex max-w-full items-center gap-1 hover:text-slate-800">
              <ExternalLink className="h-3 w-3 shrink-0" /> <span className="truncate italic">{row.source_sentence}</span>
            </Link>
          )}
        </div>
      </td>
      <td className="td w-44">
        <TypeEditor row={row} onChange={(changes) => onSave(row.id, changes)} />
        <ClassifierNote row={row} />
      </td>
      <td className="td w-32"><StatusBadge status={row.status} /></td>
      <td className="td w-40"><ReviewButtons status={row.status} onChange={(status) => onSave(row.id, { status })} /></td>
    </tr>
  );
}

export default function RequirementsPage() {
  const { project, reloadProject } = useOutletContext();
  const { data: rows, setData, error, setError, loading } = useLoad(() => api.listRequirements(project.id), [project.id]);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [adding, setAdding] = useState(false);
  const [newText, setNewText] = useState("");
  const [newType, setNewType] = useState("functional");

  const visible = useMemo(() => (rows || []).filter((row) => {
    const matchesFilter = filter === "all" || row.req_type === filter || row.status === filter;
    return matchesFilter && row.text.toLowerCase().includes(search.toLowerCase());
  }), [rows, filter, search]);

  async function save(id, changes) {
    try {
      const updated = await api.updateRequirement(id, changes);
      setData((current) => current.map((row) => (row.id === id ? updated : row)));
      reloadProject();
      return true;
    } catch (problem) {
      setError(problem.message);
      return false;
    }
  }

  async function add(event) {
    event.preventDefault();
    try {
      const created = await api.addRequirement(project.id, {
        text: newText, req_type: newType, nfr_category: newType === "non_functional" ? "other" : null,
      });
      setData((current) => [...current, created]);
      setNewText("");
      setAdding(false);
      reloadProject();
    } catch (problem) {
      setError(problem.message);
    }
  }

  return (
    <>
      <PageHeader title="Requirements" subtitle="Check each extracted requirement. Edit the wording, correct its classification, and accept or reject it. Nothing here is approved until you accept it.">
        <button className="btn" onClick={() => setAdding(!adding)}><Plus className="h-4 w-4" /> Add requirement</button>
      </PageHeader>
      <ErrorBanner message={error} onClose={() => setError("")} />

      {adding && (
        <form className="card mb-4 flex flex-wrap items-end gap-2 p-4" onSubmit={add}>
          <div className="min-w-[16rem] flex-1">
            <label className="mb-1 block text-sm font-medium" htmlFor="new-requirement">New requirement</label>
            <input id="new-requirement" className="input" autoFocus value={newText} onChange={(e) => setNewText(e.target.value)} />
          </div>
          <select className="input w-auto" aria-label="Type" value={newType} onChange={(e) => setNewType(e.target.value)}>
            <option value="functional">Functional</option>
            <option value="non_functional">Non-functional</option>
          </select>
          <button className="btn btn-primary" disabled={newText.trim().length < 3}>Add</button>
        </form>
      )}

      {loading ? <Spinner /> : !rows?.length ? (
        <EmptyState icon={ClipboardList} title="No requirements yet" text="Add source text and run the analysis, or add a requirement by hand.">
          <Link className="btn" to={`/projects/${project.id}/source`}>Go to source text</Link>
        </EmptyState>
      ) : (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <input className="input max-w-xs" placeholder="Search requirements" aria-label="Search requirements" value={search} onChange={(e) => setSearch(e.target.value)} />
            <select className="input w-auto" aria-label="Filter" value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">All</option>
              <option value="functional">Functional</option>
              <option value="non_functional">Non-functional</option>
              <option value="pending">Unreviewed</option>
              <option value="accepted">Accepted</option>
              <option value="rejected">Rejected</option>
            </select>
            <span className="text-sm text-slate-500">{visible.length} shown</span>
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full min-w-[860px]">
              <thead className="border-b border-slate-200">
                <tr>
                  <th className="th">ID</th><th className="th">Requirement and source</th><th className="th">Classification</th><th className="th">Status</th><th className="th">Review</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {visible.map((row) => <RequirementRow key={row.id} row={row} projectId={project.id} onSave={save} />)}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}

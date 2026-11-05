import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FolderKanban, Pencil, Plus, Sparkles, Trash2 } from "lucide-react";
import { api } from "../api";
import { useLoad } from "../useLoad";
import { EmptyState, ErrorBanner, PageHeader, Spinner } from "../components/ui";

function ProjectForm({ initial = { name: "", description: "" }, submitLabel, onSubmit, onCancel }) {
  const [form, setForm] = useState(initial);
  return (
    <form
      className="card mb-5 space-y-3 p-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(form);
      }}
    >
      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="project-name">Project name</label>
        <input id="project-name" className="input" required maxLength={200} autoFocus value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="project-description">Description (optional)</label>
        <input id="project-description" className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </div>
      <div className="flex gap-2">
        <button className="btn btn-primary" disabled={!form.name.trim()}>{submitLabel}</button>
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

export default function ProjectsPage() {
  const { data: projects, error, setError, loading, reload } = useLoad(api.listProjects);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function attempt(action) {
    setBusy(true);
    try {
      await action();
    } catch (problem) {
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }

  const create = (form) => attempt(async () => {
    const project = await api.createProject(form);
    navigate(`/projects/${project.id}/source`);
  });
  const createSample = () => attempt(async () => {
    const project = await api.createSample();
    navigate(`/projects/${project.id}`);
  });
  const save = (form) => attempt(async () => {
    await api.updateProject(editing.id, form);
    setEditing(null);
    await reload();
  });
  const remove = (project) => {
    if (!window.confirm(`Delete "${project.name}" and all its results? This cannot be undone.`)) return;
    attempt(async () => {
      await api.deleteProject(project.id);
      await reload();
    });
  };

  return (
    <>
      <PageHeader title="Projects" subtitle="Turn client requirement text into structured, reviewed software requirements.">
        <button className="btn" onClick={createSample} disabled={busy}><Sparkles className="h-4 w-4" /> Sample project</button>
        <button className="btn btn-primary" onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New project</button>
      </PageHeader>
      <ErrorBanner message={error} onClose={() => setError("")} />
      {creating && <ProjectForm submitLabel="Create project" onSubmit={create} onCancel={() => setCreating(false)} />}
      {editing && <ProjectForm key={editing.id} initial={{ name: editing.name, description: editing.description || "" }} submitLabel="Save changes" onSubmit={save} onCancel={() => setEditing(null)} />}

      {loading ? <Spinner /> : !projects?.length ? (
        <EmptyState icon={FolderKanban} title="No projects yet" text="Create a project and paste your client's requirements, or try the built-in sample.">
          <button className="btn" onClick={createSample} disabled={busy}><Sparkles className="h-4 w-4" /> Open the sample</button>
          <button className="btn btn-primary" onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New project</button>
        </EmptyState>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead className="border-b border-slate-200">
              <tr>
                <th className="th">Project</th>
                <th className="th text-right">Requirements</th>
                <th className="th text-right">Functional</th>
                <th className="th text-right">Non-functional</th>
                <th className="th text-right">Duplicates</th>
                <th className="th text-right">Warnings</th>
                <th className="th text-right">Reviewed</th>
                <th className="th"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {projects.map((project) => (
                <tr key={project.id} className="hover:bg-slate-50">
                  <td className="td">
                    <Link className="font-medium text-slate-900 hover:underline" to={`/projects/${project.id}`}>{project.name}</Link>
                    {project.description && <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">{project.description}</p>}
                  </td>
                  <td className="td text-right tabular-nums">{project.stats.total}</td>
                  <td className="td text-right tabular-nums">{project.stats.functional}</td>
                  <td className="td text-right tabular-nums">{project.stats.non_functional}</td>
                  <td className="td text-right tabular-nums">{project.stats.duplicates}</td>
                  <td className="td text-right tabular-nums">{project.stats.warnings}</td>
                  <td className="td text-right tabular-nums">{project.stats.reviewed}/{project.stats.all_requirements}</td>
                  <td className="td whitespace-nowrap text-right">
                    <button className="btn btn-sm mr-1" onClick={() => setEditing(project)} aria-label={`Edit ${project.name}`}><Pencil className="h-3 w-3" /></button>
                    <button className="btn btn-sm btn-danger" onClick={() => remove(project)} aria-label={`Delete ${project.name}`} disabled={busy}><Trash2 className="h-3 w-3" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

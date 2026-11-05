import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { ListChecks, Pencil, Save, X } from "lucide-react";
import { api } from "../api";
import { useLoad } from "../useLoad";
import { Badge, EmptyState, ErrorBanner, Notice, PageHeader, ReviewButtons, Spinner, StatusBadge } from "../components/ui";

function StoryEditor({ story, onSave, onCancel }) {
  const [form, setForm] = useState({
    role: story.role, feature: story.feature, benefit: story.benefit,
    criteria: (story.acceptance_criteria || []).join("\n"),
  });
  const field = (name, label) => (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor={`${name}-${story.id}`}>{label}</label>
      <input id={`${name}-${story.id}`} className="input" value={form[name]} onChange={(e) => setForm({ ...form, [name]: e.target.value })} />
    </div>
  );
  const valid = form.role.trim() && form.feature.trim() && form.benefit.trim();
  return (
    <div className="mt-3 space-y-2">
      {field("role", "As a")}
      {field("feature", "I want to")}
      {field("benefit", "So that")}
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor={`criteria-${story.id}`}>Acceptance criteria (one per line)</label>
        <textarea id={`criteria-${story.id}`} className="input" rows={3} value={form.criteria} onChange={(e) => setForm({ ...form, criteria: e.target.value })} />
      </div>
      <div className="flex gap-1">
        <button className="btn btn-sm btn-primary" disabled={!valid} onClick={() => onSave({
          role: form.role.trim(), feature: form.feature.trim(), benefit: form.benefit.trim(),
          acceptance_criteria: form.criteria.split("\n").map((line) => line.trim()).filter(Boolean),
        })}><Save className="h-3 w-3" /> Save</button>
        <button className="btn btn-sm" onClick={onCancel}><X className="h-3 w-3" /> Cancel</button>
      </div>
    </div>
  );
}

function StoryCard({ story, onSave }) {
  const [editing, setEditing] = useState(false);
  const save = async (changes) => {
    if (await onSave(story.id, changes)) setEditing(false);
  };
  return (
    <div className={`card p-4 ${story.status === "rejected" ? "opacity-60" : ""}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <StatusBadge status={story.status} />
          {story.status === "pending" && <Badge tone="violet">AI draft</Badge>}
          {story.role_inferred && <Badge tone="amber" title="The source did not name this role.">Role inferred</Badge>}
          {story.edited && <Badge>Edited</Badge>}
        </div>
        <div className="flex gap-1">
          <button className="btn btn-sm" onClick={() => setEditing(!editing)}><Pencil className="h-3 w-3" /> Edit</button>
          <ReviewButtons status={story.status} onChange={(status) => onSave(story.id, { status })} />
        </div>
      </div>
      <p className="mt-3 text-sm font-medium text-slate-900">{story.sentence}</p>
      <p className="mt-1 text-xs text-slate-500">From REQ-{story.requirement_id}: {story.requirement_text}</p>
      {editing ? <StoryEditor story={story} onSave={save} onCancel={() => setEditing(false)} /> : (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Draft acceptance criteria</p>
          {story.acceptance_criteria?.length ? (
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700">
              {story.acceptance_criteria.map((item, index) => <li key={index}>{item}</li>)}
            </ul>
          ) : <p className="mt-1 text-sm text-slate-500">None passed the checks. Please write them by hand with Edit.</p>}
        </div>
      )}
    </div>
  );
}

export default function StoriesPage() {
  const { project, reloadProject } = useOutletContext();
  const { data: stories, setData, error, setError, loading } = useLoad(() => api.listStories(project.id), [project.id]);

  async function save(id, changes) {
    try {
      const updated = await api.updateStory(id, changes);
      setData((current) => current.map((row) => {
        if (row.id !== id) return row;
        const merged = { ...row, ...updated };
        const article = /^[aeio]/i.test(merged.role) ? "an" : "a";
        return { ...merged, sentence: `As ${article} ${merged.role}, I want to ${merged.feature}, so that ${merged.benefit}.` };
      }));
      reloadProject();
      return true;
    } catch (problem) {
      setError(problem.message);
      return false;
    }
  }

  return (
    <>
      <PageHeader title="User stories" subtitle="Draft stories for functional requirements." />
      <Notice>These are AI drafts. The client did not state the benefits or acceptance criteria, and accepting a story here does not mean the client has approved it.</Notice>
      <ErrorBanner message={error} onClose={() => setError("")} />
      {loading ? <Spinner /> : !stories?.length ? (
        <EmptyState icon={ListChecks} title="No user stories yet" text="Stories are drafted for functional requirements when the analysis runs. Start it from Overview." />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {stories.map((story) => <StoryCard key={story.id} story={story} onSave={save} />)}
        </div>
      )}
    </>
  );
}

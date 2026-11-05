import { useOutletContext } from "react-router-dom";
import { AlertTriangle, CheckSquare, ClipboardList, Copy, Gauge, Wrench } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { useLoad } from "../useLoad";
import AnalyzePanel from "../components/AnalyzePanel";
import { capitalize, KIND_LABELS } from "../labels";
import { PageHeader } from "../components/ui";

const SERIES_COLOR = "#2a78d6";

function Stat({ icon: Icon, label, value, note }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-sm text-slate-500"><Icon className="h-4 w-4" /> {label}</div>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      {note && <p className="mt-0.5 text-xs text-slate-500">{note}</p>}
    </div>
  );
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs shadow-sm">
      <span className="text-slate-600">{payload[0].payload.name}: </span>
      <span className="font-semibold text-slate-900">{payload[0].value}</span>
    </div>
  );
}

function CountChart({ title, rows, empty }) {
  return (
    <div className="card p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {rows.length === 0 ? <p className="py-8 text-center text-sm text-slate-500">{empty}</p> : (
        <ResponsiveContainer width="100%" height={Math.max(120, rows.length * 38)}>
          <BarChart data={rows} layout="vertical" margin={{ left: 0, right: 24, top: 0, bottom: 0 }} barCategoryGap={10}>
            <XAxis type="number" hide allowDecimals={false} domain={[0, "dataMax"]} />
            <YAxis type="category" dataKey="name" width={150} tickLine={false} axisLine={{ stroke: "#e2e8f0" }} tick={{ fontSize: 12, fill: "#475569" }} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f1f5f9" }} />
            <Bar dataKey="value" fill={SERIES_COLOR} radius={[0, 4, 4, 0]} maxBarSize={20} isAnimationActive={false}
              label={{ position: "right", fontSize: 12, fill: "#334155" }} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default function OverviewPage() {
  const { project } = useOutletContext();
  const { data: documents } = useLoad(() => api.listDocuments(project.id), [project.id]);
  const stats = project.stats;
  const percent = stats.all_requirements ? Math.round((stats.reviewed / stats.all_requirements) * 100) : 0;
  const toRows = (counts, label) => Object.entries(counts).map(([key, value]) => ({ name: label(key), value })).sort((a, b) => b.value - a.value);

  return (
    <>
      <PageHeader title={project.name} subtitle={project.description} />
      <AnalyzePanel hasSource={documents === null || documents.length > 0 || stats.all_requirements > 0} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat icon={ClipboardList} label="Requirements" value={stats.total} note={stats.rejected ? `${stats.rejected} rejected, not counted` : undefined} />
        <Stat icon={Wrench} label="Functional" value={stats.functional} />
        <Stat icon={Gauge} label="Non-functional" value={stats.non_functional} />
        <Stat icon={Copy} label="Potential duplicates" value={stats.duplicates} />
        <Stat icon={AlertTriangle} label="Quality warnings" value={stats.warnings} />
      </div>

      <div className="card mt-3 p-4">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="flex items-center gap-2 font-semibold text-slate-700"><CheckSquare className="h-4 w-4" /> Review progress</span>
          <span className="tabular-nums text-slate-600">{stats.reviewed} of {stats.all_requirements} requirements reviewed ({percent}%)</span>
        </div>
        <div className="h-2 overflow-hidden rounded bg-slate-100" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label="Review progress">
          <div className="h-full rounded bg-slate-700" style={{ width: `${percent}%` }} />
        </div>
        <p className="mt-2 text-xs text-slate-500">
          {stats.accepted} accepted, {stats.rejected} rejected. {stats.stories_accepted} of {stats.stories} user stories accepted.
        </p>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <CountChart title="Non-functional requirements by category" rows={toRows(stats.categories, capitalize)} empty="No non-functional requirements yet." />
        <CountChart title="Quality warnings by kind" rows={toRows(stats.issue_kinds, (kind) => KIND_LABELS[kind] || kind)} empty="No quality warnings yet." />
      </div>
    </>
  );
}

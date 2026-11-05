import { AlertCircle, Check, CheckCircle2, Clock, Loader2, RotateCcw, X, XCircle } from "lucide-react";

export function Spinner({ label = "Loading" }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-slate-500" role="status">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}
    </div>
  );
}

export function ErrorBanner({ message, onClose }) {
  if (!message) return null;
  return (
    <div className="mb-4 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span className="flex-1 whitespace-pre-wrap break-words">{message}</span>
      {onClose && (
        <button onClick={onClose} aria-label="Dismiss" className="text-red-700 hover:text-red-900"><X className="h-4 w-4" /></button>
      )}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, text, children }) {
  return (
    <div className="card flex flex-col items-center px-6 py-12 text-center">
      {Icon && <Icon className="mb-3 h-8 w-8 text-slate-400" />}
      <h3 className="font-semibold text-slate-700">{title}</h3>
      {text && <p className="mt-1 max-w-md text-sm text-slate-500">{text}</p>}
      {children && <div className="mt-4 flex flex-wrap justify-center gap-2">{children}</div>}
    </div>
  );
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        {subtitle && <p className="mt-0.5 max-w-3xl text-sm text-slate-500">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}

export function Badge({ tone = "slate", children, title }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    blue: "bg-blue-50 text-blue-700",
    violet: "bg-violet-50 text-violet-700",
    green: "bg-emerald-50 text-emerald-700",
    red: "bg-red-50 text-red-700",
    amber: "bg-amber-50 text-amber-800",
  };
  return (
    <span title={title} className={`inline-flex items-center gap-1 whitespace-nowrap rounded px-1.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

// Review states always use an icon and a word, never colour alone.
const STATUS = {
  pending: { tone: "amber", icon: Clock, label: "Unreviewed" },
  accepted: { tone: "green", icon: CheckCircle2, label: "Accepted" },
  confirmed: { tone: "green", icon: CheckCircle2, label: "Confirmed duplicate" },
  rejected: { tone: "red", icon: XCircle, label: "Rejected" },
  dismissed: { tone: "slate", icon: XCircle, label: "Dismissed" },
};

export function StatusBadge({ status }) {
  const { tone, icon: Icon, label } = STATUS[status] || STATUS.pending;
  return <Badge tone={tone}><Icon className="h-3 w-3" /> {label}</Badge>;
}

export function OriginBadge({ origin }) {
  if (origin === "rule") return <Badge tone="slate" title="Found by a fixed rule">Rule</Badge>;
  return <Badge tone="violet" title="Suggested by the local LLM. It may be wrong.">LLM suggestion</Badge>;
}

// Accept, reject and undo buttons used on each review page.
export function ReviewButtons({ status, onChange, acceptValue = "accepted", rejectValue = "rejected", acceptLabel = "Accept", rejectLabel = "Reject" }) {
  if (status !== "pending") {
    return (
      <button className="btn btn-sm" onClick={() => onChange("pending")}>
        <RotateCcw className="h-3 w-3" /> Undo
      </button>
    );
  }
  return (
    <div className="flex gap-1">
      <button className="btn btn-sm" onClick={() => onChange(acceptValue)}><Check className="h-3 w-3" /> {acceptLabel}</button>
      <button className="btn btn-sm" onClick={() => onChange(rejectValue)}><X className="h-3 w-3" /> {rejectLabel}</button>
    </div>
  );
}

export function Notice({ children }) {
  return <p className="mb-4 rounded-md border border-slate-200 bg-slate-100 px-3 py-2 text-sm text-slate-600">{children}</p>;
}

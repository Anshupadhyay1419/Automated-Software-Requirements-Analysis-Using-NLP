import { useEffect, useState } from "react";
import { NavLink, Outlet, useMatch } from "react-router-dom";
import { AlertTriangle, BarChart3, ClipboardList, Copy, Download, FileText, FolderKanban, LayoutDashboard, ListChecks, Menu, Settings, X } from "lucide-react";
import { api } from "../api";

function Item({ to, icon: Icon, children, end, onNavigate }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className={({ isActive }) =>
        `flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm font-medium ${
          isActive ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
        }`
      }
    >
      <Icon className="h-4 w-4 shrink-0" /> {children}
    </NavLink>
  );
}

function ProjectNav({ id, onNavigate }) {
  const base = `/projects/${id}`;
  const links = [
    ["", LayoutDashboard, "Overview"],
    ["/source", FileText, "Source text"],
    ["/requirements", ClipboardList, "Requirements"],
    ["/duplicates", Copy, "Duplicates"],
    ["/quality", AlertTriangle, "Quality"],
    ["/stories", ListChecks, "User stories"],
    ["/export", Download, "Export"],
  ];
  return (
    <div className="mt-5">
      <p className="mb-1 px-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Current project</p>
      <div className="space-y-0.5">
        {links.map(([path, icon, label]) => (
          <Item key={label} to={base + path} icon={icon} end={path === ""} onNavigate={onNavigate}>{label}</Item>
        ))}
      </div>
    </div>
  );
}

function OllamaStatus() {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    const check = () => api.systemStatus().then(setStatus).catch(() => setStatus({ failed: true }));
    check();
    const timer = setInterval(check, 15000);
    return () => clearInterval(timer);
  }, []);

  if (!status) return null;
  const ready = status.active_model;
  const label = status.failed ? "Backend offline" : ready ? status.active_model : status.ollama_running ? "Model missing" : "Ollama offline";
  return (
    <NavLink to="/settings" className="block border-t border-slate-800 px-4 py-3 text-xs text-slate-400 hover:text-white">
      <span className="flex items-center gap-2">
        {ready ? <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-400" /> : <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400" />}
        <span className="truncate" title={label}>{label}</span>
      </span>
    </NavLink>
  );
}

export default function Layout() {
  const [open, setOpen] = useState(false);
  const match = useMatch("/projects/:projectId/*");
  const close = () => setOpen(false);

  return (
    <div className="flex min-h-screen">
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-56 flex-col bg-slate-900 transition-transform md:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-base font-semibold text-white">ReqLens</h1>
            <p className="text-xs text-slate-400">Requirements analysis</p>
          </div>
          <button className="text-slate-400 md:hidden" onClick={close} aria-label="Close menu"><X className="h-5 w-5" /></button>
        </div>
        <nav className="flex-1 overflow-y-auto px-2">
          <div className="space-y-0.5">
            <Item to="/" icon={FolderKanban} end onNavigate={close}>Projects</Item>
          </div>
          {match && <ProjectNav id={match.params.projectId} onNavigate={close} />}
          <div className="mt-5">
            <p className="mb-1 px-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500">System</p>
            <div className="space-y-0.5">
              <Item to="/model" icon={BarChart3} onNavigate={close}>Classifier results</Item>
              <Item to="/settings" icon={Settings} onNavigate={close}>Settings</Item>
            </div>
          </div>
        </nav>
        <OllamaStatus />
      </aside>
      {open && <div className="fixed inset-0 z-20 bg-slate-900/40 md:hidden" onClick={close} />}

      <div className="min-w-0 flex-1 md:ml-56">
        <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2 md:hidden">
          <button onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
          <span className="font-semibold">ReqLens</span>
        </div>
        <main className="mx-auto max-w-6xl px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

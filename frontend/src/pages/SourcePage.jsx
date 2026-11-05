import { useRef, useState } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { FileText, Loader2, Trash2, Upload } from "lucide-react";
import { api } from "../api";
import { useLoad } from "../useLoad";
import AnalyzePanel from "../components/AnalyzePanel";
import { EmptyState, ErrorBanner, PageHeader, Spinner } from "../components/ui";

// Shows a document's original text. If the URL has a position, that sentence is highlighted.
function DocumentView({ document, start, end }) {
  const highlight = start !== null && end !== null && start < end;
  return (
    <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words p-4 font-sans text-sm leading-relaxed text-slate-700">
      {highlight ? (
        <>
          {document.text.slice(0, start)}
          <mark ref={(node) => node?.scrollIntoView({ block: "center" })} className="rounded bg-amber-200 px-0.5 text-slate-900">{document.text.slice(start, end)}</mark>
          {document.text.slice(end)}
        </>
      ) : document.text}
    </pre>
  );
}

export default function SourcePage() {
  const { project, reloadProject } = useOutletContext();
  const { data: documents, error, setError, loading, reload } = useLoad(() => api.listDocuments(project.id), [project.id]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInput = useRef(null);
  const [params] = useSearchParams();
  const focusId = Number(params.get("document")) || null;
  const number = (name) => (params.get(name) === null ? null : Number(params.get(name)));

  async function attempt(action) {
    setBusy(true);
    setError("");
    try {
      await action();
      await reload();
      await reloadProject();
    } catch (problem) {
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }

  const addText = () => attempt(async () => {
    await api.addText(project.id, text);
    setText("");
  });
  const upload = (event) => {
    const file = event.target.files[0];
    event.target.value = "";
    if (file) attempt(() => api.uploadFile(project.id, file));
  };
  const remove = (document) => {
    if (window.confirm(`Remove "${document.filename}" and all requirements extracted from it? This cannot be undone.`)) {
      attempt(() => api.deleteDocument(document.id));
    }
  };

  return (
    <>
      <PageHeader title="Source text" subtitle="Add the client's requirements by pasting text or uploading a TXT, PDF or DOCX file (10 MB maximum). Scanned PDFs are not supported." />
      <ErrorBanner message={error} onClose={() => setError("")} />

      <div className="card mb-5 p-4">
        <label className="mb-1 block text-sm font-medium" htmlFor="source-text">Paste requirements</label>
        <textarea id="source-text" className="input min-h-[8rem] resize-y" placeholder="For example: Users should register, log in, search products, and place orders." value={text} onChange={(e) => setText(e.target.value)} />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button className="btn btn-primary" disabled={busy || !text.trim()} onClick={addText}>Add text</button>
          <button className="btn" disabled={busy} onClick={() => fileInput.current.click()}><Upload className="h-4 w-4" /> Upload file</button>
          <input ref={fileInput} type="file" accept=".txt,.pdf,.docx" className="hidden" onChange={upload} aria-label="Upload a document" />
          {busy && <Loader2 className="h-4 w-4 animate-spin text-slate-500" />}
        </div>
      </div>

      {documents?.length > 0 && <AnalyzePanel hasSource />}

      {loading ? <Spinner /> : !documents?.length ? (
        <EmptyState icon={FileText} title="No source text yet" text="Paste some text or upload a file above to get started." />
      ) : (
        <div className="space-y-4">
          {documents.map((document) => (
            <div key={document.id} className="card">
              <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-4 py-2.5">
                <div className="flex min-w-0 items-center gap-2 text-sm font-medium">
                  <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                  <span className="truncate">{document.filename}</span>
                  <span className="shrink-0 font-normal text-slate-500">{document.text.split(/\s+/).length} words</span>
                </div>
                <button className="btn btn-sm btn-danger" onClick={() => remove(document)} disabled={busy} aria-label={`Remove ${document.filename}`}><Trash2 className="h-3 w-3" /></button>
              </div>
              <DocumentView document={document} start={focusId === document.id ? number("start") : null} end={focusId === document.id ? number("end") : null} />
            </div>
          ))}
        </div>
      )}
    </>
  );
}

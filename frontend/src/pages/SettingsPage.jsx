import { CheckCircle2, RefreshCw, TriangleAlert } from "lucide-react";
import { api } from "../api";
import { useLoad } from "../useLoad";
import { ErrorBanner, PageHeader, Spinner } from "../components/ui";

export default function SettingsPage() {
  const { data: status, error, setError, loading, reload } = useLoad(api.systemStatus);

  async function choose(model) {
    try {
      await api.chooseModel(model);
      await reload();
    } catch (problem) {
      setError(problem.message);
    }
  }

  return (
    <>
      <PageHeader title="Settings" subtitle="The local model used for extraction, quality review and user stories. Nothing is sent to the cloud.">
        <button className="btn" onClick={reload}><RefreshCw className="h-4 w-4" /> Check again</button>
      </PageHeader>
      <ErrorBanner message={error} onClose={() => setError("")} />
      {loading ? <Spinner /> : status && (
        <div className="space-y-4">
          <div className="card p-4">
            <h3 className="flex items-center gap-2 font-semibold text-slate-800">
              {status.active_model ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <TriangleAlert className="h-4 w-4 text-amber-600" />}
              {status.active_model ? "Ollama is ready" : status.ollama_running ? "No suitable model is available" : "Ollama is not running"}
            </h3>
            <p className="mt-1 text-sm text-slate-600">{status.active_model ? <>Using <code className="font-medium">{status.active_model}</code> at {status.ollama_url}</> : status.message}</p>
            {!status.active_model && (
              <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-700">
                <li>Install Ollama from <code>ollama.com</code>, if you have not already.</li>
                <li>Start it with <code className="rounded bg-slate-100 px-1">ollama serve</code>.</li>
                <li>Download the model with <code className="rounded bg-slate-100 px-1">ollama pull {status.recommended_model}</code>.</li>
                <li>Select Check again above.</li>
              </ol>
            )}
          </div>
          {status.ollama_running && (
            <div className="card p-4">
              <label htmlFor="model" className="mb-1 block text-sm font-medium">Model</label>
              <select id="model" className="input max-w-md" value={status.selected_model} onChange={(e) => choose(e.target.value)}>
                <option value="">Automatic (prefer a Qwen instruct model)</option>
                {status.models.map((model) => <option key={model} value={model}>{model}</option>)}
              </select>
              <p className="mt-2 text-xs text-slate-500">This app was tested with {status.recommended_model}. Other models may give different results.</p>
            </div>
          )}
          <div className="card p-4">
            <h3 className="font-semibold text-slate-800">Classifier</h3>
            <p className="mt-1 text-sm text-slate-600">
              {status.classifier_trained ? "The trained model files were found." : <>Not trained yet. Run <code className="rounded bg-slate-100 px-1">python backend/training/train.py</code>.</>}
            </p>
          </div>
        </div>
      )}
    </>
  );
}

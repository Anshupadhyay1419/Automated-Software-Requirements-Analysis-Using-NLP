import { useState } from "react";
import { BarChart3 } from "lucide-react";
import { api } from "../api";
import { useLoad } from "../useLoad";
import { capitalize, TYPE_LABELS } from "../labels";
import { EmptyState, ErrorBanner, Notice, PageHeader, Spinner } from "../components/ui";

const percent = (value) => `${(value * 100).toFixed(1)}%`;
const name = (label) => TYPE_LABELS[label] || capitalize(label);

function Metrics({ title, note, scores }) {
  const metrics = [
    ["Accuracy", scores.accuracy], ["Precision (macro)", scores.precision_macro],
    ["Recall (macro)", scores.recall_macro], ["F1 (macro)", scores.f1_macro],
  ];
  const largest = Math.max(...scores.confusion_matrix.flat(), 1);
  return (
    <div className="card p-4">
      <h3 className="font-semibold text-slate-800">{title}</h3>
      <p className="mt-0.5 text-sm text-slate-500">{note} {scores.test_rows} test rows.</p>
      <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="text-lg font-semibold tabular-nums text-slate-900">{percent(value)}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 overflow-x-auto">
        <table className="text-xs">
          <caption className="mb-1 text-left text-xs font-semibold text-slate-600">Confusion matrix (rows show the true label, columns show the prediction)</caption>
          <thead>
            <tr>
              <th />
              {scores.labels.map((label) => <th key={label} scope="col" className="px-2 py-1 font-medium text-slate-500">{name(label)}</th>)}
            </tr>
          </thead>
          <tbody>
            {scores.confusion_matrix.map((row, rowIndex) => (
              <tr key={rowIndex}>
                <th scope="row" className="whitespace-nowrap py-1 pr-2 text-right font-medium text-slate-500">{name(scores.labels[rowIndex])}</th>
                {row.map((count, columnIndex) => {
                  const strength = count / largest;
                  return (
                    <td key={columnIndex} className="border-2 border-white px-3 py-1.5 text-center font-medium tabular-nums"
                      title={`True ${name(scores.labels[rowIndex])}, predicted ${name(scores.labels[columnIndex])}: ${count}`}
                      style={{ backgroundColor: `rgba(42, 120, 214, ${strength * 0.75})`, color: strength > 0.55 ? "#fff" : "#1e293b" }}>
                      {count}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TryIt() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      setResult(await api.predict(text));
    } catch (problem) {
      setError(problem.message);
    }
  }
  return (
    <form className="card p-4" onSubmit={submit}>
      <h3 className="mb-2 font-semibold text-slate-800">Try the classifier</h3>
      <ErrorBanner message={error} />
      <div className="flex flex-wrap gap-2">
        <input className="input min-w-[14rem] flex-1" aria-label="Requirement to classify" placeholder="The website should be very fast." value={text} onChange={(e) => setText(e.target.value)} />
        <button className="btn btn-primary" disabled={!text.trim()}>Classify</button>
      </div>
      {result && (
        <p className="mt-2 text-sm text-slate-700">
          <span className="font-semibold">{TYPE_LABELS[result.type]}</span>
          {result.category && `, ${capitalize(result.category)}`}. Confidence: {Math.round(result.confidence * 100)}%.
        </p>
      )}
    </form>
  );
}

export default function ModelPage() {
  const { data: metrics, error, loading } = useLoad(api.metrics);
  return (
    <>
      <PageHeader title="Classifier results" subtitle="TF-IDF and Logistic Regression, measured on data held out from training." />
      {loading ? <Spinner /> : error ? (
        <EmptyState icon={BarChart3} title="No results available" text={error} />
      ) : (
        <div className="space-y-4">
          <Notice>Trained on {metrics.train_rows} rows from {metrics.dataset}. The cross-project score is the most realistic guide for a new client. The app-style test is small and hand-written in the same style as part of the training data, so treat it as a sanity check only.</Notice>
          <TryIt />
          <Metrics title="Functional or non-functional: PROMISE test set" note="20% of PROMISE_exp, held out from training." scores={metrics.type_model} />
          <Metrics title="Functional or non-functional: unseen projects" note="5-fold cross-validation, testing on projects not used for training." scores={metrics.type_model_cross_project} />
          <Metrics title="Functional or non-functional: app-style sanity check" note="Short hand-written sentences from other domains." scores={metrics.type_model_app_style} />
          <Metrics title="Non-functional category: PROMISE test set" note="Six categories grouped from the dataset's labels." scores={metrics.category_model} />
        </div>
      )}
    </>
  );
}

import { useOutletContext } from "react-router-dom";
import { FileDown, FileText } from "lucide-react";
import { Notice, PageHeader } from "../components/ui";

export default function ExportPage() {
  const { project } = useOutletContext();
  const { stats } = project;
  const pendingRequirements = stats.all_requirements - stats.reviewed;
  const formats = [
    { key: "pdf", label: "PDF report", text: "A fixed layout for reading and sharing.", icon: FileText },
    { key: "docx", label: "Word report", text: "An editable DOCX file.", icon: FileDown },
  ];
  return (
    <>
      <PageHeader title="Export report" subtitle="Includes the source summary, requirements, duplicates, warnings, clarification questions, user stories and acceptance criteria." />
      {pendingRequirements > 0 && (
        <Notice>{pendingRequirements} requirement{pendingRequirements > 1 ? "s are" : " is"} still unreviewed. You can export now, and these will be labelled as unreviewed AI suggestions in the report.</Notice>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        {formats.map(({ key, label, text, icon: Icon }) => (
          <div key={key} className="card flex items-center justify-between gap-3 p-5">
            <div className="flex items-start gap-3">
              <Icon className="mt-0.5 h-5 w-5 text-slate-500" />
              <div>
                <h3 className="font-semibold text-slate-800">{label}</h3>
                <p className="text-sm text-slate-500">{text}</p>
              </div>
            </div>
            <a className="btn btn-primary shrink-0" href={`/api/projects/${project.id}/export/${key}`} download>Download</a>
          </div>
        ))}
      </div>
    </>
  );
}

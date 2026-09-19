import { AppShell } from "@/components/app-shell";
import { AssessmentReportWorkspace } from "@/features/assessment-v2/components/assessment-report-workspace";

export default async function AssessmentReportPage({
  params,
}: {
  params: any;
}) {
  const { assessmentId } = await Promise.resolve(params as { assessmentId: string });

  return (
    <AppShell active="Session">
      <div className="p-6">
        <AssessmentReportWorkspace assessmentId={assessmentId} />
      </div>
    </AppShell>
  );
}

import { AppShell } from "@/components/app-shell";
import { AssessmentEvidenceWorkspace } from "@/features/assessment-v2/components/assessment-evidence-workspace";

export default async function AssessmentEvidencePage({ params }: { params: any }) {
  const { assessmentId } = await Promise.resolve(params as { assessmentId: string });

  return (
    <AppShell active="Session">
      <AssessmentEvidenceWorkspace assessmentId={assessmentId} />
    </AppShell>
  );
}

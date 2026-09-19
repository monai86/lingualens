import { AppShell } from "@/components/app-shell";
import { AssessmentClinicalReviewWorkspace } from "@/features/assessment-v2/components/assessment-clinical-review-workspace";

export default async function AssessmentClinicalReviewPage({
  params,
}: {
  params: any;
}) {
  const { assessmentId } = await Promise.resolve(params as { assessmentId: string });

  return (
    <AppShell active="Session">
      <div className="p-6">
        <AssessmentClinicalReviewWorkspace assessmentId={assessmentId} />
      </div>
    </AppShell>
  );
}

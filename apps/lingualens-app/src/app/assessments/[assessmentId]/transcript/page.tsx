import { AppShell } from "@/components/app-shell";
import { AssessmentSegmentReviewWorkspace } from "@/features/assessment-v2/components/assessment-segment-review-workspace";

export default async function AssessmentTranscriptPage({ params }: { params: any }) {
  const { assessmentId } = await Promise.resolve(params as { assessmentId: string });

  return (
    <AppShell active="Session">
      <AssessmentSegmentReviewWorkspace assessmentId={assessmentId} />
    </AppShell>
  );
}

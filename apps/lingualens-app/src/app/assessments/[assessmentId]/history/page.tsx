import { AppShell } from "@/components/app-shell";
import { AssessmentLongitudinalWorkspace } from "@/features/assessment-v2/components/assessment-longitudinal-workspace";

export default async function AssessmentHistoryPage({
  params,
  searchParams,
}: {
  params: any;
  searchParams?: any;
}) {
  const { assessmentId } = await Promise.resolve(params as { assessmentId: string });
  const resolvedSearchParams = searchParams ? await Promise.resolve(searchParams) : {};
  const childId = resolvedSearchParams?.childId as string | undefined;

  return (
    <AppShell active="Session">
      <div className="p-6">
        <AssessmentLongitudinalWorkspace
          assessmentId={assessmentId}
          childId={childId}
        />
      </div>
    </AppShell>
  );
}

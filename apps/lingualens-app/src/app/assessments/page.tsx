import { AppShell } from "@/components/app-shell";
import { AssessmentCaptureWorkspace } from "@/features/assessment-v2/components/assessment-capture-workspace";

export default function AssessmentsPage() {
  return (
    <AppShell active="Session">
      <AssessmentCaptureWorkspace />
    </AppShell>
  );
}

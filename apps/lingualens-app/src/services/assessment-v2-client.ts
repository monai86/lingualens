import { apiV2Request } from "@/lib/api";

export type AssessmentV2Purpose =
  | "initial"
  | "developmental_follow_up"
  | "post_intervention_follow_up"
  | "additional_evidence";

export type AssessmentV2ConsentPurpose = "clinical_assessment" | "research_reuse";
export type AssessmentV2ConsentStatus = "active" | "withdrawn";
export type AssessmentV2State =
  | "draft"
  | "ready_for_capture"
  | "capturing"
  | "processing"
  | "review_required"
  | "ready_for_clinician"
  | "finalized"
  | "cancelled";
export type AssessmentV2RecordingUploadState =
  | "pending"
  | "uploading"
  | "uploaded"
  | "verified"
  | "expired"
  | "failed";
export type AssessmentV2ProcessingState = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type AssessmentV2QualityStatus = "usable" | "needs_additional_sample" | "unavailable" | "failed";

export type AssessmentV2Child = {
  id: string;
  display_code: string;
  birth_year: number;
  birth_month: number;
  language_context: { primary: string; additional: string[] };
  version: number;
};

export type AssessmentV2Consent = {
  id: string;
  child_id: string;
  purpose: AssessmentV2ConsentPurpose;
  scope_version: string;
  status: AssessmentV2ConsentStatus;
  granted_at: string;
  withdrawn_at: string | null;
  version: number;
};

export type AssessmentV2Assessment = {
  id: string;
  child_id: string;
  purpose: AssessmentV2Purpose;
  state: AssessmentV2State;
  age_months: number;
  language_context: { primary: string; additional: string[] };
  assigned_clinician_id: string;
  version: number;
};

export type AssessmentV2ProtocolActivity = {
  activity_code: string;
  required: boolean;
  target_duration_seconds: number;
  minimum_duration_seconds: number;
};

export type AssessmentV2ProtocolSelection = {
  protocol_version_key: string;
  selected_at: string;
  version: number;
};

export type AssessmentV2Recording = {
  id: string;
  activity_code: string;
  content_type: string;
  size_bytes: number;
  upload_state: AssessmentV2RecordingUploadState;
  expires_at: string;
  verified_at: string | null;
  version: number;
};

export type AssessmentV2Quality = {
  status: AssessmentV2QualityStatus;
  evaluated_at: string;
  version: number;
};

export type AssessmentV2Capture = {
  assessment_id: string;
  state: AssessmentV2State;
  protocol: AssessmentV2ProtocolSelection | null;
  activities: AssessmentV2ProtocolActivity[];
  recordings: AssessmentV2Recording[];
  progress: {
    required_activities_total: number;
    required_activities_verified: number;
    required_activities_usable: number;
  };
};

export type AssessmentV2ProcessingRun = {
  id: string;
  stage: "upload_verification" | "quality_analysis" | "cleanup";
  state: AssessmentV2ProcessingState;
  attempt_count: number;
  error_code: string | null;
};

export type AssessmentV2UploadIntent = {
  recording: AssessmentV2Recording;
  upload: {
    url: string;
    expires_at: string;
    expires_in_seconds: number;
    chunk_size_bytes: number;
    upload_length_bytes: number;
    content_type: string;
    upsert: boolean;
  };
};

type AssessmentV2Requester = <T>(path: string, init?: RequestInit) => Promise<T>;

function pathSegment(value: string): string {
  return encodeURIComponent(value);
}

export class AssessmentV2Client {
  constructor(private readonly request: AssessmentV2Requester = apiV2Request) {}

  listChildren(): Promise<AssessmentV2Child[]> {
    return this.request("/children");
  }

  getChild(childId: string): Promise<AssessmentV2Child> {
    return this.request(`/children/${pathSegment(childId)}`);
  }

  listConsents(childId: string): Promise<AssessmentV2Consent[]> {
    return this.request(`/children/${pathSegment(childId)}/consents`);
  }

  createConsent(
    childId: string,
    payload: {
      purpose: AssessmentV2ConsentPurpose;
      scope_version: string;
      status: AssessmentV2ConsentStatus;
    },
  ): Promise<AssessmentV2Consent> {
    return this.request(`/children/${pathSegment(childId)}/consents`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  listAssessments(childId: string): Promise<AssessmentV2Assessment[]> {
    return this.request(`/children/${pathSegment(childId)}/assessments`);
  }

  createAssessment(
    childId: string,
    payload: { purpose: AssessmentV2Purpose; assigned_clinician_id?: string },
  ): Promise<AssessmentV2Assessment> {
    return this.request(`/children/${pathSegment(childId)}/assessments`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  selectProtocol(assessmentId: string): Promise<AssessmentV2Capture> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/protocol-selection`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  }

  getCapture(assessmentId: string): Promise<AssessmentV2Capture> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/capture`);
  }

  startCapture(assessmentId: string): Promise<{ assessment_id: string; state: AssessmentV2State; version: number }> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/capture/start`, { method: "POST" });
  }

  createRecording(
    assessmentId: string,
    activityCode: string,
    payload: { content_type: string; size_bytes: number; checksum: string },
    idempotencyKey: string,
  ): Promise<{ recording: AssessmentV2Recording; processing_run: AssessmentV2ProcessingRun }> {
    return this.request(
      `/assessments/${pathSegment(assessmentId)}/activities/${pathSegment(activityCode)}/recordings`,
      {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify(payload),
      },
    );
  }

  createUploadIntent(recordingId: string): Promise<AssessmentV2UploadIntent> {
    return this.request(`/recordings/${pathSegment(recordingId)}/upload-intent`, { method: "POST" });
  }

  completeUpload(recordingId: string): Promise<{ recording: AssessmentV2Recording; processing_run: AssessmentV2ProcessingRun }> {
    return this.request(`/recordings/${pathSegment(recordingId)}/complete-upload`, { method: "POST" });
  }

  getProcessingRun(runId: string): Promise<AssessmentV2ProcessingRun> {
    return this.request(`/processing-runs/${pathSegment(runId)}`);
  }

  getRecordingQuality(recordingId: string): Promise<AssessmentV2Quality | null> {
    return this.request(`/recordings/${pathSegment(recordingId)}/quality`);
  }

  completeCapture(assessmentId: string): Promise<AssessmentV2Assessment> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/capture/complete`, { method: "POST" });
  }
}

export function createAssessmentV2Client(request?: AssessmentV2Requester): AssessmentV2Client {
  return new AssessmentV2Client(request);
}

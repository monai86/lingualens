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
export type AssessmentV2EvidenceState =
  | "pending"
  | "processing"
  | "completed"
  | "needs_review"
  | "insufficient_data"
  | "unavailable"
  | "failed"
  | "stale";
export type AssessmentV2EvidenceSource = "reviewed_transcript" | "audio_quality" | "observation" | "instrument";
export type AssessmentV2TranscriptSource = "manual" | "asr_draft" | "imported";
export type AssessmentV2TranscriptReviewState = "draft" | "attested" | "superseded";
export type AssessmentV2DevelopmentalDomain =
  | "expressive_language"
  | "speech_clarity_production"
  | "conversational_interaction"
  | "social_communication"
  | "repetitive_language"
  | "prosody_temporal_organization"
  | "evidence_quality_sufficiency";
export type AssessmentV2DomainProfileStatus =
  | "descriptive_only"
  | "within_reference_band"
  | "outside_reference_band"
  | "attention_suggested"
  | "insufficient_data"
  | "reference_unavailable"
  | "not_assessed";

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

export type AssessmentV2EvidenceProvenance = {
  input_ref: string;
  input_sha256: string;
  protocol_version_key: string;
  extractor: string;
  pipeline_version: string;
  feature_schema_version: string;
  analyzed_at: string;
};

export type AssessmentV2MeasuredFeature = {
  key: string;
  value: boolean | number | string | null;
  unit: string;
  source: AssessmentV2EvidenceSource;
  state: AssessmentV2EvidenceState;
  limitation: string | null;
  provenance: AssessmentV2EvidenceProvenance;
};

export type AssessmentV2DomainProfile = {
  domain: AssessmentV2DevelopmentalDomain;
  status: AssessmentV2DomainProfileStatus;
  summary: string;
  feature_keys: string[];
  supporting_features: string[];
  conflicting_features: string[];
  limitations: string[];
};

export type AssessmentV2EvidenceProfile = {
  evidence_run_id: string;
  assessment_id: string;
  transcript_revision_id: string;
  state: AssessmentV2EvidenceState;
  generated_at: string;
  provenance: AssessmentV2EvidenceProvenance;
  features: AssessmentV2MeasuredFeature[];
  domains: AssessmentV2DomainProfile[];
  limitations: string[];
  not_diagnostic: true;
  decision_support_only: true;
  version: number;
};

export type AssessmentV2TranscriptRevision = {
  id: string;
  assessment_id: string;
  revision: number;
  source: AssessmentV2TranscriptSource;
  review_state: AssessmentV2TranscriptReviewState;
  content: string;
  content_sha256: string;
  created_at: string;
  attested_at: string | null;
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
  stage: "upload_verification" | "quality_analysis" | "cleanup" | "evidence_extraction";
  state: AssessmentV2ProcessingState;
  attempt_count: number;
  max_attempts: number;
  available_at: string;
  error_code: string | null;
  result_available: boolean;
  can_retry: boolean;
  can_cancel: boolean;
  version: number;
};

export type AssessmentV2EvidenceProcessing = {
  processing_run: AssessmentV2ProcessingRun;
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

  getEvidence(assessmentId: string): Promise<AssessmentV2EvidenceProfile> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/evidence`);
  }

  getTranscript(assessmentId: string): Promise<AssessmentV2TranscriptRevision> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/transcript`);
  }

  createTranscriptRevision(
    assessmentId: string,
    payload: {
      source: AssessmentV2TranscriptSource;
      content: string;
      expected_revision: number | null;
      expected_version: number | null;
    },
  ): Promise<AssessmentV2TranscriptRevision> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/transcript-revisions`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  attestTranscript(transcriptRevisionId: string, expectedVersion: number): Promise<AssessmentV2TranscriptRevision> {
    return this.request(`/transcript-revisions/${pathSegment(transcriptRevisionId)}/attest`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion }),
    });
  }

  queueEvidence(assessmentId: string): Promise<AssessmentV2EvidenceProcessing> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/evidence-runs`, { method: "POST" });
  }

  getCurrentEvidenceProcessingRun(assessmentId: string): Promise<AssessmentV2EvidenceProcessing> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/evidence-processing-run`);
  }

  retryProcessingRun(runId: string, expectedVersion: number): Promise<AssessmentV2ProcessingRun> {
    return this.request(`/processing-runs/${pathSegment(runId)}/retry`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion }),
    });
  }

  cancelProcessingRun(runId: string, expectedVersion: number): Promise<AssessmentV2ProcessingRun> {
    return this.request(`/processing-runs/${pathSegment(runId)}/cancel`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion }),
    });
  }

  completeCapture(assessmentId: string): Promise<AssessmentV2Assessment> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/capture/complete`, { method: "POST" });
  }
}

export function createAssessmentV2Client(request?: AssessmentV2Requester): AssessmentV2Client {
  return new AssessmentV2Client(request);
}

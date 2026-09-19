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
export type AssessmentV2TranscriptSegmentSpeakerRole = "child" | "therapist" | "caregiver" | "unknown";
export type AssessmentV2TranscriptSegmentUncertaintyReason =
  | "none"
  | "low_asr_confidence"
  | "unintelligible_audio"
  | "speaker_uncertain"
  | "timestamp_uncertain"
  | "manual_review";
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
  segment_set_id: string | null;
  segment_set_sha256: string | null;
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

export type AssessmentV2TranscriptSegment = {
  id: string;
  ordinal: number;
  start_ms: number;
  end_ms: number;
  speaker_role: AssessmentV2TranscriptSegmentSpeakerRole;
  text: string;
  confidence: number | null;
  uncertainty_reason: AssessmentV2TranscriptSegmentUncertaintyReason;
  created_at: string;
};

export type AssessmentV2TranscriptSegmentSet = {
  id: string;
  assessment_id: string;
  transcript_revision_id: string;
  transcript_content_sha256: string;
  recording_id: string | null;
  revision: number;
  source: AssessmentV2TranscriptSource;
  review_state: AssessmentV2TranscriptReviewState;
  segments_sha256: string;
  segments: AssessmentV2TranscriptSegment[];
  created_at: string;
  attested_at: string | null;
  version: number;
};

export type AssessmentV2TranscriptSegmentReplayGrant = {
  segment_id: string;
  start_ms: number;
  end_ms: number;
  available: boolean;
  url: string | null;
  expires_at: string | null;
  expires_in_seconds: number | null;
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

  getCurrentTranscriptSegmentSet(assessmentId: string): Promise<AssessmentV2TranscriptSegmentSet> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/transcript-segment-set`);
  }

  createTranscriptSegmentSet(
    assessmentId: string,
    payload: {
      transcript_revision_id: string;
      source: AssessmentV2TranscriptSource;
      segments: Array<{
        ordinal: number;
        start_ms: number;
        end_ms: number;
        speaker_role: AssessmentV2TranscriptSegmentSpeakerRole;
        text: string;
        confidence: number | null;
        uncertainty_reason: AssessmentV2TranscriptSegmentUncertaintyReason;
      }>;
      recording_id?: string | null;
      expected_revision?: number | null;
      expected_version?: number | null;
    },
  ): Promise<AssessmentV2TranscriptSegmentSet> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/transcript-segment-sets`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  attestTranscriptSegmentSet(
    transcriptSegmentSetId: string,
    expectedVersion: number,
  ): Promise<AssessmentV2TranscriptSegmentSet> {
    return this.request(`/transcript-segment-sets/${pathSegment(transcriptSegmentSetId)}/attest`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion }),
    });
  }

  createSegmentReplayGrant(
    segmentId: string,
  ): Promise<AssessmentV2TranscriptSegmentReplayGrant> {
    return this.request(`/transcript-segments/${pathSegment(segmentId)}/audio-replay-grant`, {
      method: "POST",
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

  createComparison(
    assessmentId: string,
    baselineAssessmentId: string,
    policyVersion: string = "longitudinal_v1",
  ): Promise<AssessmentV2Comparison> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/comparisons`, {
      method: "POST",
      body: JSON.stringify({
        baseline_assessment_id: baselineAssessmentId,
        policy_version: policyVersion,
      }),
    });
  }

  getComparisons(assessmentId: string): Promise<AssessmentV2Comparison[]> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/comparisons`);
  }

  getComparison(assessmentId: string, comparisonId: string): Promise<AssessmentV2Comparison> {
    return this.request(
      `/assessments/${pathSegment(assessmentId)}/comparisons/${pathSegment(comparisonId)}`
    );
  }

  getChildAssessmentHistory(childId: string): Promise<AssessmentV2ChildHistoryItem[]> {
    return this.request(`/children/${pathSegment(childId)}/assessments/history`);
  }

  getClinicalReview(assessmentId: string): Promise<AssessmentV2ClinicalReview> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/clinical-review`);
  }

  reviewAttentionCue(
    assessmentId: string,
    cueId: string,
    payload: {
      action: AssessmentV2CueStatus;
      rationale?: string;
      expected_version: number;
    },
  ): Promise<AssessmentV2ClinicalReview> {
    return this.request(
      `/assessments/${pathSegment(assessmentId)}/clinical-review/cues/${pathSegment(cueId)}`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  updateClinicalDisposition(
    assessmentId: string,
    payload: {
      disposition_type: AssessmentV2ClinicalDispositionType;
      disposition_notes?: string;
      clinical_summary?: string;
      follow_up_plan?: AssessmentV2FollowUpPlan;
      expected_version: number;
    },
  ): Promise<AssessmentV2ClinicalReview> {
    return this.request(
      `/assessments/${pathSegment(assessmentId)}/clinical-review/disposition`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  createReportDraft(assessmentId: string): Promise<AssessmentV2Report> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/reports/draft`, {
      method: "POST",
    });
  }

  getCurrentReport(assessmentId: string): Promise<AssessmentV2Report> {
    return this.request(`/assessments/${pathSegment(assessmentId)}/reports/current`);
  }

  getReport(assessmentId: string, reportId: string): Promise<AssessmentV2Report> {
    return this.request(
      `/assessments/${pathSegment(assessmentId)}/reports/${pathSegment(reportId)}`,
    );
  }

  updateReportDraft(
    assessmentId: string,
    reportId: string,
    payload: {
      markdown_content?: string;
      report_title?: string;
      clinical_summary?: string;
      expected_version: number;
    },
  ): Promise<AssessmentV2Report> {
    return this.request(
      `/assessments/${pathSegment(assessmentId)}/reports/${pathSegment(reportId)}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      },
    );
  }

  signOffReport(
    assessmentId: string,
    reportId: string,
    payload: {
      expected_version: number;
    },
  ): Promise<AssessmentV2Report> {
    return this.request(
      `/assessments/${pathSegment(assessmentId)}/reports/${pathSegment(reportId)}/sign`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  createReportAmendment(
    assessmentId: string,
    reportId: string,
    payload: {
      amendment_reason: string;
      expected_version: number;
    },
  ): Promise<AssessmentV2Report> {
    return this.request(
      `/assessments/${pathSegment(assessmentId)}/reports/${pathSegment(reportId)}/amend`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  }

  getReportLineage(assessmentId: string, reportId: string): Promise<AssessmentV2ReportLineageItem[]> {
    return this.request(
      `/assessments/${pathSegment(assessmentId)}/reports/${pathSegment(reportId)}/lineage`,
    );
  }

  getReportExportPdfUrl(assessmentId: string, reportId: string): string {
    return `/api/v2/assessments/${pathSegment(assessmentId)}/reports/${pathSegment(reportId)}/export?format=pdf`;
  }
}

export type AssessmentV2CompatibilityStatus = "compatible" | "not_comparable";
export type AssessmentV2NumericalTrend = "increased" | "decreased" | "unchanged" | "indeterminate";
export type AssessmentV2IncompatibilityReason =
  | "different_child"
  | "tenant_mismatch"
  | "protocol_incompatible"
  | "language_mismatch"
  | "unit_mismatch"
  | "extractor_mismatch"
  | "baseline_feature_not_completed"
  | "current_feature_not_completed"
  | "missing_feature"
  | "non_numeric_value"
  | "quality_insufficient";

export interface AssessmentV2FeatureComparison {
  feature_key: string;
  unit: string | null;
  status: AssessmentV2CompatibilityStatus;
  incompatibility_reasons: AssessmentV2IncompatibilityReason[];
  baseline_value: number | null;
  current_value: number | null;
  absolute_delta: number | null;
  percent_change: number | null;
  percent_change_limitation: string | null;
  numerical_trend: AssessmentV2NumericalTrend;
  clinical_interpretation: string;
}

export interface AssessmentV2Comparison {
  comparison_id: string;
  baseline_assessment_id: string;
  current_assessment_id: string;
  baseline_evidence_run_id: string;
  current_evidence_run_id: string;
  baseline_evidence_sha256: string;
  current_evidence_sha256: string;
  policy_version: string;
  status: AssessmentV2CompatibilityStatus;
  is_stale: boolean;
  features: AssessmentV2FeatureComparison[];
  created_at: string;
}

export interface AssessmentV2ChildHistoryItem {
  assessment_id: string;
  created_at: string;
  purpose: string;
  state: string;
  age_months: number;
  protocol_version_key: string | null;
  language: string;
  evidence_run_id: string | null;
  is_comparable: boolean;
}

export type AssessmentV2AttentionCueType =
  | "lexical_diversity_low"
  | "turn_taking_low"
  | "intelligibility_concern"
  | "speech_rate_atypical"
  | "repetition_high"
  | "social_affect_low"
  | "acoustic_signal_unstable";

export type AssessmentV2CueStatus =
  | "unreviewed"
  | "acknowledged"
  | "disagreed"
  | "more_evidence_requested";

export interface AssessmentV2AttentionCue {
  cue_id: string;
  cue_type: AssessmentV2AttentionCueType;
  title: string;
  description: string;
  severity_level: "info" | "moderate" | "significant";
  policy_version: string;
  evidence_run_id: string;
  feature_key: string | null;
  status: AssessmentV2CueStatus;
  clinician_action: AssessmentV2CueStatus;
  clinician_rationale: string | null;
  reviewed_at: string | null;
  reviewed_by: string | null;
}

export type AssessmentV2ClinicalDispositionType =
  | "within_normal_expectations"
  | "monitoring_recommended"
  | "targeted_intervention_recommended"
  | "comprehensive_multidisciplinary_evaluation_recommended"
  | "inconclusive_further_evidence_needed";

export interface AssessmentV2FollowUpPlan {
  target_window_weeks: number;
  recommended_activities: string[];
  caregiver_guidance: string;
}

export interface AssessmentV2ClinicalReview {
  review_id: string;
  assessment_id: string;
  organization_id: string;
  clinician_id: string;
  cues_evaluated: boolean;
  cues_policy_version: string;
  attention_cues: AssessmentV2AttentionCue[];
  disposition_type: AssessmentV2ClinicalDispositionType | null;
  disposition_notes: string;
  clinical_summary: string;
  follow_up_plan: AssessmentV2FollowUpPlan | null;
  unreviewed_cues_count: number;
  can_finalize: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export type AssessmentV2ReportStatus = "draft" | "signed_off" | "amended" | "archived";

export interface AssessmentV2ReportReadiness {
  is_ready: boolean;
  blockers: string[];
}

export interface AssessmentV2Report {
  report_id: string;
  assessment_id: string;
  organization_id: string;
  status: AssessmentV2ReportStatus;
  signer_id: string | null;
  signer_name: string | null;
  signer_role: string | null;
  amends_report_id: string | null;
  amendment_sequence: number;
  report_title: string;
  markdown_content: string;
  clinical_summary: string;
  disposition_type: string | null;
  disposition_notes: string;
  follow_up_plan: Record<string, any> | null;
  snapshot_data: Record<string, any> | null;
  snapshot_sha256: string | null;
  signed_at: string | null;
  amendment_reason: string | null;
  readiness: AssessmentV2ReportReadiness;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AssessmentV2ReportLineageItem {
  report_id: string;
  amendment_sequence: number;
  status: AssessmentV2ReportStatus;
  signed_at: string | null;
  signer_id: string | null;
  snapshot_sha256: string | null;
  amendment_reason: string | null;
  created_at: string;
}

export function createAssessmentV2Client(request?: AssessmentV2Requester): AssessmentV2Client {
  return new AssessmentV2Client(request);
}


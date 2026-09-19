-- ==============================================================================
-- LinguaLens Assessment V2: Clean-Slate Supabase Migration & Initialization
-- 
-- Summary:
--   Completely wipes existing public schema in Supabase and initializes:
--   1. Schema reset & permissions (anon, authenticated, service_role)
--   2. Extensions (uuid-ossp, pgcrypto)
--   3. Multi-Tenant Helper Functions (current_org_id, is_org_member)
--   4. All 28 Assessment V2 Tables with PKs, FKs, Unique and Check Constraints
--   5. All 100 Performance & Query Indexes
--   6. Multi-Tenant Row Level Security (RLS) enabled & forced
--   7. Supabase Auth Automatic Sync Trigger (auth.users -> user_profiles)
--   8. Private Audio Storage Bucket (audio-recordings) and storage RLS policies
--   9. Clinical Catalog Seed Data (organizations, protocol catalog, activities)
--  10. Alembic Version Stamp (0012_clinical_review_reports)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- PART 1: SCHEMA TEAR DOWN & EXTENSIONS
-- ------------------------------------------------------------------------------
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON ROUTINES TO postgres, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres, anon, authenticated, service_role;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

-- ------------------------------------------------------------------------------
-- PART 2: HELPER FUNCTIONS FOR TENANT RLS & AUTH RESOLUTION
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.current_org_id()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT coalesce(
    nullif(current_setting('app.current_organization_id', true), ''),
    (
      SELECT organization_id
      FROM public.organization_memberships
      WHERE user_id = auth.uid()::text
        AND active = true
      LIMIT 1
    )
  );
$$;

CREATE OR REPLACE FUNCTION public.is_org_member(target_org_id text)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT (
    -- 1. Session setting override (used by FastAPI backend connection pool)
    current_setting('app.current_organization_id', true) = target_org_id
    -- 2. Service role bypass (Supabase service_role API key)
    OR auth.role() = 'service_role'
    -- 3. Supabase Auth user membership lookup
    OR (
      auth.uid() IS NOT NULL
      AND EXISTS (
        SELECT 1
        FROM public.organization_memberships
        WHERE organization_id = target_org_id
          AND user_id = auth.uid()::text
          AND active = true
      )
    )
  );
$$;

-- ------------------------------------------------------------------------------
-- PART 3: TABLE DEFINITIONS & CONSTRAINTS
-- ------------------------------------------------------------------------------

-- Table: organizations
CREATE TABLE organizations (
	organization_id VARCHAR(64) NOT NULL, 
	display_label VARCHAR(256) NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (organization_id)
);

-- Table: protocol_versions
CREATE TABLE protocol_versions (
	protocol_version_key VARCHAR(128) NOT NULL, 
	primary_language VARCHAR(16) NOT NULL, 
	minimum_age_months INTEGER NOT NULL, 
	maximum_age_months INTEGER NOT NULL, 
	supported_purposes VARCHAR(256) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (protocol_version_key), 
	CONSTRAINT ck_protocol_versions_primary_language CHECK (length(primary_language) > 0), 
	CONSTRAINT ck_protocol_versions_minimum_age CHECK (minimum_age_months >= 0), 
	CONSTRAINT ck_protocol_versions_age_range CHECK (maximum_age_months >= minimum_age_months), 
	CONSTRAINT ck_protocol_versions_supported_purposes CHECK (length(supported_purposes) > 0)
);

-- Table: user_profiles
CREATE TABLE user_profiles (
	user_id VARCHAR(128) NOT NULL, 
	display_label VARCHAR(256) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (user_id)
);

-- Table: audit_events
CREATE TABLE audit_events (
	audit_event_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	actor_user_id VARCHAR(128) NOT NULL, 
	action VARCHAR(128) NOT NULL, 
	target_type VARCHAR(64) NOT NULL, 
	target_id VARCHAR(128) NOT NULL, 
	outcome VARCHAR(32) NOT NULL, 
	correlation_id VARCHAR(128) NOT NULL, 
	target_version INTEGER, 
	metadata_json JSON DEFAULT '{}' NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (audit_event_id), 
	CONSTRAINT fk_audit_events_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id)
);

-- Table: children
CREATE TABLE children (
	child_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	display_code VARCHAR(128) NOT NULL, 
	birth_month INTEGER NOT NULL, 
	birth_year INTEGER NOT NULL, 
	language_context VARCHAR(128) NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (child_id), 
	CONSTRAINT uq_children_organization_child UNIQUE (organization_id, child_id), 
	CONSTRAINT uq_child_organization_display_code UNIQUE (organization_id, display_code), 
	CONSTRAINT ck_children_birth_month CHECK (birth_month BETWEEN 1 AND 12), 
	CONSTRAINT ck_children_birth_year CHECK (birth_year BETWEEN 1900 AND 2100), 
	CONSTRAINT ck_children_version CHECK (version >= 1), 
	CONSTRAINT fk_children_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id)
);

-- Table: organization_memberships
CREATE TABLE organization_memberships (
	membership_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(128) NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (membership_id), 
	CONSTRAINT uq_membership_organization_user UNIQUE (organization_id, user_id), 
	CONSTRAINT ck_membership_role CHECK (role IN ('therapist', 'clinical_supervisor', 'org_admin', 'researcher')), 
	CONSTRAINT fk_membership_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_membership_user FOREIGN KEY(user_id) REFERENCES user_profiles (user_id)
);

-- Table: protocol_activities
CREATE TABLE protocol_activities (
	protocol_version_key VARCHAR(128) NOT NULL, 
	activity_key VARCHAR(64) NOT NULL, 
	required BOOLEAN NOT NULL, 
	target_duration_seconds INTEGER NOT NULL, 
	minimum_duration_seconds INTEGER NOT NULL, 
	sort_order INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (protocol_version_key, activity_key), 
	CONSTRAINT ck_protocol_activities_target_duration CHECK (target_duration_seconds > 0), 
	CONSTRAINT ck_protocol_activities_minimum_duration CHECK (minimum_duration_seconds > 0), 
	CONSTRAINT ck_protocol_activities_duration_range CHECK (target_duration_seconds >= minimum_duration_seconds), 
	CONSTRAINT ck_protocol_activities_sort_order CHECK (sort_order >= 1), 
	CONSTRAINT fk_protocol_activities_protocol_version FOREIGN KEY(protocol_version_key) REFERENCES protocol_versions (protocol_version_key)
);

-- Table: assessments
CREATE TABLE assessments (
	assessment_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	child_id VARCHAR(64) NOT NULL, 
	purpose VARCHAR(32) NOT NULL, 
	state VARCHAR(32) NOT NULL, 
	age_months INTEGER NOT NULL, 
	language_context VARCHAR(128) NOT NULL, 
	assigned_clinician_id VARCHAR(128) NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (assessment_id), 
	CONSTRAINT uq_assessments_organization_assessment UNIQUE (organization_id, assessment_id), 
	CONSTRAINT fk_assessments_child_tenant FOREIGN KEY(organization_id, child_id) REFERENCES children (organization_id, child_id), 
	CONSTRAINT fk_assessments_clinician_membership_tenant FOREIGN KEY(organization_id, assigned_clinician_id) REFERENCES organization_memberships (organization_id, user_id), 
	CONSTRAINT ck_assessments_purpose CHECK (purpose IN ('initial', 'developmental_follow_up', 'post_intervention_follow_up', 'additional_evidence')), 
	CONSTRAINT ck_assessments_state CHECK (state IN ('draft', 'ready_for_capture', 'capturing', 'processing', 'review_required', 'ready_for_clinician', 'finalized', 'cancelled')), 
	CONSTRAINT ck_assessments_age_months CHECK (age_months BETWEEN 0 AND 216), 
	CONSTRAINT ck_assessments_version CHECK (version >= 1), 
	CONSTRAINT fk_assessments_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_assessments_child FOREIGN KEY(child_id) REFERENCES children (child_id), 
	CONSTRAINT fk_assessments_clinician FOREIGN KEY(assigned_clinician_id) REFERENCES user_profiles (user_id)
);

-- Table: care_team_assignments
CREATE TABLE care_team_assignments (
	assignment_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	child_id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(128) NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (assignment_id), 
	CONSTRAINT uq_care_team_organization_child_user UNIQUE (organization_id, child_id, user_id), 
	CONSTRAINT fk_care_team_child_tenant FOREIGN KEY(organization_id, child_id) REFERENCES children (organization_id, child_id), 
	CONSTRAINT fk_care_team_membership_tenant FOREIGN KEY(organization_id, user_id) REFERENCES organization_memberships (organization_id, user_id), 
	CONSTRAINT ck_care_team_role CHECK (role IN ('assigned_clinician', 'supervisor', 'observer')), 
	CONSTRAINT fk_care_team_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_care_team_child FOREIGN KEY(child_id) REFERENCES children (child_id), 
	CONSTRAINT fk_care_team_user FOREIGN KEY(user_id) REFERENCES user_profiles (user_id)
);

-- Table: consent_records
CREATE TABLE consent_records (
	consent_record_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	child_id VARCHAR(64) NOT NULL, 
	purpose VARCHAR(32) NOT NULL, 
	scope_version VARCHAR(64) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	granted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	withdrawn_at TIMESTAMP WITH TIME ZONE, 
	recorded_by_user_id VARCHAR(128) NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (consent_record_id), 
	CONSTRAINT uq_consent_organization_child_purpose_version UNIQUE (organization_id, child_id, purpose, version), 
	CONSTRAINT fk_consent_child_tenant FOREIGN KEY(organization_id, child_id) REFERENCES children (organization_id, child_id), 
	CONSTRAINT ck_consent_records_purpose CHECK (purpose IN ('clinical_assessment', 'research_reuse')), 
	CONSTRAINT ck_consent_records_status CHECK (status IN ('active', 'withdrawn')), 
	CONSTRAINT ck_consent_records_version CHECK (version >= 1), 
	CONSTRAINT fk_consent_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_consent_child FOREIGN KEY(child_id) REFERENCES children (child_id)
);

-- Table: assessment_instruments
CREATE TABLE assessment_instruments (
	administration_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	instrument_name VARCHAR(128) NOT NULL, 
	instrument_version VARCHAR(64) NOT NULL, 
	respondent_type VARCHAR(32) NOT NULL, 
	administered_by_user_id VARCHAR(128) NOT NULL, 
	administered_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	licensing_verified BOOLEAN NOT NULL, 
	summary_scores_json JSON DEFAULT '{}' NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (administration_id), 
	CONSTRAINT uq_instruments_organization_administration UNIQUE (organization_id, administration_id), 
	CONSTRAINT fk_instruments_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT ck_instruments_respondent_type CHECK (respondent_type IN ('caregiver', 'clinician', 'teacher')), 
	CONSTRAINT ck_instruments_name_non_empty CHECK (length(instrument_name) > 0), 
	CONSTRAINT ck_instruments_version_non_empty CHECK (length(instrument_version) > 0), 
	CONSTRAINT ck_instruments_version CHECK (version >= 1), 
	CONSTRAINT fk_instruments_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_instruments_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id)
);

-- Table: assessment_observations
CREATE TABLE assessment_observations (
	observation_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	category VARCHAR(64) NOT NULL, 
	source VARCHAR(32) NOT NULL, 
	observer_name VARCHAR(256) NOT NULL, 
	observer_role VARCHAR(128) NOT NULL, 
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	activity_context VARCHAR(512) NOT NULL, 
	notes TEXT NOT NULL, 
	structured_flags_json JSON DEFAULT '[]' NOT NULL, 
	is_amendment BOOLEAN NOT NULL, 
	amends_observation_id VARCHAR(64), 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (observation_id), 
	CONSTRAINT uq_observations_organization_observation UNIQUE (organization_id, observation_id), 
	CONSTRAINT fk_observations_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT ck_observations_category CHECK (category IN ('communication', 'social_engagement', 'play_behavior', 'sensory_motor', 'emotional_regulation')), 
	CONSTRAINT ck_observations_source CHECK (source IN ('clinician', 'caregiver', 'educator')), 
	CONSTRAINT ck_observations_notes_non_empty CHECK (length(notes) > 0), 
	CONSTRAINT ck_observations_version CHECK (version >= 1), 
	CONSTRAINT ck_observations_amendment_integrity CHECK ((NOT is_amendment AND amends_observation_id IS NULL AND version = 1) OR (is_amendment AND amends_observation_id IS NOT NULL AND version >= 2)), 
	CONSTRAINT fk_observations_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_observations_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id)
);

-- Table: assessment_protocol_selections
CREATE TABLE assessment_protocol_selections (
	assessment_protocol_selection_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	protocol_version_key VARCHAR(128) NOT NULL, 
	selected_by_user_id VARCHAR(128) NOT NULL, 
	selected_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (assessment_protocol_selection_id), 
	CONSTRAINT uq_assessment_protocol_selections_organization_assessment UNIQUE (organization_id, assessment_id), 
	CONSTRAINT uq_aps_org_assessment_protocol UNIQUE (organization_id, assessment_id, protocol_version_key), 
	CONSTRAINT fk_assessment_protocol_selections_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT fk_assessment_protocol_selections_actor_membership_tenant FOREIGN KEY(organization_id, selected_by_user_id) REFERENCES organization_memberships (organization_id, user_id), 
	CONSTRAINT ck_assessment_protocol_selections_version CHECK (version >= 1), 
	CONSTRAINT fk_assessment_protocol_selections_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_assessment_protocol_selections_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_assessment_protocol_selections_protocol FOREIGN KEY(protocol_version_key) REFERENCES protocol_versions (protocol_version_key), 
	CONSTRAINT fk_assessment_protocol_selections_actor FOREIGN KEY(selected_by_user_id) REFERENCES user_profiles (user_id)
);

-- Table: transcript_revisions
CREATE TABLE transcript_revisions (
	transcript_revision_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	revision INTEGER NOT NULL, 
	source VARCHAR(32) NOT NULL, 
	review_state VARCHAR(32) NOT NULL, 
	content TEXT NOT NULL, 
	content_sha256 VARCHAR(64) NOT NULL, 
	created_by_user_id VARCHAR(128) NOT NULL, 
	attested_by_user_id VARCHAR(128), 
	attested_at TIMESTAMP WITH TIME ZONE, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (transcript_revision_id), 
	CONSTRAINT uq_transcript_revisions_organization_revision_id UNIQUE (organization_id, transcript_revision_id), 
	CONSTRAINT uq_transcript_revisions_organization_assessment_revision UNIQUE (organization_id, assessment_id, revision), 
	CONSTRAINT fk_transcript_revisions_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT ck_transcript_revisions_source CHECK (source IN ('manual', 'asr_draft', 'imported')), 
	CONSTRAINT ck_transcript_revisions_review_state CHECK (review_state IN ('draft', 'attested', 'superseded')), 
	CONSTRAINT ck_transcript_revisions_content CHECK (length(content) > 0), 
	CONSTRAINT ck_transcript_revisions_content_sha256 CHECK (length(content_sha256) = 64), 
	CONSTRAINT ck_transcript_revisions_revision CHECK (revision >= 1), 
	CONSTRAINT ck_transcript_revisions_version CHECK (version >= 1), 
	CONSTRAINT fk_transcript_revisions_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_transcript_revisions_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id)
);

-- Table: assessment_instrument_items
CREATE TABLE assessment_instrument_items (
	item_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	administration_id VARCHAR(64) NOT NULL, 
	item_key VARCHAR(64) NOT NULL, 
	prompt_label VARCHAR(512) NOT NULL, 
	response_value VARCHAR(512) NOT NULL, 
	score FLOAT, 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (item_id), 
	CONSTRAINT uq_instrument_items_organization_item UNIQUE (organization_id, item_id), 
	CONSTRAINT uq_instrument_items_admin_item_key UNIQUE (organization_id, administration_id, item_key), 
	CONSTRAINT fk_instrument_items_administration_tenant FOREIGN KEY(organization_id, administration_id) REFERENCES assessment_instruments (organization_id, administration_id), 
	CONSTRAINT ck_instrument_items_key_non_empty CHECK (length(item_key) > 0), 
	CONSTRAINT ck_instrument_items_label_non_empty CHECK (length(prompt_label) > 0), 
	CONSTRAINT fk_instrument_items_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_instrument_items_administration FOREIGN KEY(administration_id) REFERENCES assessment_instruments (administration_id)
);

-- Table: recordings
CREATE TABLE recordings (
	recording_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	protocol_version_key VARCHAR(128) NOT NULL, 
	activity_key VARCHAR(64) NOT NULL, 
	declared_content_type VARCHAR(128) NOT NULL, 
	declared_size_bytes BIGINT NOT NULL, 
	declared_checksum VARCHAR(128) NOT NULL, 
	object_key VARCHAR(512) NOT NULL, 
	upload_state VARCHAR(32) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	verified_content_type VARCHAR(128), 
	verified_size_bytes BIGINT, 
	verified_checksum VARCHAR(128), 
	verified_at TIMESTAMP WITH TIME ZONE, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (recording_id), 
	CONSTRAINT uq_recordings_organization_recording UNIQUE (organization_id, recording_id), 
	CONSTRAINT uq_recordings_object_key UNIQUE (object_key), 
	CONSTRAINT fk_recordings_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT fk_recordings_assessment_protocol_selection_tenant FOREIGN KEY(organization_id, assessment_id, protocol_version_key) REFERENCES assessment_protocol_selections (organization_id, assessment_id, protocol_version_key), 
	CONSTRAINT fk_recordings_protocol_activity FOREIGN KEY(protocol_version_key, activity_key) REFERENCES protocol_activities (protocol_version_key, activity_key), 
	CONSTRAINT ck_recordings_declared_size CHECK (declared_size_bytes > 0), 
	CONSTRAINT ck_recordings_declared_content_type CHECK (length(declared_content_type) > 0), 
	CONSTRAINT ck_recordings_declared_checksum CHECK (length(declared_checksum) > 0), 
	CONSTRAINT ck_recordings_object_key CHECK (length(object_key) > 0), 
	CONSTRAINT ck_recordings_upload_state CHECK (upload_state IN ('pending', 'uploading', 'uploaded', 'verified', 'expired', 'failed')), 
	CONSTRAINT ck_recordings_verified_size CHECK (verified_size_bytes IS NULL OR verified_size_bytes > 0), 
	CONSTRAINT ck_recordings_verified_metadata_complete CHECK ((verified_content_type IS NULL AND verified_size_bytes IS NULL AND verified_checksum IS NULL AND verified_at IS NULL) OR (verified_content_type IS NOT NULL AND verified_size_bytes IS NOT NULL AND verified_checksum IS NOT NULL AND verified_at IS NOT NULL)), 
	CONSTRAINT ck_recordings_version CHECK (version >= 1), 
	CONSTRAINT fk_recordings_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_recordings_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_recordings_protocol_version FOREIGN KEY(protocol_version_key) REFERENCES protocol_versions (protocol_version_key)
);

-- Table: recording_quality_results
CREATE TABLE recording_quality_results (
	recording_quality_result_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	recording_id VARCHAR(64) NOT NULL, 
	status VARCHAR(32) DEFAULT 'usable' NOT NULL, 
	measured_duration_seconds FLOAT, 
	measured_loudness_db FLOAT, 
	measured_silence_ratio FLOAT, 
	measured_decodability FLOAT, 
	unavailable_checks_json JSON DEFAULT '[]' NOT NULL, 
	provenance VARCHAR(256) NOT NULL, 
	evaluated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (recording_quality_result_id), 
	CONSTRAINT uq_recording_quality_results_organization_recording UNIQUE (organization_id, recording_id), 
	CONSTRAINT fk_recording_quality_results_recording_tenant FOREIGN KEY(organization_id, recording_id) REFERENCES recordings (organization_id, recording_id), 
	CONSTRAINT ck_recording_quality_results_status CHECK (status IN ('usable', 'needs_additional_sample', 'unavailable', 'failed')), 
	CONSTRAINT ck_recording_quality_results_duration CHECK (measured_duration_seconds IS NULL OR measured_duration_seconds >= 0), 
	CONSTRAINT ck_recording_quality_results_silence_ratio CHECK (measured_silence_ratio IS NULL OR measured_silence_ratio BETWEEN 0 AND 1), 
	CONSTRAINT ck_recording_quality_results_decodability CHECK (measured_decodability IS NULL OR measured_decodability BETWEEN 0 AND 1), 
	CONSTRAINT ck_recording_quality_results_provenance CHECK (length(provenance) > 0), 
	CONSTRAINT ck_recording_quality_results_version CHECK (version >= 1), 
	CONSTRAINT fk_recording_quality_results_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_recording_quality_results_recording FOREIGN KEY(recording_id) REFERENCES recordings (recording_id)
);

-- Table: transcript_segment_sets
CREATE TABLE transcript_segment_sets (
	transcript_segment_set_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	transcript_revision_id VARCHAR(64) NOT NULL, 
	transcript_content_sha256 VARCHAR(64) NOT NULL, 
	recording_id VARCHAR(64), 
	revision INTEGER NOT NULL, 
	source VARCHAR(32) NOT NULL, 
	review_state VARCHAR(32) NOT NULL, 
	segments_sha256 VARCHAR(64) NOT NULL, 
	created_by_user_id VARCHAR(128) NOT NULL, 
	attested_by_user_id VARCHAR(128), 
	attested_at TIMESTAMP WITH TIME ZONE, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (transcript_segment_set_id), 
	CONSTRAINT uq_segment_sets_organization_set_id UNIQUE (organization_id, transcript_segment_set_id), 
	CONSTRAINT uq_segment_sets_organization_assessment_revision UNIQUE (organization_id, assessment_id, revision), 
	CONSTRAINT fk_segment_sets_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT fk_segment_sets_transcript_tenant FOREIGN KEY(organization_id, transcript_revision_id) REFERENCES transcript_revisions (organization_id, transcript_revision_id), 
	CONSTRAINT fk_segment_sets_recording_tenant FOREIGN KEY(organization_id, recording_id) REFERENCES recordings (organization_id, recording_id), 
	CONSTRAINT ck_segment_sets_source CHECK (source IN ('manual', 'asr_draft', 'imported')), 
	CONSTRAINT ck_segment_sets_review_state CHECK (review_state IN ('draft', 'attested', 'superseded')), 
	CONSTRAINT ck_segment_sets_sha256 CHECK (length(segments_sha256) = 64), 
	CONSTRAINT ck_segment_sets_transcript_sha256 CHECK (length(transcript_content_sha256) = 64), 
	CONSTRAINT ck_segment_sets_attestation_metadata CHECK ((attested_by_user_id IS NULL AND attested_at IS NULL) OR (attested_by_user_id IS NOT NULL AND attested_at IS NOT NULL)), 
	CONSTRAINT ck_segment_sets_revision CHECK (revision >= 1), 
	CONSTRAINT ck_segment_sets_version CHECK (version >= 1), 
	CONSTRAINT fk_segment_sets_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_segment_sets_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_segment_sets_transcript FOREIGN KEY(transcript_revision_id) REFERENCES transcript_revisions (transcript_revision_id), 
	CONSTRAINT fk_segment_sets_recording FOREIGN KEY(recording_id) REFERENCES recordings (recording_id)
);

-- Table: evidence_runs
CREATE TABLE evidence_runs (
	evidence_run_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	transcript_revision_id VARCHAR(64) NOT NULL, 
	segment_set_id VARCHAR(64), 
	segment_set_sha256 VARCHAR(64), 
	state VARCHAR(32) NOT NULL, 
	input_ref VARCHAR(256) NOT NULL, 
	input_sha256 VARCHAR(64) NOT NULL, 
	protocol_version_key VARCHAR(128) NOT NULL, 
	extractor VARCHAR(128) NOT NULL, 
	pipeline_version VARCHAR(128) NOT NULL, 
	feature_schema_version VARCHAR(128) NOT NULL, 
	limitations_json JSON DEFAULT '[]' NOT NULL, 
	generated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (evidence_run_id), 
	CONSTRAINT uq_evidence_runs_organization_run UNIQUE (organization_id, evidence_run_id), 
	CONSTRAINT uq_evidence_runs_segment_identity UNIQUE (organization_id, assessment_id, transcript_revision_id, segment_set_id, segment_set_sha256, pipeline_version, feature_schema_version), 
	CONSTRAINT fk_evidence_runs_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT fk_evidence_runs_transcript_tenant FOREIGN KEY(organization_id, transcript_revision_id) REFERENCES transcript_revisions (organization_id, transcript_revision_id), 
	CONSTRAINT fk_evidence_runs_segment_set_tenant FOREIGN KEY(organization_id, segment_set_id) REFERENCES transcript_segment_sets (organization_id, transcript_segment_set_id), 
	CONSTRAINT ck_evidence_runs_state CHECK (state IN ('pending', 'processing', 'completed', 'needs_review', 'insufficient_data', 'unavailable', 'failed', 'stale')), 
	CONSTRAINT ck_evidence_runs_input_ref CHECK (length(input_ref) > 0), 
	CONSTRAINT ck_evidence_runs_input_sha256 CHECK (length(input_sha256) = 64), 
	CONSTRAINT ck_evidence_runs_protocol CHECK (length(protocol_version_key) > 0), 
	CONSTRAINT ck_evidence_runs_extractor CHECK (length(extractor) > 0), 
	CONSTRAINT ck_evidence_runs_pipeline CHECK (length(pipeline_version) > 0), 
	CONSTRAINT ck_evidence_runs_schema CHECK (length(feature_schema_version) > 0), 
	CONSTRAINT ck_evidence_runs_version CHECK (version >= 1), 
	CONSTRAINT ck_evidence_runs_segment_provenance CHECK ((segment_set_id IS NULL AND segment_set_sha256 IS NULL) OR (segment_set_id IS NOT NULL AND length(segment_set_sha256) = 64)), 
	CONSTRAINT fk_evidence_runs_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_evidence_runs_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_evidence_runs_transcript_revision FOREIGN KEY(transcript_revision_id) REFERENCES transcript_revisions (transcript_revision_id)
);

-- Table: transcript_segments
CREATE TABLE transcript_segments (
	transcript_segment_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	transcript_segment_set_id VARCHAR(64) NOT NULL, 
	ordinal INTEGER NOT NULL, 
	start_ms BIGINT NOT NULL, 
	end_ms BIGINT NOT NULL, 
	speaker_role VARCHAR(32) NOT NULL, 
	text TEXT NOT NULL, 
	confidence FLOAT, 
	uncertainty_reason VARCHAR(64) DEFAULT 'none' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (transcript_segment_id), 
	CONSTRAINT uq_segments_organization_segment_id UNIQUE (organization_id, transcript_segment_id), 
	CONSTRAINT uq_segments_organization_set_ordinal UNIQUE (organization_id, transcript_segment_set_id, ordinal), 
	CONSTRAINT fk_segments_segment_set_tenant FOREIGN KEY(organization_id, transcript_segment_set_id) REFERENCES transcript_segment_sets (organization_id, transcript_segment_set_id), 
	CONSTRAINT ck_segments_ordinal CHECK (ordinal >= 1), 
	CONSTRAINT ck_segments_start_ms CHECK (start_ms >= 0), 
	CONSTRAINT ck_segments_end_ms CHECK (end_ms > start_ms), 
	CONSTRAINT ck_segments_speaker_role CHECK (speaker_role IN ('child', 'therapist', 'caregiver', 'unknown')), 
	CONSTRAINT ck_segments_text CHECK (length(text) > 0), 
	CONSTRAINT ck_segments_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1), 
	CONSTRAINT ck_segments_uncertainty_reason CHECK (uncertainty_reason IN ('none', 'low_asr_confidence', 'unintelligible_audio', 'speaker_uncertain', 'timestamp_uncertain', 'manual_review')), 
	CONSTRAINT fk_segments_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_segments_segment_set FOREIGN KEY(transcript_segment_set_id) REFERENCES transcript_segment_sets (transcript_segment_set_id)
);

-- Table: assessment_clinical_reviews
CREATE TABLE assessment_clinical_reviews (
	review_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	child_id VARCHAR(64) NOT NULL, 
	evidence_run_id VARCHAR(64) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	disposition VARCHAR(64), 
	disposition_notes TEXT, 
	follow_up_plan_json JSON, 
	reviewed_by VARCHAR(128), 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	version INTEGER NOT NULL, 
	is_stale BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (review_id), 
	CONSTRAINT uq_clinical_reviews_org_id UNIQUE (organization_id, review_id), 
	CONSTRAINT uq_clinical_reviews_org_assessment UNIQUE (organization_id, assessment_id), 
	CONSTRAINT fk_clinical_reviews_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT fk_clinical_reviews_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_clinical_reviews_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_clinical_reviews_child FOREIGN KEY(child_id) REFERENCES children (child_id), 
	CONSTRAINT fk_clinical_reviews_evidence_run FOREIGN KEY(evidence_run_id) REFERENCES evidence_runs (evidence_run_id)
);

-- Table: assessment_comparisons
CREATE TABLE assessment_comparisons (
	comparison_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	child_id VARCHAR(64) NOT NULL, 
	baseline_assessment_id VARCHAR(64) NOT NULL, 
	current_assessment_id VARCHAR(64) NOT NULL, 
	baseline_evidence_run_id VARCHAR(64) NOT NULL, 
	current_evidence_run_id VARCHAR(64) NOT NULL, 
	baseline_evidence_sha256 VARCHAR(64) NOT NULL, 
	current_evidence_sha256 VARCHAR(64) NOT NULL, 
	policy_version VARCHAR(64) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	is_stale BOOLEAN NOT NULL, 
	compatible_feature_count INTEGER NOT NULL, 
	incompatible_feature_count INTEGER NOT NULL, 
	compared_by_user_id VARCHAR(128) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (comparison_id), 
	CONSTRAINT uq_comparisons_organization_comparison UNIQUE (organization_id, comparison_id), 
	CONSTRAINT uq_comparisons_org_baseline_current_policy UNIQUE (organization_id, baseline_evidence_run_id, current_evidence_run_id, policy_version), 
	CONSTRAINT fk_comparisons_child_tenant FOREIGN KEY(organization_id, child_id) REFERENCES children (organization_id, child_id), 
	CONSTRAINT fk_comparisons_baseline_assessment_tenant FOREIGN KEY(organization_id, baseline_assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT fk_comparisons_current_assessment_tenant FOREIGN KEY(organization_id, current_assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT fk_comparisons_baseline_evidence_run_tenant FOREIGN KEY(organization_id, baseline_evidence_run_id) REFERENCES evidence_runs (organization_id, evidence_run_id), 
	CONSTRAINT fk_comparisons_current_evidence_run_tenant FOREIGN KEY(organization_id, current_evidence_run_id) REFERENCES evidence_runs (organization_id, evidence_run_id), 
	CONSTRAINT fk_comparisons_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_comparisons_child FOREIGN KEY(child_id) REFERENCES children (child_id), 
	CONSTRAINT fk_comparisons_baseline_assessment FOREIGN KEY(baseline_assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_comparisons_current_assessment FOREIGN KEY(current_assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_comparisons_baseline_evidence_run FOREIGN KEY(baseline_evidence_run_id) REFERENCES evidence_runs (evidence_run_id), 
	CONSTRAINT fk_comparisons_current_evidence_run FOREIGN KEY(current_evidence_run_id) REFERENCES evidence_runs (evidence_run_id)
);

-- Table: evidence_domain_profiles
CREATE TABLE evidence_domain_profiles (
	domain_profile_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	evidence_run_id VARCHAR(64) NOT NULL, 
	domain VARCHAR(64) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	summary TEXT NOT NULL, 
	feature_keys_json JSON DEFAULT '[]' NOT NULL, 
	supporting_features_json JSON DEFAULT '[]' NOT NULL, 
	conflicting_features_json JSON DEFAULT '[]' NOT NULL, 
	limitations_json JSON DEFAULT '[]' NOT NULL, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (domain_profile_id), 
	CONSTRAINT uq_evidence_domains_organization_profile UNIQUE (organization_id, domain_profile_id), 
	CONSTRAINT uq_evidence_domains_run_domain UNIQUE (organization_id, evidence_run_id, domain), 
	CONSTRAINT fk_evidence_domains_run_tenant FOREIGN KEY(organization_id, evidence_run_id) REFERENCES evidence_runs (organization_id, evidence_run_id), 
	CONSTRAINT ck_evidence_domains_domain CHECK (domain IN ('expressive_language', 'speech_clarity_production', 'conversational_interaction', 'social_communication', 'repetitive_language', 'prosody_temporal_organization', 'evidence_quality_sufficiency')), 
	CONSTRAINT ck_evidence_domains_status CHECK (status IN ('descriptive_only', 'within_reference_band', 'outside_reference_band', 'attention_suggested', 'insufficient_data', 'reference_unavailable', 'not_assessed')), 
	CONSTRAINT ck_evidence_domains_summary CHECK (length(summary) > 0), 
	CONSTRAINT ck_evidence_domains_version CHECK (version >= 1), 
	CONSTRAINT fk_evidence_domains_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_evidence_domains_run FOREIGN KEY(evidence_run_id) REFERENCES evidence_runs (evidence_run_id)
);

-- Table: evidence_feature_values
CREATE TABLE evidence_feature_values (
	evidence_feature_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	evidence_run_id VARCHAR(64) NOT NULL, 
	feature_key VARCHAR(128) NOT NULL, 
	value_json JSON, 
	unit VARCHAR(64) NOT NULL, 
	source VARCHAR(32) NOT NULL, 
	state VARCHAR(32) NOT NULL, 
	limitation TEXT, 
	version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (evidence_feature_id), 
	CONSTRAINT uq_evidence_features_organization_feature UNIQUE (organization_id, evidence_feature_id), 
	CONSTRAINT uq_evidence_features_run_key UNIQUE (organization_id, evidence_run_id, feature_key), 
	CONSTRAINT fk_evidence_features_run_tenant FOREIGN KEY(organization_id, evidence_run_id) REFERENCES evidence_runs (organization_id, evidence_run_id), 
	CONSTRAINT ck_evidence_features_source CHECK (source IN ('reviewed_transcript', 'audio_quality', 'observation', 'instrument')), 
	CONSTRAINT ck_evidence_features_state CHECK (state IN ('pending', 'processing', 'completed', 'needs_review', 'insufficient_data', 'unavailable', 'failed', 'stale')), 
	CONSTRAINT ck_evidence_features_value_state CHECK ((state = 'completed' AND value_json IS NOT NULL) OR (state <> 'completed' AND value_json IS NULL AND length(limitation) > 0)), 
	CONSTRAINT ck_evidence_features_key CHECK (length(feature_key) > 0), 
	CONSTRAINT ck_evidence_features_unit CHECK (length(unit) > 0), 
	CONSTRAINT ck_evidence_features_version CHECK (version >= 1), 
	CONSTRAINT fk_evidence_features_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_evidence_features_run FOREIGN KEY(evidence_run_id) REFERENCES evidence_runs (evidence_run_id)
);

-- Table: processing_runs
CREATE TABLE processing_runs (
	processing_run_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	recording_id VARCHAR(64), 
	assessment_id VARCHAR(64), 
	transcript_revision_id VARCHAR(64), 
	evidence_run_id VARCHAR(64), 
	segment_set_id VARCHAR(64), 
	segment_set_sha256 VARCHAR(64), 
	stage VARCHAR(64) NOT NULL, 
	state VARCHAR(32) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	attempt_count INTEGER NOT NULL, 
	max_attempts INTEGER DEFAULT 3 NOT NULL, 
	available_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	error_code VARCHAR(64), 
	lease_token VARCHAR(128), 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	cancel_requested_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	pipeline_version VARCHAR(128), 
	feature_schema_version VARCHAR(128), 
	version INTEGER DEFAULT 1 NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (processing_run_id), 
	CONSTRAINT uq_processing_runs_organization_idempotency UNIQUE (organization_id, idempotency_key), 
	CONSTRAINT fk_processing_runs_recording_tenant FOREIGN KEY(organization_id, recording_id) REFERENCES recordings (organization_id, recording_id), 
	CONSTRAINT fk_processing_runs_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT fk_processing_runs_transcript_tenant FOREIGN KEY(organization_id, transcript_revision_id) REFERENCES transcript_revisions (organization_id, transcript_revision_id), 
	CONSTRAINT fk_processing_runs_evidence_tenant FOREIGN KEY(organization_id, evidence_run_id) REFERENCES evidence_runs (organization_id, evidence_run_id), 
	CONSTRAINT fk_processing_runs_segment_set_tenant FOREIGN KEY(organization_id, segment_set_id) REFERENCES transcript_segment_sets (organization_id, transcript_segment_set_id), 
	CONSTRAINT ck_processing_runs_stage CHECK (stage IN ('upload_verification', 'quality_analysis', 'cleanup', 'evidence_extraction')), 
	CONSTRAINT ck_processing_runs_state CHECK (state IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')), 
	CONSTRAINT ck_processing_runs_idempotency_key CHECK (length(idempotency_key) > 0), 
	CONSTRAINT ck_processing_runs_attempt_count CHECK (attempt_count >= 0), 
	CONSTRAINT ck_processing_runs_max_attempts CHECK (max_attempts >= 1), 
	CONSTRAINT ck_processing_runs_version CHECK (version >= 1), 
	CONSTRAINT ck_processing_runs_segment_provenance CHECK ((segment_set_id IS NULL AND segment_set_sha256 IS NULL) OR (segment_set_id IS NOT NULL AND length(segment_set_sha256) = 64)), 
	CONSTRAINT ck_processing_runs_target CHECK ((stage IN ('upload_verification', 'quality_analysis', 'cleanup') AND recording_id IS NOT NULL AND assessment_id IS NULL AND transcript_revision_id IS NULL) OR (stage = 'evidence_extraction' AND recording_id IS NULL AND assessment_id IS NOT NULL AND transcript_revision_id IS NOT NULL)), 
	CONSTRAINT fk_processing_runs_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_processing_runs_recording FOREIGN KEY(recording_id) REFERENCES recordings (recording_id), 
	CONSTRAINT fk_processing_runs_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_processing_runs_transcript_revision FOREIGN KEY(transcript_revision_id) REFERENCES transcript_revisions (transcript_revision_id), 
	CONSTRAINT fk_processing_runs_evidence_run FOREIGN KEY(evidence_run_id) REFERENCES evidence_runs (evidence_run_id)
);

-- Table: assessment_attention_cues
CREATE TABLE assessment_attention_cues (
	cue_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	review_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	cue_type VARCHAR(64) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	policy_version VARCHAR(64) NOT NULL, 
	evidence_run_id VARCHAR(64) NOT NULL, 
	supporting_feature_keys_json JSON DEFAULT '[]' NOT NULL, 
	conflicting_feature_keys_json JSON DEFAULT '[]' NOT NULL, 
	limitations_json JSON DEFAULT '[]' NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	reviewer_id VARCHAR(128), 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	rationale TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (cue_id), 
	CONSTRAINT uq_attention_cues_org_id UNIQUE (organization_id, cue_id), 
	CONSTRAINT fk_attention_cues_review_tenant FOREIGN KEY(organization_id, review_id) REFERENCES assessment_clinical_reviews (organization_id, review_id), 
	CONSTRAINT fk_attention_cues_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_attention_cues_review FOREIGN KEY(review_id) REFERENCES assessment_clinical_reviews (review_id), 
	CONSTRAINT fk_attention_cues_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_attention_cues_evidence_run FOREIGN KEY(evidence_run_id) REFERENCES evidence_runs (evidence_run_id)
);

-- Table: assessment_comparison_features
CREATE TABLE assessment_comparison_features (
	comparison_feature_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	comparison_id VARCHAR(64) NOT NULL, 
	feature_key VARCHAR(64) NOT NULL, 
	unit VARCHAR(32), 
	status VARCHAR(32) NOT NULL, 
	incompatibility_reasons_json JSON DEFAULT '[]' NOT NULL, 
	baseline_value FLOAT, 
	current_value FLOAT, 
	absolute_delta FLOAT, 
	percent_change FLOAT, 
	percent_change_limitation VARCHAR(64), 
	numerical_trend VARCHAR(32) NOT NULL, 
	clinical_interpretation VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (comparison_feature_id), 
	CONSTRAINT uq_comparison_features_org_id UNIQUE (organization_id, comparison_feature_id), 
	CONSTRAINT uq_comparison_features_org_comp_feature UNIQUE (organization_id, comparison_id, feature_key), 
	CONSTRAINT fk_comparison_features_comparison_tenant FOREIGN KEY(organization_id, comparison_id) REFERENCES assessment_comparisons (organization_id, comparison_id), 
	CONSTRAINT fk_comparison_features_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_comparison_features_comparison FOREIGN KEY(comparison_id) REFERENCES assessment_comparisons (comparison_id)
);

-- Table: assessment_reports
CREATE TABLE assessment_reports (
	report_id VARCHAR(64) NOT NULL, 
	organization_id VARCHAR(64) NOT NULL, 
	assessment_id VARCHAR(64) NOT NULL, 
	child_id VARCHAR(64) NOT NULL, 
	evidence_run_id VARCHAR(64) NOT NULL, 
	comparison_id VARCHAR(64), 
	review_id VARCHAR(64) NOT NULL, 
	amends_report_id VARCHAR(64), 
	amendment_sequence INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	purpose TEXT NOT NULL, 
	content_markdown TEXT NOT NULL, 
	limitations_json JSON DEFAULT '[]' NOT NULL, 
	signed_by VARCHAR(128), 
	signed_at TIMESTAMP WITH TIME ZONE, 
	signed_snapshot JSON, 
	signed_snapshot_hash VARCHAR(64), 
	is_stale BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (report_id), 
	CONSTRAINT uq_reports_org_id UNIQUE (organization_id, report_id), 
	CONSTRAINT fk_reports_assessment_tenant FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, assessment_id), 
	CONSTRAINT fk_reports_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id), 
	CONSTRAINT fk_reports_assessment FOREIGN KEY(assessment_id) REFERENCES assessments (assessment_id), 
	CONSTRAINT fk_reports_child FOREIGN KEY(child_id) REFERENCES children (child_id), 
	CONSTRAINT fk_reports_evidence_run FOREIGN KEY(evidence_run_id) REFERENCES evidence_runs (evidence_run_id), 
	CONSTRAINT fk_reports_comparison FOREIGN KEY(comparison_id) REFERENCES assessment_comparisons (comparison_id), 
	CONSTRAINT fk_reports_review FOREIGN KEY(review_id) REFERENCES assessment_clinical_reviews (review_id), 
	CONSTRAINT fk_reports_amends_report FOREIGN KEY(amends_report_id) REFERENCES assessment_reports (report_id)
);

-- ------------------------------------------------------------------------------
-- PART 4: PERFORMANCE & QUERY INDEXES
-- ------------------------------------------------------------------------------

CREATE INDEX ix_audit_events_organization_id ON audit_events (organization_id);
CREATE INDEX ix_audit_events_correlation_id ON audit_events (correlation_id);
CREATE INDEX ix_children_organization_id ON children (organization_id);
CREATE INDEX ix_organization_memberships_user_id ON organization_memberships (user_id);
CREATE INDEX ix_organization_memberships_organization_id ON organization_memberships (organization_id);
CREATE INDEX ix_protocol_activities_protocol_version_key ON protocol_activities (protocol_version_key);
CREATE INDEX ix_assessments_organization_id ON assessments (organization_id);
CREATE INDEX ix_assessments_child_id ON assessments (child_id);
CREATE INDEX ix_assessments_assigned_clinician_id ON assessments (assigned_clinician_id);
CREATE INDEX ix_care_team_assignments_user_id ON care_team_assignments (user_id);
CREATE INDEX ix_care_team_assignments_child_id ON care_team_assignments (child_id);
CREATE INDEX ix_care_team_assignments_organization_id ON care_team_assignments (organization_id);
CREATE INDEX ix_consent_records_child_id ON consent_records (child_id);
CREATE INDEX ix_consent_records_organization_id ON consent_records (organization_id);
CREATE INDEX ix_instruments_organization_assessment_administered ON assessment_instruments (organization_id, assessment_id, administered_at);
CREATE INDEX ix_assessment_instruments_organization_id ON assessment_instruments (organization_id);
CREATE INDEX ix_assessment_instruments_assessment_id ON assessment_instruments (assessment_id);
CREATE INDEX ix_observations_organization_assessment_created ON assessment_observations (organization_id, assessment_id, created_at);
CREATE INDEX ix_assessment_observations_assessment_id ON assessment_observations (assessment_id);
CREATE INDEX ix_assessment_observations_organization_id ON assessment_observations (organization_id);
CREATE INDEX ix_assessment_protocol_selections_selected_by_user_id ON assessment_protocol_selections (selected_by_user_id);
CREATE INDEX ix_assessment_protocol_selections_assessment_id ON assessment_protocol_selections (assessment_id);
CREATE INDEX ix_assessment_protocol_selections_organization_id ON assessment_protocol_selections (organization_id);
CREATE INDEX ix_transcript_revisions_organization_assessment_revision ON transcript_revisions (organization_id, assessment_id, revision);
CREATE INDEX ix_transcript_revisions_assessment_id ON transcript_revisions (assessment_id);
CREATE INDEX ix_transcript_revisions_organization_id ON transcript_revisions (organization_id);
CREATE INDEX ix_assessment_instrument_items_administration_id ON assessment_instrument_items (administration_id);
CREATE INDEX ix_assessment_instrument_items_organization_id ON assessment_instrument_items (organization_id);
CREATE INDEX ix_instrument_items_organization_admin ON assessment_instrument_items (organization_id, administration_id);
CREATE INDEX ix_recordings_organization_upload_state_expiry ON recordings (organization_id, upload_state, expires_at);
CREATE INDEX ix_recordings_activity_key ON recordings (activity_key);
CREATE INDEX ix_recordings_organization_id ON recordings (organization_id);
CREATE INDEX ix_recordings_assessment_id ON recordings (assessment_id);
CREATE INDEX ix_recordings_organization_assessment ON recordings (organization_id, assessment_id);
CREATE INDEX ix_recordings_upload_state ON recordings (upload_state);
CREATE INDEX ix_recording_quality_results_organization_status ON recording_quality_results (organization_id, status);
CREATE INDEX ix_recording_quality_results_recording_id ON recording_quality_results (recording_id);
CREATE INDEX ix_recording_quality_results_organization_id ON recording_quality_results (organization_id);
CREATE INDEX ix_transcript_segment_sets_transcript_revision_id ON transcript_segment_sets (transcript_revision_id);
CREATE INDEX ix_transcript_segment_sets_assessment_id ON transcript_segment_sets (assessment_id);
CREATE INDEX ix_segment_sets_organization_assessment_revision ON transcript_segment_sets (organization_id, assessment_id, revision);
CREATE INDEX ix_transcript_segment_sets_organization_id ON transcript_segment_sets (organization_id);
CREATE INDEX ix_transcript_segment_sets_recording_id ON transcript_segment_sets (recording_id);
CREATE INDEX ix_evidence_runs_state ON evidence_runs (state);
CREATE INDEX ix_evidence_runs_organization_id ON evidence_runs (organization_id);
CREATE INDEX ix_evidence_runs_assessment_id ON evidence_runs (assessment_id);
CREATE INDEX ix_evidence_runs_organization_segment_set ON evidence_runs (organization_id, segment_set_id);
CREATE INDEX ix_evidence_runs_segment_set_id ON evidence_runs (segment_set_id);
CREATE INDEX ix_evidence_runs_transcript_revision_id ON evidence_runs (transcript_revision_id);
CREATE INDEX ix_evidence_runs_organization_assessment_created ON evidence_runs (organization_id, assessment_id, created_at);
CREATE INDEX ix_segments_organization_set_ordinal ON transcript_segments (organization_id, transcript_segment_set_id, ordinal);
CREATE INDEX ix_transcript_segments_transcript_segment_set_id ON transcript_segments (transcript_segment_set_id);
CREATE INDEX ix_transcript_segments_organization_id ON transcript_segments (organization_id);
CREATE INDEX ix_assessment_clinical_reviews_assessment_id ON assessment_clinical_reviews (assessment_id);
CREATE INDEX ix_clinical_reviews_org_assessment ON assessment_clinical_reviews (organization_id, assessment_id);
CREATE INDEX ix_assessment_clinical_reviews_evidence_run_id ON assessment_clinical_reviews (evidence_run_id);
CREATE INDEX ix_assessment_clinical_reviews_child_id ON assessment_clinical_reviews (child_id);
CREATE INDEX ix_assessment_clinical_reviews_organization_id ON assessment_clinical_reviews (organization_id);
CREATE INDEX ix_comparisons_organization_current ON assessment_comparisons (organization_id, current_assessment_id);
CREATE INDEX ix_comparisons_organization_child ON assessment_comparisons (organization_id, child_id);
CREATE INDEX ix_assessment_comparisons_organization_id ON assessment_comparisons (organization_id);
CREATE INDEX ix_assessment_comparisons_child_id ON assessment_comparisons (child_id);
CREATE INDEX ix_assessment_comparisons_current_evidence_run_id ON assessment_comparisons (current_evidence_run_id);
CREATE INDEX ix_assessment_comparisons_baseline_evidence_run_id ON assessment_comparisons (baseline_evidence_run_id);
CREATE INDEX ix_assessment_comparisons_current_assessment_id ON assessment_comparisons (current_assessment_id);
CREATE INDEX ix_assessment_comparisons_baseline_assessment_id ON assessment_comparisons (baseline_assessment_id);
CREATE INDEX ix_evidence_domain_profiles_organization_id ON evidence_domain_profiles (organization_id);
CREATE INDEX ix_evidence_domain_profiles_evidence_run_id ON evidence_domain_profiles (evidence_run_id);
CREATE INDEX ix_evidence_domains_organization_run ON evidence_domain_profiles (organization_id, evidence_run_id);
CREATE INDEX ix_evidence_feature_values_evidence_run_id ON evidence_feature_values (evidence_run_id);
CREATE INDEX ix_evidence_feature_values_organization_id ON evidence_feature_values (organization_id);
CREATE INDEX ix_evidence_features_organization_run ON evidence_feature_values (organization_id, evidence_run_id);
CREATE INDEX ix_processing_runs_organization_state_available ON processing_runs (organization_id, state, available_at);
CREATE INDEX ix_processing_runs_organization_id ON processing_runs (organization_id);
CREATE INDEX ix_processing_runs_organization_segment_set ON processing_runs (organization_id, segment_set_id);
CREATE INDEX ix_processing_runs_segment_set_id ON processing_runs (segment_set_id);
CREATE INDEX ix_processing_runs_organization_stage_state_available ON processing_runs (organization_id, stage, state, available_at);
CREATE INDEX ix_processing_runs_evidence_run_id ON processing_runs (evidence_run_id);
CREATE INDEX ix_processing_runs_transcript_revision_id ON processing_runs (transcript_revision_id);
CREATE INDEX ix_processing_runs_assessment_id ON processing_runs (assessment_id);
CREATE INDEX ix_processing_runs_organization_stage_lease ON processing_runs (organization_id, stage, state, lease_expires_at);
CREATE INDEX ix_processing_runs_recording_id ON processing_runs (recording_id);
CREATE INDEX ix_processing_runs_organization_recording ON processing_runs (organization_id, recording_id);
CREATE INDEX ix_assessment_attention_cues_assessment_id ON assessment_attention_cues (assessment_id);
CREATE INDEX ix_attention_cues_org_review ON assessment_attention_cues (organization_id, review_id);
CREATE INDEX ix_attention_cues_org_assessment ON assessment_attention_cues (organization_id, assessment_id);
CREATE INDEX ix_assessment_attention_cues_organization_id ON assessment_attention_cues (organization_id);
CREATE INDEX ix_assessment_attention_cues_review_id ON assessment_attention_cues (review_id);
CREATE INDEX ix_comparison_features_org_comp ON assessment_comparison_features (organization_id, comparison_id);
CREATE INDEX ix_assessment_comparison_features_comparison_id ON assessment_comparison_features (comparison_id);
CREATE INDEX ix_assessment_comparison_features_organization_id ON assessment_comparison_features (organization_id);
CREATE INDEX ix_reports_snapshot_hash ON assessment_reports (signed_snapshot_hash);
CREATE INDEX ix_assessment_reports_child_id ON assessment_reports (child_id);
CREATE INDEX ix_assessment_reports_evidence_run_id ON assessment_reports (evidence_run_id);
CREATE INDEX ix_reports_org_assessment ON assessment_reports (organization_id, assessment_id);
CREATE INDEX ix_assessment_reports_organization_id ON assessment_reports (organization_id);
CREATE INDEX ix_assessment_reports_review_id ON assessment_reports (review_id);
CREATE INDEX ix_reports_org_status ON assessment_reports (organization_id, status);
CREATE INDEX ix_assessment_reports_signed_snapshot_hash ON assessment_reports (signed_snapshot_hash);
CREATE INDEX ix_assessment_reports_assessment_id ON assessment_reports (assessment_id);

-- ------------------------------------------------------------------------------
-- PART 5: ROW LEVEL SECURITY (RLS) POLICIES
-- ------------------------------------------------------------------------------
-- Organizations access
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizations FORCE ROW LEVEL SECURITY;
CREATE POLICY organizations_access ON public.organizations
  FOR SELECT
  USING (
    public.is_org_member(organization_id)
    OR auth.role() = 'service_role'
    OR current_setting('app.current_organization_id', true) IS NOT NULL
  );

-- User Profiles access
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles FORCE ROW LEVEL SECURITY;
CREATE POLICY user_profiles_access ON public.user_profiles
  FOR ALL
  USING (
    user_id = auth.uid()::text
    OR auth.role() = 'service_role'
    OR current_setting('app.current_organization_id', true) IS NOT NULL
    OR EXISTS (
      SELECT 1 FROM public.organization_memberships m1
      JOIN public.organization_memberships m2 ON m1.organization_id = m2.organization_id
      WHERE m1.user_id = auth.uid()::text AND m2.user_id = public.user_profiles.user_id
    )
  );

-- Organization Memberships access
ALTER TABLE public.organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organization_memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY organization_memberships_access ON public.organization_memberships
  FOR ALL
  USING (
    user_id = auth.uid()::text
    OR public.is_org_member(organization_id)
    OR auth.role() = 'service_role'
  );

-- Protocol Catalogs (global read)
ALTER TABLE public.protocol_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.protocol_versions FORCE ROW LEVEL SECURITY;
CREATE POLICY protocol_versions_read ON public.protocol_versions FOR SELECT USING (true);

ALTER TABLE public.protocol_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.protocol_activities FORCE ROW LEVEL SECURITY;
CREATE POLICY protocol_activities_read ON public.protocol_activities FOR SELECT USING (true);

ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_events_tenant_isolation ON public.audit_events
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.children ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.children FORCE ROW LEVEL SECURITY;
CREATE POLICY children_tenant_isolation ON public.children
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.care_team_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.care_team_assignments FORCE ROW LEVEL SECURITY;
CREATE POLICY care_team_assignments_tenant_isolation ON public.care_team_assignments
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consent_records FORCE ROW LEVEL SECURITY;
CREATE POLICY consent_records_tenant_isolation ON public.consent_records
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessments FORCE ROW LEVEL SECURITY;
CREATE POLICY assessments_tenant_isolation ON public.assessments
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessment_instruments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_instruments FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_instruments_tenant_isolation ON public.assessment_instruments
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessment_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_observations FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_observations_tenant_isolation ON public.assessment_observations
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessment_protocol_selections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_protocol_selections FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_protocol_selections_tenant_isolation ON public.assessment_protocol_selections
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.transcript_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcript_revisions FORCE ROW LEVEL SECURITY;
CREATE POLICY transcript_revisions_tenant_isolation ON public.transcript_revisions
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessment_instrument_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_instrument_items FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_instrument_items_tenant_isolation ON public.assessment_instrument_items
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.recordings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recordings FORCE ROW LEVEL SECURITY;
CREATE POLICY recordings_tenant_isolation ON public.recordings
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.recording_quality_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recording_quality_results FORCE ROW LEVEL SECURITY;
CREATE POLICY recording_quality_results_tenant_isolation ON public.recording_quality_results
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.transcript_segment_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcript_segment_sets FORCE ROW LEVEL SECURITY;
CREATE POLICY transcript_segment_sets_tenant_isolation ON public.transcript_segment_sets
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.evidence_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY evidence_runs_tenant_isolation ON public.evidence_runs
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.transcript_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcript_segments FORCE ROW LEVEL SECURITY;
CREATE POLICY transcript_segments_tenant_isolation ON public.transcript_segments
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessment_clinical_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_clinical_reviews FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_clinical_reviews_tenant_isolation ON public.assessment_clinical_reviews
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessment_comparisons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_comparisons FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_comparisons_tenant_isolation ON public.assessment_comparisons
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.evidence_domain_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_domain_profiles FORCE ROW LEVEL SECURITY;
CREATE POLICY evidence_domain_profiles_tenant_isolation ON public.evidence_domain_profiles
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.evidence_feature_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_feature_values FORCE ROW LEVEL SECURITY;
CREATE POLICY evidence_feature_values_tenant_isolation ON public.evidence_feature_values
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.processing_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processing_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY processing_runs_tenant_isolation ON public.processing_runs
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessment_attention_cues ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_attention_cues FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_attention_cues_tenant_isolation ON public.assessment_attention_cues
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessment_comparison_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_comparison_features FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_comparison_features_tenant_isolation ON public.assessment_comparison_features
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

ALTER TABLE public.assessment_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_reports FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_reports_tenant_isolation ON public.assessment_reports
  FOR ALL
  USING (public.is_org_member(organization_id))
  WITH CHECK (public.is_org_member(organization_id));

-- ------------------------------------------------------------------------------
-- PART 6: SUPABASE AUTH INTEGRATION TRIGGER
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  default_org_id text := 'org_alpha';
  user_display text;
BEGIN
  user_display := coalesce(
    new.raw_user_meta_data->>'full_name',
    new.raw_user_meta_data->>'name',
    split_part(new.email, '@', 1),
    'Therapist User'
  );

  INSERT INTO public.user_profiles (user_id, display_label, created_at, updated_at)
  VALUES (new.id::text, user_display, now(), now())
  ON CONFLICT (user_id) DO UPDATE
  SET display_label = EXCLUDED.display_label,
      updated_at = now();

  INSERT INTO public.organization_memberships (
    membership_id, organization_id, user_id, role, active, created_at, updated_at
  )
  VALUES (
    'mem_' || substr(md5(new.id::text || default_org_id), 1, 16),
    default_org_id,
    new.id::text,
    'therapist',
    true,
    now(),
    now()
  )
  ON CONFLICT (organization_id, user_id) DO NOTHING;

  RETURN new;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ------------------------------------------------------------------------------
-- PART 7: SUPABASE STORAGE BUCKET & POLICIES
-- ------------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'audio-recordings',
  'audio-recordings',
  false,
  104857600,
  ARRAY['audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/mp3', 'audio/m4a', 'audio/x-m4a', 'audio/flac', 'audio/ogg', 'audio/webm']
)
ON CONFLICT (id) DO UPDATE
SET public = false,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS "Authenticated users can upload audio files" ON storage.objects;
CREATE POLICY "Authenticated users can upload audio files"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'audio-recordings');

DROP POLICY IF EXISTS "Authenticated users can read audio files" ON storage.objects;
CREATE POLICY "Authenticated users can read audio files"
ON storage.objects FOR SELECT TO authenticated
USING (bucket_id = 'audio-recordings');

DROP POLICY IF EXISTS "Service role has full storage access" ON storage.objects;
CREATE POLICY "Service role has full storage access"
ON storage.objects FOR ALL TO service_role
USING (bucket_id = 'audio-recordings')
WITH CHECK (bucket_id = 'audio-recordings');

-- ------------------------------------------------------------------------------
-- PART 8: CLINICAL PILOT SEED DATA
-- ------------------------------------------------------------------------------
INSERT INTO public.organizations (organization_id, display_label, active, created_at, updated_at)
VALUES ('org_alpha', 'LinguaLens Clinical Pilot Clinic', true, now(), now())
ON CONFLICT (organization_id) DO NOTHING;

INSERT INTO public.protocol_versions (
  protocol_version_key, display_label, description, primary_language,
  minimum_age_months, maximum_age_months, supported_purposes, active, created_at, updated_at
)
VALUES (
  'thai_guided_language_sample:v0',
  'Thai Guided Language Sample Protocol v0',
  'Standardized guided language sample protocol for Thai pediatric language and communication assessment.',
  'th',
  18,
  72,
  'initial,developmental_follow_up,post_intervention_follow_up,additional_evidence',
  true,
  now(),
  now()
)
ON CONFLICT (protocol_version_key) DO NOTHING;

INSERT INTO public.protocol_activities (
  protocol_version_key, activity_key, display_label, prompt_summary,
  required, target_duration_seconds, minimum_duration_seconds, sort_order, active, created_at, updated_at
)
VALUES
  ('thai_guided_language_sample:v0', 'free_play', 'Free Play Interaction (การเล่นอิสระ)', 'Semi-structured play with familiar toys to elicit spontaneous child-directed vocalizations.', true, 180, 120, 1, true, now(), now()),
  ('thai_guided_language_sample:v0', 'shared_book', 'Shared Book Reading (การอ่านหนังสือนิทานร่วมกัน)', 'Dialogic book sharing to assess joint attention, pointing, and narrative vocabulary.', false, 120, 60, 2, true, now(), now()),
  ('thai_guided_language_sample:v0', 'turn_taking', 'Turn-Taking Social Routine (กิจกรรมผลัดกันพูด)', 'Structured turn-taking routine or game to evaluate reciprocal social communication.', false, 120, 60, 3, true, now(), now())
ON CONFLICT (protocol_version_key, activity_key) DO NOTHING;

-- Backfill existing Supabase Auth users into user_profiles & organization_memberships
INSERT INTO public.user_profiles (user_id, display_label, created_at, updated_at)
SELECT
  id::text,
  coalesce(raw_user_meta_data->>'full_name', raw_user_meta_data->>'name', split_part(email, '@', 1), 'Therapist User'),
  created_at,
  coalesce(updated_at, created_at)
FROM auth.users
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO public.organization_memberships (
  membership_id, organization_id, user_id, role, active, created_at, updated_at
)
SELECT
  'mem_' || substr(md5(id::text || 'org_alpha'), 1, 16),
  'org_alpha',
  id::text,
  'therapist',
  true,
  created_at,
  coalesce(updated_at, created_at)
FROM auth.users
ON CONFLICT (organization_id, user_id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- PART 9: ALEMBIC VERSION REGISTRATION
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.alembic_version (
  version_num VARCHAR(32) NOT NULL,
  CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

DELETE FROM public.alembic_version;
INSERT INTO public.alembic_version (version_num) VALUES ('0012_clinical_review_reports');

-- Completion notification
DO $$
BEGIN
  RAISE NOTICE 'LinguaLens Assessment V2 clean-slate initialization completed successfully.';
END;
$$;

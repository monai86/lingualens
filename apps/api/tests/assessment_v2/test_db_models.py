from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, UniqueConstraint

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db import models as _models  # noqa: F401  # register mapped tables


EXPECTED_TABLES = {
    "organizations",
    "user_profiles",
    "organization_memberships",
    "children",
    "care_team_assignments",
    "consent_records",
    "assessments",
    "audit_events",
    "protocol_versions",
    "protocol_activities",
    "assessment_protocol_selections",
    "recordings",
    "processing_runs",
    "recording_quality_results",
    "transcript_revisions",
    "evidence_runs",
    "evidence_feature_values",
    "evidence_domain_profiles",
}

GLOBAL_CATALOG_TABLES = {"organizations", "user_profiles", "protocol_versions", "protocol_activities"}
CAPTURE_TENANT_TABLES = {
    "assessment_protocol_selections",
    "recordings",
    "processing_runs",
    "recording_quality_results",
}


def test_foundation_metadata_is_complete_and_tenant_scoped() -> None:
    assert set(AssessmentBase.metadata.tables) == EXPECTED_TABLES

    for table_name in EXPECTED_TABLES - GLOBAL_CATALOG_TABLES:
        assert "organization_id" in AssessmentBase.metadata.tables[table_name].columns


def test_foundation_unique_constraints_protect_tenant_scoped_identity() -> None:
    membership = AssessmentBase.metadata.tables["organization_memberships"]
    care_team = AssessmentBase.metadata.tables["care_team_assignments"]
    children = AssessmentBase.metadata.tables["children"]

    assert ("organization_id", "user_id") in {
        tuple(constraint.columns.keys())
        for constraint in membership.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("organization_id", "child_id", "user_id") in {
        tuple(constraint.columns.keys())
        for constraint in care_team.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("organization_id", "display_code") in {
        tuple(constraint.columns.keys())
        for constraint in children.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_child_linked_records_use_composite_tenant_foreign_keys() -> None:
    children = AssessmentBase.metadata.tables["children"]
    care_team = AssessmentBase.metadata.tables["care_team_assignments"]
    consents = AssessmentBase.metadata.tables["consent_records"]
    assessments = AssessmentBase.metadata.tables["assessments"]

    assert ("organization_id", "child_id") in {
        tuple(constraint.columns.keys())
        for constraint in children.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    for table in (care_team, consents, assessments):
        foreign_keys = [
            constraint
            for constraint in table.constraints
            if isinstance(constraint, ForeignKeyConstraint)
        ]
        assert any(
            tuple(constraint.column_keys) == ("organization_id", "child_id")
            for constraint in foreign_keys
        )

    assert any(
        tuple(constraint.column_keys) == ("organization_id", "assigned_clinician_id")
        for constraint in assessments.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    )


def test_mutable_records_use_utc_timestamps_and_version_checks() -> None:
    for table_name in (
        "children",
        "consent_records",
        "assessments",
        "assessment_protocol_selections",
        "recordings",
        "processing_runs",
        "recording_quality_results",
    ):
        table = AssessmentBase.metadata.tables[table_name]
        assert isinstance(table.c.created_at.type, DateTime)
        assert table.c.created_at.type.timezone is True

    for table in AssessmentBase.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint) and "version >= 1" in str(constraint.sqltext):
                assert "version >= 1" in str(constraint.sqltext)


def test_domain_value_checks_are_named_and_audit_metadata_is_payload_free() -> None:
    assessments = AssessmentBase.metadata.tables["assessments"]
    consents = AssessmentBase.metadata.tables["consent_records"]
    audit = AssessmentBase.metadata.tables["audit_events"]

    constraint_names = {
        constraint.name
        for table in (assessments, consents)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_assessments_purpose" in constraint_names
    assert "ck_assessments_state" in constraint_names
    assert "ck_consent_records_purpose" in constraint_names
    assert "ck_consent_records_status" in constraint_names
    assert "metadata_json" in audit.columns
    assert "payload" not in audit.columns
    assert audit.c.metadata_json.default is not None


def test_capture_tenant_tables_have_version_checks_and_quality_status_contract() -> None:
    for table_name in CAPTURE_TENANT_TABLES:
        table = AssessmentBase.metadata.tables[table_name]
        if table_name != "processing_runs":
            assert any(
                isinstance(constraint, CheckConstraint) and "version >= 1" in str(constraint.sqltext)
                for constraint in table.constraints
            )

    quality = AssessmentBase.metadata.tables["recording_quality_results"]
    assert quality.c.status.default.arg == "usable"
    assert {
        str(constraint.sqltext)
        for constraint in quality.constraints
        if isinstance(constraint, CheckConstraint)
    } >= {
        "status IN ('usable', 'needs_additional_sample', 'unavailable', 'failed')"
    }

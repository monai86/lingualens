"""Create the assessment v2 capture protocol and recording foundation."""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0003_capture_protocols_recordings"
down_revision = "0002_assessment_tenant_integrity"
branch_labels = None
depends_on = None


_PROTOCOL_VERSION_KEY = "thai_guided_language_sample:v0"
_SUPPORTED_PURPOSES = "initial,developmental_follow_up,post_intervention_follow_up,additional_evidence"


def _enable_tenant_rls(table_name: str, policy_name: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"CREATE POLICY {policy_name} ON {table_name} "
            "USING (organization_id = current_setting('app.current_organization_id', true)) "
            "WITH CHECK (organization_id = current_setting('app.current_organization_id', true))"
        )
    )


def _disable_tenant_rls(table_name: str, policy_name: str) -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}"))


def _catalog_triggers() -> tuple[tuple[str, str, str], ...]:
    return (
        ("protocol_versions_immutable_update", "protocol_versions", "UPDATE"),
        ("protocol_versions_immutable_delete", "protocol_versions", "DELETE"),
        ("protocol_activities_immutable_update", "protocol_activities", "UPDATE"),
        ("protocol_activities_immutable_delete", "protocol_activities", "DELETE"),
    )


def _install_catalog_immutability_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        for trigger_name, table_name, event in _catalog_triggers():
            op.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_name}"))
            op.execute(
                sa.text(
                    f"CREATE TRIGGER {trigger_name} BEFORE {event} ON {table_name} "
                    "BEGIN SELECT RAISE(ABORT, 'assessment v2 protocol catalog is immutable'); END"
                )
            )
        return

    if dialect == "postgresql":
        op.execute(
            sa.text(
                "CREATE OR REPLACE FUNCTION assessment_v2_reject_catalog_mutation() "
                "RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'assessment v2 protocol catalog is immutable'; "
                "RETURN NULL; END; $$"
            )
        )
        for trigger_name, table_name, event in (
            ("protocol_versions_immutable_mutation", "protocol_versions", "UPDATE OR DELETE"),
            ("protocol_activities_immutable_mutation", "protocol_activities", "UPDATE OR DELETE"),
        ):
            op.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}"))
            op.execute(
                sa.text(
                    f"CREATE TRIGGER {trigger_name} BEFORE {event} ON {table_name} "
                    "FOR EACH ROW EXECUTE FUNCTION assessment_v2_reject_catalog_mutation()"
                )
            )
        return

    raise RuntimeError(f"assessment v2 catalog immutability is unsupported for {dialect}")


def _remove_catalog_immutability_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        for trigger_name, _, _ in _catalog_triggers():
            op.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_name}"))
        return

    if dialect == "postgresql":
        op.execute(sa.text("DROP TRIGGER IF EXISTS protocol_versions_immutable_mutation ON protocol_versions"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS protocol_activities_immutable_mutation ON protocol_activities"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS assessment_v2_reject_catalog_mutation()"))
        return

    raise RuntimeError(f"assessment v2 catalog immutability is unsupported for {dialect}")


def upgrade() -> None:
    with op.batch_alter_table("assessments") as batch:
        batch.create_unique_constraint(
            "uq_assessments_organization_assessment",
            ["organization_id", "assessment_id"],
        )

    op.create_table(
        "protocol_versions",
        sa.Column("protocol_version_key", sa.String(length=128), nullable=False),
        sa.Column("primary_language", sa.String(length=16), nullable=False),
        sa.Column("minimum_age_months", sa.Integer(), nullable=False),
        sa.Column("maximum_age_months", sa.Integer(), nullable=False),
        sa.Column("supported_purposes", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("protocol_version_key", name="pk_protocol_versions"),
        sa.CheckConstraint("length(primary_language) > 0", name="ck_protocol_versions_primary_language"),
        sa.CheckConstraint("minimum_age_months >= 0", name="ck_protocol_versions_minimum_age"),
        sa.CheckConstraint(
            "maximum_age_months >= minimum_age_months",
            name="ck_protocol_versions_age_range",
        ),
        sa.CheckConstraint("length(supported_purposes) > 0", name="ck_protocol_versions_supported_purposes"),
    )
    op.create_table(
        "protocol_activities",
        sa.Column("protocol_version_key", sa.String(length=128), nullable=False),
        sa.Column("activity_key", sa.String(length=64), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("target_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("minimum_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["protocol_version_key"],
            ["protocol_versions.protocol_version_key"],
            name="fk_protocol_activities_protocol_version",
        ),
        sa.PrimaryKeyConstraint("protocol_version_key", "activity_key", name="pk_protocol_activities"),
        sa.CheckConstraint("target_duration_seconds > 0", name="ck_protocol_activities_target_duration"),
        sa.CheckConstraint("minimum_duration_seconds > 0", name="ck_protocol_activities_minimum_duration"),
        sa.CheckConstraint(
            "target_duration_seconds >= minimum_duration_seconds",
            name="ck_protocol_activities_duration_range",
        ),
        sa.CheckConstraint("sort_order >= 1", name="ck_protocol_activities_sort_order"),
    )
    op.create_index(
        "ix_protocol_activities_protocol_version_key",
        "protocol_activities",
        ["protocol_version_key"],
    )

    op.create_table(
        "assessment_protocol_selections",
        sa.Column("assessment_protocol_selection_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("protocol_version_key", sa.String(length=128), nullable=False),
        sa.Column("selected_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_assessment_protocol_selections_organization",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_assessment_protocol_selections_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["protocol_version_key"],
            ["protocol_versions.protocol_version_key"],
            name="fk_assessment_protocol_selections_protocol",
        ),
        sa.ForeignKeyConstraint(
            ["selected_by_user_id"],
            ["user_profiles.user_id"],
            name="fk_assessment_protocol_selections_actor",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_assessment_protocol_selections_assessment_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "selected_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
            name="fk_assessment_protocol_selections_actor_membership_tenant",
        ),
        sa.PrimaryKeyConstraint(
            "assessment_protocol_selection_id",
            name="pk_assessment_protocol_selections",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "assessment_id",
            name="uq_assessment_protocol_selections_organization_assessment",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "assessment_id",
            "protocol_version_key",
            name="uq_aps_org_assessment_protocol",
        ),
        sa.CheckConstraint("version >= 1", name="ck_assessment_protocol_selections_version"),
    )
    op.create_index(
        "ix_assessment_protocol_selections_organization_id",
        "assessment_protocol_selections",
        ["organization_id"],
    )
    op.create_index(
        "ix_assessment_protocol_selections_assessment_id",
        "assessment_protocol_selections",
        ["assessment_id"],
    )
    op.create_index(
        "ix_assessment_protocol_selections_selected_by_user_id",
        "assessment_protocol_selections",
        ["selected_by_user_id"],
    )

    op.create_table(
        "recordings",
        sa.Column("recording_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("protocol_version_key", sa.String(length=128), nullable=False),
        sa.Column("activity_key", sa.String(length=64), nullable=False),
        sa.Column("declared_content_type", sa.String(length=128), nullable=False),
        sa.Column("declared_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("declared_checksum", sa.String(length=128), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("upload_state", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_content_type", sa.String(length=128), nullable=True),
        sa.Column("verified_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("verified_checksum", sa.String(length=128), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_recordings_organization",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_recordings_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["protocol_version_key"],
            ["protocol_versions.protocol_version_key"],
            name="fk_recordings_protocol_version",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_recordings_assessment_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id", "protocol_version_key"],
            [
                "assessment_protocol_selections.organization_id",
                "assessment_protocol_selections.assessment_id",
                "assessment_protocol_selections.protocol_version_key",
            ],
            name="fk_recordings_assessment_protocol_selection_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["protocol_version_key", "activity_key"],
            ["protocol_activities.protocol_version_key", "protocol_activities.activity_key"],
            name="fk_recordings_protocol_activity",
        ),
        sa.PrimaryKeyConstraint("recording_id", name="pk_recordings"),
        sa.UniqueConstraint("organization_id", "recording_id", name="uq_recordings_organization_recording"),
        sa.UniqueConstraint("object_key", name="uq_recordings_object_key"),
        sa.CheckConstraint("declared_size_bytes > 0", name="ck_recordings_declared_size"),
        sa.CheckConstraint("length(declared_content_type) > 0", name="ck_recordings_declared_content_type"),
        sa.CheckConstraint("length(declared_checksum) > 0", name="ck_recordings_declared_checksum"),
        sa.CheckConstraint("length(object_key) > 0", name="ck_recordings_object_key"),
        sa.CheckConstraint(
            "upload_state IN ('pending', 'uploading', 'uploaded', 'verified', 'expired', 'failed')",
            name="ck_recordings_upload_state",
        ),
        sa.CheckConstraint(
            "verified_size_bytes IS NULL OR verified_size_bytes > 0",
            name="ck_recordings_verified_size",
        ),
        sa.CheckConstraint(
            "(verified_content_type IS NULL AND verified_size_bytes IS NULL "
            "AND verified_checksum IS NULL AND verified_at IS NULL) OR "
            "(verified_content_type IS NOT NULL AND verified_size_bytes IS NOT NULL "
            "AND verified_checksum IS NOT NULL AND verified_at IS NOT NULL)",
            name="ck_recordings_verified_metadata_complete",
        ),
        sa.CheckConstraint("version >= 1", name="ck_recordings_version"),
    )
    op.create_index("ix_recordings_organization_id", "recordings", ["organization_id"])
    op.create_index("ix_recordings_assessment_id", "recordings", ["assessment_id"])
    op.create_index("ix_recordings_activity_key", "recordings", ["activity_key"])
    op.create_index("ix_recordings_upload_state", "recordings", ["upload_state"])
    op.create_index(
        "ix_recordings_organization_assessment",
        "recordings",
        ["organization_id", "assessment_id"],
    )
    op.create_index(
        "ix_recordings_organization_upload_state_expiry",
        "recordings",
        ["organization_id", "upload_state", "expires_at"],
    )

    op.create_table(
        "processing_runs",
        sa.Column("processing_run_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("recording_id", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_processing_runs_organization",
        ),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recordings.recording_id"],
            name="fk_processing_runs_recording",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "recording_id"],
            ["recordings.organization_id", "recordings.recording_id"],
            name="fk_processing_runs_recording_tenant",
        ),
        sa.PrimaryKeyConstraint("processing_run_id", name="pk_processing_runs"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_processing_runs_organization_idempotency",
        ),
        sa.CheckConstraint(
            "stage IN ('upload_verification', 'quality_analysis')",
            name="ck_processing_runs_stage",
        ),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_processing_runs_state",
        ),
        sa.CheckConstraint("length(idempotency_key) > 0", name="ck_processing_runs_idempotency_key"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_processing_runs_attempt_count"),
    )
    op.create_index("ix_processing_runs_organization_id", "processing_runs", ["organization_id"])
    op.create_index("ix_processing_runs_recording_id", "processing_runs", ["recording_id"])
    op.create_index(
        "ix_processing_runs_organization_recording",
        "processing_runs",
        ["organization_id", "recording_id"],
    )
    op.create_index(
        "ix_processing_runs_organization_state_available",
        "processing_runs",
        ["organization_id", "state", "available_at"],
    )

    op.create_table(
        "recording_quality_results",
        sa.Column("recording_quality_result_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("recording_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'usable'"), nullable=False),
        sa.Column("measured_duration_seconds", sa.Float(), nullable=True),
        sa.Column("measured_loudness_db", sa.Float(), nullable=True),
        sa.Column("measured_silence_ratio", sa.Float(), nullable=True),
        sa.Column("measured_decodability", sa.Float(), nullable=True),
        sa.Column("unavailable_checks_json", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("provenance", sa.String(length=256), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_recording_quality_results_organization",
        ),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recordings.recording_id"],
            name="fk_recording_quality_results_recording",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "recording_id"],
            ["recordings.organization_id", "recordings.recording_id"],
            name="fk_recording_quality_results_recording_tenant",
        ),
        sa.PrimaryKeyConstraint("recording_quality_result_id", name="pk_recording_quality_results"),
        sa.UniqueConstraint(
            "organization_id",
            "recording_id",
            name="uq_recording_quality_results_organization_recording",
        ),
        sa.CheckConstraint(
            "status IN ('usable', 'needs_additional_sample', 'unavailable', 'failed')",
            name="ck_recording_quality_results_status",
        ),
        sa.CheckConstraint(
            "measured_duration_seconds IS NULL OR measured_duration_seconds >= 0",
            name="ck_recording_quality_results_duration",
        ),
        sa.CheckConstraint(
            "measured_silence_ratio IS NULL OR measured_silence_ratio BETWEEN 0 AND 1",
            name="ck_recording_quality_results_silence_ratio",
        ),
        sa.CheckConstraint(
            "measured_decodability IS NULL OR measured_decodability BETWEEN 0 AND 1",
            name="ck_recording_quality_results_decodability",
        ),
        sa.CheckConstraint("length(provenance) > 0", name="ck_recording_quality_results_provenance"),
        sa.CheckConstraint("version >= 1", name="ck_recording_quality_results_version"),
    )
    op.create_index(
        "ix_recording_quality_results_organization_id",
        "recording_quality_results",
        ["organization_id"],
    )
    op.create_index(
        "ix_recording_quality_results_recording_id",
        "recording_quality_results",
        ["recording_id"],
    )
    op.create_index(
        "ix_recording_quality_results_organization_status",
        "recording_quality_results",
        ["organization_id", "status"],
    )

    protocol_versions = sa.table(
        "protocol_versions",
        sa.column("protocol_version_key", sa.String),
        sa.column("primary_language", sa.String),
        sa.column("minimum_age_months", sa.Integer),
        sa.column("maximum_age_months", sa.Integer),
        sa.column("supported_purposes", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    protocol_activities = sa.table(
        "protocol_activities",
        sa.column("protocol_version_key", sa.String),
        sa.column("activity_key", sa.String),
        sa.column("required", sa.Boolean),
        sa.column("target_duration_seconds", sa.Integer),
        sa.column("minimum_duration_seconds", sa.Integer),
        sa.column("sort_order", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        protocol_versions,
        [
            {
                "protocol_version_key": _PROTOCOL_VERSION_KEY,
                "primary_language": "th",
                "minimum_age_months": 18,
                "maximum_age_months": 72,
                "supported_purposes": _SUPPORTED_PURPOSES,
                "created_at": now,
            }
        ],
    )
    op.bulk_insert(
        protocol_activities,
        [
            {
                "protocol_version_key": _PROTOCOL_VERSION_KEY,
                "activity_key": "free_play",
                "required": True,
                "target_duration_seconds": 180,
                "minimum_duration_seconds": 120,
                "sort_order": 1,
                "created_at": now,
            },
            {
                "protocol_version_key": _PROTOCOL_VERSION_KEY,
                "activity_key": "shared_book",
                "required": False,
                "target_duration_seconds": 120,
                "minimum_duration_seconds": 60,
                "sort_order": 2,
                "created_at": now,
            },
            {
                "protocol_version_key": _PROTOCOL_VERSION_KEY,
                "activity_key": "turn_taking",
                "required": False,
                "target_duration_seconds": 120,
                "minimum_duration_seconds": 60,
                "sort_order": 3,
                "created_at": now,
            },
        ],
    )
    _install_catalog_immutability_guards()

    for table_name, policy_name in (
        (
            "assessment_protocol_selections",
            "assessment_protocol_selections_tenant_isolation",
        ),
        ("recordings", "recordings_tenant_isolation"),
        ("processing_runs", "processing_runs_tenant_isolation"),
        ("recording_quality_results", "recording_quality_results_tenant_isolation"),
    ):
        _enable_tenant_rls(table_name, policy_name)


def downgrade() -> None:
    _remove_catalog_immutability_guards()

    for table_name, policy_name in (
        ("recording_quality_results", "recording_quality_results_tenant_isolation"),
        ("processing_runs", "processing_runs_tenant_isolation"),
        ("recordings", "recordings_tenant_isolation"),
        (
            "assessment_protocol_selections",
            "assessment_protocol_selections_tenant_isolation",
        ),
    ):
        _disable_tenant_rls(table_name, policy_name)

    op.drop_index(
        "ix_recording_quality_results_organization_status",
        table_name="recording_quality_results",
    )
    op.drop_index("ix_recording_quality_results_recording_id", table_name="recording_quality_results")
    op.drop_index("ix_recording_quality_results_organization_id", table_name="recording_quality_results")
    op.drop_table("recording_quality_results")

    op.drop_index("ix_processing_runs_organization_state_available", table_name="processing_runs")
    op.drop_index("ix_processing_runs_organization_recording", table_name="processing_runs")
    op.drop_index("ix_processing_runs_recording_id", table_name="processing_runs")
    op.drop_index("ix_processing_runs_organization_id", table_name="processing_runs")
    op.drop_table("processing_runs")

    op.drop_index("ix_recordings_organization_upload_state_expiry", table_name="recordings")
    op.drop_index("ix_recordings_organization_assessment", table_name="recordings")
    op.drop_index("ix_recordings_upload_state", table_name="recordings")
    op.drop_index("ix_recordings_activity_key", table_name="recordings")
    op.drop_index("ix_recordings_assessment_id", table_name="recordings")
    op.drop_index("ix_recordings_organization_id", table_name="recordings")
    op.drop_table("recordings")

    op.drop_index(
        "ix_assessment_protocol_selections_selected_by_user_id",
        table_name="assessment_protocol_selections",
    )
    op.drop_index(
        "ix_assessment_protocol_selections_assessment_id",
        table_name="assessment_protocol_selections",
    )
    op.drop_index(
        "ix_assessment_protocol_selections_organization_id",
        table_name="assessment_protocol_selections",
    )
    op.drop_table("assessment_protocol_selections")

    op.drop_index("ix_protocol_activities_protocol_version_key", table_name="protocol_activities")
    op.drop_table("protocol_activities")
    op.drop_table("protocol_versions")

    with op.batch_alter_table("assessments") as batch:
        batch.drop_constraint("uq_assessments_organization_assessment", type_="unique")

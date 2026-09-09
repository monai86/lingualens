"""Add durable evidence-processing targets, leases, and recovery metadata."""

from alembic import op
import sqlalchemy as sa


revision = "0007_durable_evidence_jobs"
down_revision = "0006_evidence_profiles"
branch_labels = None
depends_on = None


_CAPTURE_STAGES = "'upload_verification', 'quality_analysis', 'cleanup'"
_PROCESSING_STATES = "'queued', 'running', 'succeeded', 'failed', 'cancelled'"
_TARGET_CHECK = (
    f"(stage IN ({_CAPTURE_STAGES}) AND recording_id IS NOT NULL "
    "AND assessment_id IS NULL AND transcript_revision_id IS NULL) OR "
    "(stage = 'evidence_extraction' AND recording_id IS NULL "
    "AND assessment_id IS NOT NULL AND transcript_revision_id IS NOT NULL)"
)


def _restore_processing_run_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE processing_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE processing_runs FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS processing_runs_tenant_isolation ON processing_runs")
    op.execute(
        "CREATE POLICY processing_runs_tenant_isolation ON processing_runs "
        "USING (organization_id = current_setting('app.current_organization_id', true)) "
        "WITH CHECK (organization_id = current_setting('app.current_organization_id', true))"
    )


def _upgrade_postgresql_constraints() -> None:
    """Alter PostgreSQL in place so forced RLS cannot hide rows during copy."""

    op.alter_column(
        "processing_runs",
        "recording_id",
        existing_type=sa.String(length=64),
        existing_nullable=False,
        nullable=True,
    )
    op.drop_constraint("ck_processing_runs_stage", table_name="processing_runs", type_="check")
    op.create_check_constraint(
        "ck_processing_runs_stage",
        "processing_runs",
        f"stage IN ({_CAPTURE_STAGES}, 'evidence_extraction')",
    )
    op.create_check_constraint("ck_processing_runs_max_attempts", "processing_runs", "max_attempts >= 1")
    op.create_check_constraint("ck_processing_runs_version", "processing_runs", "version >= 1")
    op.create_check_constraint("ck_processing_runs_target", "processing_runs", _TARGET_CHECK)
    op.create_foreign_key(
        "fk_processing_runs_assessment",
        "processing_runs",
        "assessments",
        ["assessment_id"],
        ["assessment_id"],
    )
    op.create_foreign_key(
        "fk_processing_runs_assessment_tenant",
        "processing_runs",
        "assessments",
        ["organization_id", "assessment_id"],
        ["organization_id", "assessment_id"],
    )
    op.create_foreign_key(
        "fk_processing_runs_transcript_revision",
        "processing_runs",
        "transcript_revisions",
        ["transcript_revision_id"],
        ["transcript_revision_id"],
    )
    op.create_foreign_key(
        "fk_processing_runs_transcript_tenant",
        "processing_runs",
        "transcript_revisions",
        ["organization_id", "transcript_revision_id"],
        ["organization_id", "transcript_revision_id"],
    )
    op.create_foreign_key(
        "fk_processing_runs_evidence_run",
        "processing_runs",
        "evidence_runs",
        ["evidence_run_id"],
        ["evidence_run_id"],
    )
    op.create_foreign_key(
        "fk_processing_runs_evidence_tenant",
        "processing_runs",
        "evidence_runs",
        ["organization_id", "evidence_run_id"],
        ["organization_id", "evidence_run_id"],
    )


def _downgrade_postgresql(bind) -> None:
    """Guard and downgrade without an RLS-blind Alembic batch copy."""

    # The migration role owns the table but is deliberately NOBYPASSRLS. Make
    # the guard and direct ALTER statements see all tenants, then restore the
    # forced policy before returning. A failed migration transaction rolls the
    # temporary RLS change back as well.
    op.execute("ALTER TABLE processing_runs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE processing_runs DISABLE ROW LEVEL SECURITY")
    try:
        has_evidence_jobs = bind.execute(
            sa.text(
                "SELECT EXISTS "
                "(SELECT 1 FROM processing_runs WHERE stage = 'evidence_extraction')"
            )
        ).scalar()
        if has_evidence_jobs:
            raise RuntimeError(
                "evidence_processing_downgrade_blocked: evidence jobs exist and "
                "must not be deleted."
            )

        op.drop_index(
            "ix_processing_runs_organization_stage_lease",
            table_name="processing_runs",
        )
        op.drop_index(
            "ix_processing_runs_organization_stage_state_available",
            table_name="processing_runs",
        )
        for constraint_name in (
            "ck_processing_runs_target",
            "ck_processing_runs_version",
            "ck_processing_runs_max_attempts",
            "fk_processing_runs_evidence_tenant",
            "fk_processing_runs_evidence_run",
            "fk_processing_runs_transcript_tenant",
            "fk_processing_runs_transcript_revision",
            "fk_processing_runs_assessment_tenant",
            "fk_processing_runs_assessment",
        ):
            constraint_type = "check" if constraint_name.startswith("ck_") else "foreignkey"
            op.drop_constraint(constraint_name, table_name="processing_runs", type_=constraint_type)
        for column_name in (
            "version",
            "feature_schema_version",
            "pipeline_version",
            "completed_at",
            "cancel_requested_at",
            "lease_expires_at",
            "lease_token",
            "max_attempts",
            "evidence_run_id",
            "transcript_revision_id",
            "assessment_id",
        ):
            op.drop_column("processing_runs", column_name)
        op.alter_column(
            "processing_runs",
            "recording_id",
            existing_type=sa.String(length=64),
            existing_nullable=True,
            nullable=False,
        )
        op.drop_constraint("ck_processing_runs_stage", table_name="processing_runs", type_="check")
        op.create_check_constraint(
            "ck_processing_runs_stage",
            "processing_runs",
            f"stage IN ({_CAPTURE_STAGES})",
        )
    finally:
        _restore_processing_run_rls()


def upgrade() -> None:
    op.add_column(
        "processing_runs",
        sa.Column("assessment_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column("transcript_revision_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column("evidence_run_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default=sa.text("3"),
            nullable=False,
        ),
    )
    op.add_column(
        "processing_runs",
        sa.Column("lease_token", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column("pipeline_version", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column("feature_schema_version", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )

    if op.get_bind().dialect.name == "postgresql":
        _upgrade_postgresql_constraints()
        op.create_index(
            "ix_processing_runs_organization_stage_state_available",
            "processing_runs",
            ["organization_id", "stage", "state", "available_at"],
        )
        op.create_index(
            "ix_processing_runs_organization_stage_lease",
            "processing_runs",
            ["organization_id", "stage", "state", "lease_expires_at"],
        )
        _restore_processing_run_rls()
        return

    with op.batch_alter_table("processing_runs", recreate="always") as batch:
        batch.alter_column(
            "recording_id",
            existing_type=sa.String(length=64),
            existing_nullable=False,
            nullable=True,
        )
        batch.drop_constraint("ck_processing_runs_stage", type_="check")
        batch.create_check_constraint(
            "ck_processing_runs_stage",
            f"stage IN ({_CAPTURE_STAGES}, 'evidence_extraction')",
        )
        batch.create_check_constraint(
            "ck_processing_runs_max_attempts",
            "max_attempts >= 1",
        )
        batch.create_check_constraint(
            "ck_processing_runs_version",
            "version >= 1",
        )
        batch.create_check_constraint("ck_processing_runs_target", _TARGET_CHECK)
        batch.create_foreign_key(
            "fk_processing_runs_assessment",
            "assessments",
            ["assessment_id"],
            ["assessment_id"],
        )
        batch.create_foreign_key(
            "fk_processing_runs_assessment_tenant",
            "assessments",
            ["organization_id", "assessment_id"],
            ["organization_id", "assessment_id"],
        )
        batch.create_foreign_key(
            "fk_processing_runs_transcript_revision",
            "transcript_revisions",
            ["transcript_revision_id"],
            ["transcript_revision_id"],
        )
        batch.create_foreign_key(
            "fk_processing_runs_transcript_tenant",
            "transcript_revisions",
            ["organization_id", "transcript_revision_id"],
            ["organization_id", "transcript_revision_id"],
        )
        batch.create_foreign_key(
            "fk_processing_runs_evidence_run",
            "evidence_runs",
            ["evidence_run_id"],
            ["evidence_run_id"],
        )
        batch.create_foreign_key(
            "fk_processing_runs_evidence_tenant",
            "evidence_runs",
            ["organization_id", "evidence_run_id"],
            ["organization_id", "evidence_run_id"],
        )

    op.create_index(
        "ix_processing_runs_organization_stage_state_available",
        "processing_runs",
        ["organization_id", "stage", "state", "available_at"],
    )
    op.create_index(
        "ix_processing_runs_organization_stage_lease",
        "processing_runs",
        ["organization_id", "stage", "state", "lease_expires_at"],
    )
    _restore_processing_run_rls()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _downgrade_postgresql(bind)
        return

    has_evidence_jobs = bind.execute(
        sa.text(
            "SELECT EXISTS "
            "(SELECT 1 FROM processing_runs WHERE stage = 'evidence_extraction')"
        )
    ).scalar()
    if has_evidence_jobs:
        raise RuntimeError(
            "evidence_processing_downgrade_blocked: evidence jobs exist and "
            "must not be deleted."
        )

    op.drop_index(
        "ix_processing_runs_organization_stage_lease",
        table_name="processing_runs",
    )
    op.drop_index(
        "ix_processing_runs_organization_stage_state_available",
        table_name="processing_runs",
    )

    with op.batch_alter_table("processing_runs", recreate="always") as batch:
        batch.drop_constraint("ck_processing_runs_target", type_="check")
        batch.drop_constraint("ck_processing_runs_version", type_="check")
        batch.drop_constraint("ck_processing_runs_max_attempts", type_="check")
        batch.drop_constraint("ck_processing_runs_stage", type_="check")
        batch.drop_constraint("ck_processing_runs_state", type_="check")
        batch.drop_constraint("fk_processing_runs_evidence_tenant", type_="foreignkey")
        batch.drop_constraint("fk_processing_runs_evidence_run", type_="foreignkey")
        batch.drop_constraint("fk_processing_runs_transcript_tenant", type_="foreignkey")
        batch.drop_constraint("fk_processing_runs_transcript_revision", type_="foreignkey")
        batch.drop_constraint("fk_processing_runs_assessment_tenant", type_="foreignkey")
        batch.drop_constraint("fk_processing_runs_assessment", type_="foreignkey")
        batch.drop_column("version")
        batch.drop_column("feature_schema_version")
        batch.drop_column("pipeline_version")
        batch.drop_column("completed_at")
        batch.drop_column("cancel_requested_at")
        batch.drop_column("lease_expires_at")
        batch.drop_column("lease_token")
        batch.drop_column("max_attempts")
        batch.drop_column("evidence_run_id")
        batch.drop_column("transcript_revision_id")
        batch.drop_column("assessment_id")
        batch.alter_column(
            "recording_id",
            existing_type=sa.String(length=64),
            existing_nullable=True,
            nullable=False,
        )
        batch.create_check_constraint(
            "ck_processing_runs_stage",
            f"stage IN ({_CAPTURE_STAGES})",
        )
        batch.create_check_constraint(
            "ck_processing_runs_state",
            f"state IN ({_PROCESSING_STATES})",
        )
    _restore_processing_run_rls()

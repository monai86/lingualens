"""Persist versioned measured features and descriptive domain profiles."""

from alembic import op
import sqlalchemy as sa


revision = "0006_evidence_profiles"
down_revision = "0005_transcript_revisions"
branch_labels = None
depends_on = None


_EVIDENCE_STATES = (
    "'pending', 'processing', 'completed', 'needs_review', 'insufficient_data', "
    "'unavailable', 'failed', 'stale'"
)
_EVIDENCE_SOURCES = "'reviewed_transcript', 'audio_quality', 'observation', 'instrument'"
_DOMAINS = (
    "'expressive_language', 'speech_clarity_production', 'conversational_interaction', "
    "'social_communication', 'repetitive_language', 'prosody_temporal_organization', "
    "'evidence_quality_sufficiency'"
)
_DOMAIN_STATUSES = (
    "'descriptive_only', 'within_reference_band', 'outside_reference_band', "
    "'attention_suggested', 'insufficient_data', 'reference_unavailable', 'not_assessed'"
)


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


def upgrade() -> None:
    op.create_table(
        "evidence_runs",
        sa.Column("evidence_run_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("transcript_revision_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("input_ref", sa.String(length=256), nullable=False),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.Column("protocol_version_key", sa.String(length=128), nullable=False),
        sa.Column("extractor", sa.String(length=128), nullable=False),
        sa.Column("pipeline_version", sa.String(length=128), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=128), nullable=False),
        sa.Column(
            "limitations_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_evidence_runs_organization",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_evidence_runs_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["transcript_revision_id"],
            ["transcript_revisions.transcript_revision_id"],
            name="fk_evidence_runs_transcript_revision",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_evidence_runs_assessment_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "transcript_revision_id"],
            [
                "transcript_revisions.organization_id",
                "transcript_revisions.transcript_revision_id",
            ],
            name="fk_evidence_runs_transcript_tenant",
        ),
        sa.PrimaryKeyConstraint("evidence_run_id", name="pk_evidence_runs"),
        sa.UniqueConstraint(
            "organization_id",
            "evidence_run_id",
            name="uq_evidence_runs_organization_run",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "assessment_id",
            "transcript_revision_id",
            "pipeline_version",
            "feature_schema_version",
            name="uq_evidence_runs_identity",
        ),
        sa.CheckConstraint(
            f"state IN ({_EVIDENCE_STATES})",
            name="ck_evidence_runs_state",
        ),
        sa.CheckConstraint("length(input_ref) > 0", name="ck_evidence_runs_input_ref"),
        sa.CheckConstraint(
            "length(input_sha256) = 64",
            name="ck_evidence_runs_input_sha256",
        ),
        sa.CheckConstraint(
            "length(protocol_version_key) > 0",
            name="ck_evidence_runs_protocol",
        ),
        sa.CheckConstraint("length(extractor) > 0", name="ck_evidence_runs_extractor"),
        sa.CheckConstraint(
            "length(pipeline_version) > 0",
            name="ck_evidence_runs_pipeline",
        ),
        sa.CheckConstraint(
            "length(feature_schema_version) > 0",
            name="ck_evidence_runs_schema",
        ),
        sa.CheckConstraint("version >= 1", name="ck_evidence_runs_version"),
    )
    op.create_index(
        "ix_evidence_runs_organization_id",
        "evidence_runs",
        ["organization_id"],
    )
    op.create_index(
        "ix_evidence_runs_assessment_id",
        "evidence_runs",
        ["assessment_id"],
    )
    op.create_index(
        "ix_evidence_runs_transcript_revision_id",
        "evidence_runs",
        ["transcript_revision_id"],
    )
    op.create_index("ix_evidence_runs_state", "evidence_runs", ["state"])
    op.create_index(
        "ix_evidence_runs_organization_assessment_created",
        "evidence_runs",
        ["organization_id", "assessment_id", "created_at"],
    )

    op.create_table(
        "evidence_feature_values",
        sa.Column("evidence_feature_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_run_id", sa.String(length=64), nullable=False),
        sa.Column("feature_key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("limitation", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_evidence_features_organization",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_run_id"],
            ["evidence_runs.evidence_run_id"],
            name="fk_evidence_features_run",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "evidence_run_id"],
            ["evidence_runs.organization_id", "evidence_runs.evidence_run_id"],
            name="fk_evidence_features_run_tenant",
        ),
        sa.PrimaryKeyConstraint("evidence_feature_id", name="pk_evidence_feature_values"),
        sa.UniqueConstraint(
            "organization_id",
            "evidence_feature_id",
            name="uq_evidence_features_organization_feature",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "evidence_run_id",
            "feature_key",
            name="uq_evidence_features_run_key",
        ),
        sa.CheckConstraint(
            f"source IN ({_EVIDENCE_SOURCES})",
            name="ck_evidence_features_source",
        ),
        sa.CheckConstraint(
            f"state IN ({_EVIDENCE_STATES})",
            name="ck_evidence_features_state",
        ),
        sa.CheckConstraint(
            "(state = 'completed' AND value_json IS NOT NULL) OR "
            "(state <> 'completed' AND value_json IS NULL AND length(limitation) > 0)",
            name="ck_evidence_features_value_state",
        ),
        sa.CheckConstraint("length(feature_key) > 0", name="ck_evidence_features_key"),
        sa.CheckConstraint("length(unit) > 0", name="ck_evidence_features_unit"),
        sa.CheckConstraint("version >= 1", name="ck_evidence_features_version"),
    )
    op.create_index(
        "ix_evidence_features_organization_id",
        "evidence_feature_values",
        ["organization_id"],
    )
    op.create_index(
        "ix_evidence_features_evidence_run_id",
        "evidence_feature_values",
        ["evidence_run_id"],
    )
    op.create_index(
        "ix_evidence_features_organization_run",
        "evidence_feature_values",
        ["organization_id", "evidence_run_id"],
    )

    op.create_table(
        "evidence_domain_profiles",
        sa.Column("domain_profile_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_run_id", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "feature_keys_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "supporting_features_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "conflicting_features_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "limitations_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_evidence_domains_organization",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_run_id"],
            ["evidence_runs.evidence_run_id"],
            name="fk_evidence_domains_run",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "evidence_run_id"],
            ["evidence_runs.organization_id", "evidence_runs.evidence_run_id"],
            name="fk_evidence_domains_run_tenant",
        ),
        sa.PrimaryKeyConstraint("domain_profile_id", name="pk_evidence_domain_profiles"),
        sa.UniqueConstraint(
            "organization_id",
            "domain_profile_id",
            name="uq_evidence_domains_organization_profile",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "evidence_run_id",
            "domain",
            name="uq_evidence_domains_run_domain",
        ),
        sa.CheckConstraint(
            f"domain IN ({_DOMAINS})",
            name="ck_evidence_domains_domain",
        ),
        sa.CheckConstraint(
            f"status IN ({_DOMAIN_STATUSES})",
            name="ck_evidence_domains_status",
        ),
        sa.CheckConstraint("length(summary) > 0", name="ck_evidence_domains_summary"),
        sa.CheckConstraint("version >= 1", name="ck_evidence_domains_version"),
    )
    op.create_index(
        "ix_evidence_domains_organization_id",
        "evidence_domain_profiles",
        ["organization_id"],
    )
    op.create_index(
        "ix_evidence_domains_evidence_run_id",
        "evidence_domain_profiles",
        ["evidence_run_id"],
    )
    op.create_index(
        "ix_evidence_domains_organization_run",
        "evidence_domain_profiles",
        ["organization_id", "evidence_run_id"],
    )

    _enable_tenant_rls("evidence_runs", "evidence_runs_organization_isolation")
    _enable_tenant_rls(
        "evidence_feature_values",
        "evidence_features_organization_isolation",
    )
    _enable_tenant_rls(
        "evidence_domain_profiles",
        "evidence_domains_organization_isolation",
    )


def downgrade() -> None:
    _disable_tenant_rls(
        "evidence_domain_profiles",
        "evidence_domains_organization_isolation",
    )
    _disable_tenant_rls(
        "evidence_feature_values",
        "evidence_features_organization_isolation",
    )
    _disable_tenant_rls("evidence_runs", "evidence_runs_organization_isolation")

    op.drop_index(
        "ix_evidence_domains_organization_run",
        table_name="evidence_domain_profiles",
    )
    op.drop_index(
        "ix_evidence_domains_evidence_run_id",
        table_name="evidence_domain_profiles",
    )
    op.drop_index(
        "ix_evidence_domains_organization_id",
        table_name="evidence_domain_profiles",
    )
    op.drop_table("evidence_domain_profiles")

    op.drop_index(
        "ix_evidence_features_organization_run",
        table_name="evidence_feature_values",
    )
    op.drop_index(
        "ix_evidence_features_evidence_run_id",
        table_name="evidence_feature_values",
    )
    op.drop_index(
        "ix_evidence_features_organization_id",
        table_name="evidence_feature_values",
    )
    op.drop_table("evidence_feature_values")

    op.drop_index(
        "ix_evidence_runs_organization_assessment_created",
        table_name="evidence_runs",
    )
    op.drop_index("ix_evidence_runs_state", table_name="evidence_runs")
    op.drop_index(
        "ix_evidence_runs_transcript_revision_id",
        table_name="evidence_runs",
    )
    op.drop_index("ix_evidence_runs_assessment_id", table_name="evidence_runs")
    op.drop_index("ix_evidence_runs_organization_id", table_name="evidence_runs")
    op.drop_table("evidence_runs")

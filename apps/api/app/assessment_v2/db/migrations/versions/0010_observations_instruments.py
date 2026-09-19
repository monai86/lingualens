"""Add structured observations and instrument administrations with tenant RLS.

Revision ID: 0010_observations_instruments
Revises: 0009_segment_evidence_provenance
Create Date: 2026-09-12 00:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_observations_instruments"
down_revision = "0009_segment_evidence_provenance"
branch_labels = None
depends_on = None

_OBSERVATION_CATEGORIES = (
    "'communication', 'social_engagement', 'play_behavior', 'sensory_motor', 'emotional_regulation'"
)
_OBSERVATION_SOURCES = "'clinician', 'caregiver', 'educator'"
_INSTRUMENT_RESPONDENTS = "'caregiver', 'clinician', 'teacher'"


def _enable_tenant_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table_name in (
        "assessment_observations",
        "assessment_instruments",
        "assessment_instrument_items",
    ):
        policy_name = f"{table_name}_organization_isolation"
        op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"CREATE POLICY {policy_name} ON {table_name} "
                "USING (organization_id = current_setting('app.current_organization_id', true)) "
                "WITH CHECK (organization_id = current_setting('app.current_organization_id', true))"
            )
        )


def _disable_tenant_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table_name in (
        "assessment_instrument_items",
        "assessment_instruments",
        "assessment_observations",
    ):
        op.execute(sa.text(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS assessment_instrument_items_organization_isolation "
            "ON assessment_instrument_items"
        )
    )
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS assessment_instruments_organization_isolation "
            "ON assessment_instruments"
        )
    )
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS assessment_observations_organization_isolation "
            "ON assessment_observations"
        )
    )


def upgrade() -> None:
    op.create_table(
        "assessment_observations",
        sa.Column("observation_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("observer_name", sa.String(length=256), nullable=False),
        sa.Column("observer_role", sa.String(length=128), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activity_context", sa.String(length=512), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("structured_flags_json", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("is_amendment", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("amends_observation_id", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("observation_id"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_observations_organization",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_observations_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_observations_assessment_tenant",
        ),
        sa.UniqueConstraint("organization_id", "observation_id", name="uq_observations_organization_observation"),
        sa.CheckConstraint(f"category IN ({_OBSERVATION_CATEGORIES})", name="ck_observations_category"),
        sa.CheckConstraint(f"source IN ({_OBSERVATION_SOURCES})", name="ck_observations_source"),
        sa.CheckConstraint("length(notes) > 0", name="ck_observations_notes_non_empty"),
        sa.CheckConstraint("version >= 1", name="ck_observations_version"),
        sa.CheckConstraint(
            "(NOT is_amendment AND amends_observation_id IS NULL AND version = 1) OR "
            "(is_amendment AND amends_observation_id IS NOT NULL AND version >= 2)",
            name="ck_observations_amendment_integrity",
        ),
    )
    op.create_index(
        "ix_observations_organization_assessment_created",
        "assessment_observations",
        ["organization_id", "assessment_id", "created_at"],
    )

    op.create_table(
        "assessment_instruments",
        sa.Column("administration_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("instrument_name", sa.String(length=128), nullable=False),
        sa.Column("instrument_version", sa.String(length=64), nullable=False),
        sa.Column("respondent_type", sa.String(length=32), nullable=False),
        sa.Column("administered_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("administered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("licensing_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("summary_scores_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("administration_id"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_instruments_organization",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_instruments_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_instruments_assessment_tenant",
        ),
        sa.UniqueConstraint("organization_id", "administration_id", name="uq_instruments_organization_administration"),
        sa.CheckConstraint(f"respondent_type IN ({_INSTRUMENT_RESPONDENTS})", name="ck_instruments_respondent_type"),
        sa.CheckConstraint("length(instrument_name) > 0", name="ck_instruments_name_non_empty"),
        sa.CheckConstraint("length(instrument_version) > 0", name="ck_instruments_version_non_empty"),
        sa.CheckConstraint("version >= 1", name="ck_instruments_version"),
    )
    op.create_index(
        "ix_instruments_organization_assessment_administered",
        "assessment_instruments",
        ["organization_id", "assessment_id", "administered_at"],
    )

    op.create_table(
        "assessment_instrument_items",
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("administration_id", sa.String(length=64), nullable=False),
        sa.Column("item_key", sa.String(length=64), nullable=False),
        sa.Column("prompt_label", sa.String(length=512), nullable=False),
        sa.Column("response_value", sa.String(length=512), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("item_id"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_instrument_items_organization",
        ),
        sa.ForeignKeyConstraint(
            ["administration_id"],
            ["assessment_instruments.administration_id"],
            name="fk_instrument_items_administration",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "administration_id"],
            ["assessment_instruments.organization_id", "assessment_instruments.administration_id"],
            name="fk_instrument_items_administration_tenant",
        ),
        sa.UniqueConstraint("organization_id", "item_id", name="uq_instrument_items_organization_item"),
        sa.UniqueConstraint("organization_id", "administration_id", "item_key", name="uq_instrument_items_admin_item_key"),
        sa.CheckConstraint("length(item_key) > 0", name="ck_instrument_items_key_non_empty"),
        sa.CheckConstraint("length(prompt_label) > 0", name="ck_instrument_items_label_non_empty"),
    )
    op.create_index(
        "ix_instrument_items_organization_admin",
        "assessment_instrument_items",
        ["organization_id", "administration_id"],
    )

    _enable_tenant_rls()


def downgrade() -> None:
    bind = op.get_bind()
    _disable_tenant_rls()

    # Guard against dropping populated tables
    for table_name in ("assessment_instrument_items", "assessment_instruments", "assessment_observations"):
        count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        if count:
            raise RuntimeError(f"Cannot downgrade migration 0010: {table_name} contains {count} records")

    op.drop_table("assessment_instrument_items")
    op.drop_table("assessment_instruments")
    op.drop_table("assessment_observations")

"""Create the assessment v2 reviewed-transcript revision boundary."""

from alembic import op
import sqlalchemy as sa


revision = "0005_transcript_revisions"
down_revision = "0004_capture_cleanup_stage"
branch_labels = None
depends_on = None


def _enable_tenant_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(sa.text("ALTER TABLE transcript_revisions ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE transcript_revisions FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            "CREATE POLICY transcript_revisions_organization_isolation "
            "ON transcript_revisions "
            "USING (organization_id = current_setting('app.current_organization_id', true)) "
            "WITH CHECK (organization_id = current_setting('app.current_organization_id', true))"
        )
    )


def _disable_tenant_rls() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            sa.text(
                "DROP POLICY IF EXISTS transcript_revisions_organization_isolation "
                "ON transcript_revisions"
            )
        )


def upgrade() -> None:
    op.create_table(
        "transcript_revisions",
        sa.Column("transcript_revision_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("review_state", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("attested_by_user_id", sa.String(length=128), nullable=True),
        sa.Column("attested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_transcript_revisions_organization",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_transcript_revisions_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_transcript_revisions_assessment_tenant",
        ),
        sa.PrimaryKeyConstraint("transcript_revision_id", name="pk_transcript_revisions"),
        sa.UniqueConstraint(
            "organization_id",
            "transcript_revision_id",
            name="uq_transcript_revisions_organization_revision_id",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "assessment_id",
            "revision",
            name="uq_transcript_revisions_organization_assessment_revision",
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'asr_draft', 'imported')",
            name="ck_transcript_revisions_source",
        ),
        sa.CheckConstraint(
            "review_state IN ('draft', 'attested', 'superseded')",
            name="ck_transcript_revisions_review_state",
        ),
        sa.CheckConstraint("length(content) > 0", name="ck_transcript_revisions_content"),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_transcript_revisions_content_sha256",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_transcript_revisions_revision"),
        sa.CheckConstraint("version >= 1", name="ck_transcript_revisions_version"),
    )
    op.create_index(
        "ix_transcript_revisions_organization_id",
        "transcript_revisions",
        ["organization_id"],
    )
    op.create_index(
        "ix_transcript_revisions_assessment_id",
        "transcript_revisions",
        ["assessment_id"],
    )
    op.create_index(
        "ix_transcript_revisions_organization_assessment_revision",
        "transcript_revisions",
        ["organization_id", "assessment_id", "revision"],
    )
    _enable_tenant_rls()


def downgrade() -> None:
    _disable_tenant_rls()
    op.drop_index(
        "ix_transcript_revisions_organization_assessment_revision",
        table_name="transcript_revisions",
    )
    op.drop_index("ix_transcript_revisions_assessment_id", table_name="transcript_revisions")
    op.drop_index("ix_transcript_revisions_organization_id", table_name="transcript_revisions")
    op.drop_table("transcript_revisions")

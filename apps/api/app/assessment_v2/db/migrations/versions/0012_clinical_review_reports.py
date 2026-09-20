"""Add clinical review, attention cues, and reports with tenant RLS.

Revision ID: 0012_clinical_review_reports
Revises: 0011_longitudinal_comparisons
Create Date: 2026-09-12 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_clinical_review_reports"
down_revision = "0011_longitudinal_comparisons"
branch_labels = None
depends_on = None


def _enable_tenant_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table_name in (
        "assessment_clinical_reviews",
        "assessment_attention_cues",
        "assessment_reports",
    ):
        op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
        op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {table_name}_organization_isolation
                ON {table_name}
                FOR ALL
                USING (
                    organization_id = current_setting('app.current_organization_id', true)
                )
                WITH CHECK (
                    organization_id = current_setting('app.current_organization_id', true)
                );
                """
            )
        )


def _disable_tenant_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table_name in (
        "assessment_reports",
        "assessment_attention_cues",
        "assessment_clinical_reviews",
    ):
        op.execute(sa.text(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY;"))
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;"))
        op.execute(
            sa.text(
                f"DROP POLICY IF EXISTS {table_name}_organization_isolation "
                f"ON {table_name};"
            )
        )


def upgrade() -> None:
    op.create_table(
        "assessment_clinical_reviews",
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("child_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_run_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="in_progress", nullable=False),
        sa.Column("disposition", sa.String(length=64), nullable=True),
        sa.Column("disposition_notes", sa.Text(), nullable=True),
        sa.Column("follow_up_plan_json", sa.JSON(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=128), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_clinical_reviews_organization",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_clinical_reviews_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.child_id"],
            name="fk_clinical_reviews_child",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_run_id"],
            ["evidence_runs.evidence_run_id"],
            name="fk_clinical_reviews_evidence_run",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_clinical_reviews_assessment_tenant",
        ),
        sa.PrimaryKeyConstraint("review_id"),
        sa.UniqueConstraint("organization_id", "review_id", name="uq_clinical_reviews_org_id"),
        sa.UniqueConstraint("organization_id", "assessment_id", name="uq_clinical_reviews_org_assessment"),
    )
    op.create_index("ix_clinical_reviews_org_assessment", "assessment_clinical_reviews", ["organization_id", "assessment_id"])

    op.create_table(
        "assessment_attention_cues",
        sa.Column("cue_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("cue_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.String(length=64), server_default="cues-v2.0", nullable=False),
        sa.Column("evidence_run_id", sa.String(length=64), nullable=False),
        sa.Column("supporting_feature_keys_json", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("conflicting_feature_keys_json", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("limitations_json", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending_review", nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_attention_cues_organization",
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["assessment_clinical_reviews.review_id"],
            name="fk_attention_cues_review",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_attention_cues_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_run_id"],
            ["evidence_runs.evidence_run_id"],
            name="fk_attention_cues_evidence_run",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "review_id"],
            ["assessment_clinical_reviews.organization_id", "assessment_clinical_reviews.review_id"],
            name="fk_attention_cues_review_tenant",
        ),
        sa.PrimaryKeyConstraint("cue_id"),
        sa.UniqueConstraint("organization_id", "cue_id", name="uq_attention_cues_org_id"),
    )
    op.create_index("ix_attention_cues_org_review", "assessment_attention_cues", ["organization_id", "review_id"])
    op.create_index("ix_attention_cues_org_assessment", "assessment_attention_cues", ["organization_id", "assessment_id"])

    op.create_table(
        "assessment_reports",
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("child_id", sa.String(length=64), nullable=False),
        sa.Column("evidence_run_id", sa.String(length=64), nullable=False),
        sa.Column("comparison_id", sa.String(length=64), nullable=True),
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("amends_report_id", sa.String(length=64), nullable=True),
        sa.Column("amendment_sequence", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("limitations_json", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("signed_by", sa.String(length=128), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_snapshot", sa.JSON(), nullable=True),
        sa.Column("signed_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_reports_organization",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_reports_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.child_id"],
            name="fk_reports_child",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_run_id"],
            ["evidence_runs.evidence_run_id"],
            name="fk_reports_evidence_run",
        ),
        sa.ForeignKeyConstraint(
            ["comparison_id"],
            ["assessment_comparisons.comparison_id"],
            name="fk_reports_comparison",
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["assessment_clinical_reviews.review_id"],
            name="fk_reports_review",
        ),
        sa.ForeignKeyConstraint(
            ["amends_report_id"],
            ["assessment_reports.report_id"],
            name="fk_reports_amends_report",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_reports_assessment_tenant",
        ),
        sa.PrimaryKeyConstraint("report_id"),
        sa.UniqueConstraint("organization_id", "report_id", name="uq_reports_org_id"),
    )
    op.create_index("ix_reports_org_assessment", "assessment_reports", ["organization_id", "assessment_id"])
    op.create_index("ix_reports_org_status", "assessment_reports", ["organization_id", "status"])
    op.create_index("ix_reports_snapshot_hash", "assessment_reports", ["signed_snapshot_hash"])

    _enable_tenant_rls()


def downgrade() -> None:
    _disable_tenant_rls()
    op.drop_index("ix_reports_snapshot_hash", table_name="assessment_reports")
    op.drop_index("ix_reports_org_status", table_name="assessment_reports")
    op.drop_index("ix_reports_org_assessment", table_name="assessment_reports")
    op.drop_table("assessment_reports")

    op.drop_index("ix_attention_cues_org_assessment", table_name="assessment_attention_cues")
    op.drop_index("ix_attention_cues_org_review", table_name="assessment_attention_cues")
    op.drop_table("assessment_attention_cues")

    op.drop_index("ix_clinical_reviews_org_assessment", table_name="assessment_clinical_reviews")
    op.drop_table("assessment_clinical_reviews")

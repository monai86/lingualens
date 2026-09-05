"""Create the fresh assessment v2 foundation schema."""

from alembic import op
import sqlalchemy as sa


revision = "0001_assessment_foundation"
down_revision = None
branch_labels = None
depends_on = None


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
        "organizations",
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("display_label", sa.String(length=256), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("organization_id", name="pk_organizations"),
    )
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("display_label", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_profiles"),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("membership_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_membership_organization"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.user_id"], name="fk_membership_user"),
        sa.PrimaryKeyConstraint("membership_id", name="pk_organization_memberships"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership_organization_user"),
        sa.CheckConstraint(
            "role IN ('therapist', 'clinical_supervisor', 'org_admin', 'researcher')",
            name="ck_membership_role",
        ),
    )
    op.create_index("ix_membership_organization_id", "organization_memberships", ["organization_id"])
    op.create_index("ix_membership_user_id", "organization_memberships", ["user_id"])
    op.create_table(
        "children",
        sa.Column("child_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("display_code", sa.String(length=128), nullable=False),
        sa.Column("birth_month", sa.Integer(), nullable=False),
        sa.Column("birth_year", sa.Integer(), nullable=False),
        sa.Column("language_context", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_children_organization"),
        sa.PrimaryKeyConstraint("child_id", name="pk_children"),
        sa.UniqueConstraint("organization_id", "display_code", name="uq_child_organization_display_code"),
        sa.CheckConstraint("birth_month BETWEEN 1 AND 12", name="ck_children_birth_month"),
        sa.CheckConstraint("birth_year BETWEEN 1900 AND 2100", name="ck_children_birth_year"),
        sa.CheckConstraint("version >= 1", name="ck_children_version"),
    )
    op.create_index("ix_children_organization_id", "children", ["organization_id"])
    op.create_table(
        "care_team_assignments",
        sa.Column("assignment_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("child_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_care_team_organization"),
        sa.ForeignKeyConstraint(["child_id"], ["children.child_id"], name="fk_care_team_child"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.user_id"], name="fk_care_team_user"),
        sa.PrimaryKeyConstraint("assignment_id", name="pk_care_team_assignments"),
        sa.UniqueConstraint("organization_id", "child_id", "user_id", name="uq_care_team_organization_child_user"),
        sa.CheckConstraint(
            "role IN ('assigned_clinician', 'supervisor', 'observer')",
            name="ck_care_team_role",
        ),
    )
    op.create_index("ix_care_team_organization_id", "care_team_assignments", ["organization_id"])
    op.create_index("ix_care_team_child_id", "care_team_assignments", ["child_id"])
    op.create_index("ix_care_team_user_id", "care_team_assignments", ["user_id"])
    op.create_table(
        "consent_records",
        sa.Column("consent_record_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("child_id", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("scope_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_consent_organization"),
        sa.ForeignKeyConstraint(["child_id"], ["children.child_id"], name="fk_consent_child"),
        sa.PrimaryKeyConstraint("consent_record_id", name="pk_consent_records"),
        sa.CheckConstraint(
            "purpose IN ('clinical_assessment', 'research_reuse')",
            name="ck_consent_records_purpose",
        ),
        sa.CheckConstraint("status IN ('active', 'withdrawn')", name="ck_consent_records_status"),
        sa.CheckConstraint("version >= 1", name="ck_consent_records_version"),
    )
    op.create_index("ix_consent_organization_id", "consent_records", ["organization_id"])
    op.create_index("ix_consent_child_id", "consent_records", ["child_id"])
    op.create_table(
        "assessments",
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("child_id", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("age_months", sa.Integer(), nullable=False),
        sa.Column("language_context", sa.String(length=128), nullable=False),
        sa.Column("assigned_clinician_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_assessments_organization"),
        sa.ForeignKeyConstraint(["child_id"], ["children.child_id"], name="fk_assessments_child"),
        sa.ForeignKeyConstraint(["assigned_clinician_id"], ["user_profiles.user_id"], name="fk_assessments_clinician"),
        sa.PrimaryKeyConstraint("assessment_id", name="pk_assessments"),
        sa.CheckConstraint(
            "purpose IN ('initial', 'developmental_follow_up', 'post_intervention_follow_up', 'additional_evidence')",
            name="ck_assessments_purpose",
        ),
        sa.CheckConstraint(
            "state IN ('draft', 'ready_for_capture', 'capturing', 'processing', 'review_required', 'ready_for_clinician', 'finalized', 'cancelled')",
            name="ck_assessments_state",
        ),
        sa.CheckConstraint("age_months BETWEEN 0 AND 216", name="ck_assessments_age_months"),
        sa.CheckConstraint("version >= 1", name="ck_assessments_version"),
    )
    op.create_index("ix_assessments_organization_id", "assessments", ["organization_id"])
    op.create_index("ix_assessments_child_id", "assessments", ["child_id"])
    op.create_index("ix_assessments_assigned_clinician_id", "assessments", ["assigned_clinician_id"])
    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("target_version", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_audit_events_organization"),
        sa.PrimaryKeyConstraint("audit_event_id", name="pk_audit_events"),
    )
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])

    for table_name, policy_name in (
        ("organization_memberships", "organization_memberships_tenant_isolation"),
        ("children", "children_tenant_isolation"),
        ("care_team_assignments", "care_team_assignments_tenant_isolation"),
        ("consent_records", "consent_records_tenant_isolation"),
        ("assessments", "assessments_tenant_isolation"),
        ("audit_events", "audit_events_tenant_isolation"),
    ):
        _enable_tenant_rls(table_name, policy_name)


def downgrade() -> None:
    for table_name, policy_name in (
        ("audit_events", "audit_events_tenant_isolation"),
        ("assessments", "assessments_tenant_isolation"),
        ("consent_records", "consent_records_tenant_isolation"),
        ("care_team_assignments", "care_team_assignments_tenant_isolation"),
        ("children", "children_tenant_isolation"),
        ("organization_memberships", "organization_memberships_tenant_isolation"),
    ):
        _disable_tenant_rls(table_name, policy_name)

    op.drop_index("ix_audit_events_correlation_id", table_name="audit_events")
    op.drop_index("ix_audit_events_organization_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_assessments_assigned_clinician_id", table_name="assessments")
    op.drop_index("ix_assessments_child_id", table_name="assessments")
    op.drop_index("ix_assessments_organization_id", table_name="assessments")
    op.drop_table("assessments")
    op.drop_index("ix_consent_child_id", table_name="consent_records")
    op.drop_index("ix_consent_organization_id", table_name="consent_records")
    op.drop_table("consent_records")
    op.drop_index("ix_care_team_user_id", table_name="care_team_assignments")
    op.drop_index("ix_care_team_child_id", table_name="care_team_assignments")
    op.drop_index("ix_care_team_organization_id", table_name="care_team_assignments")
    op.drop_table("care_team_assignments")
    op.drop_index("ix_children_organization_id", table_name="children")
    op.drop_table("children")
    op.drop_index("ix_membership_user_id", table_name="organization_memberships")
    op.drop_index("ix_membership_organization_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_table("user_profiles")
    op.drop_table("organizations")

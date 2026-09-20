"""Harden tenant identity across child-linked assessment records."""

from alembic import op


revision = "0002_assessment_tenant_integrity"
down_revision = "0001_assessment_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("children") as batch:
        batch.create_unique_constraint(
            "uq_children_organization_child",
            ["organization_id", "child_id"],
        )

    with op.batch_alter_table("care_team_assignments") as batch:
        batch.create_foreign_key(
            "fk_care_team_child_tenant",
            "children",
            ["organization_id", "child_id"],
            ["organization_id", "child_id"],
        )
        batch.create_foreign_key(
            "fk_care_team_membership_tenant",
            "organization_memberships",
            ["organization_id", "user_id"],
            ["organization_id", "user_id"],
        )

    with op.batch_alter_table("consent_records") as batch:
        batch.create_unique_constraint(
            "uq_consent_organization_child_purpose_version",
            ["organization_id", "child_id", "purpose", "version"],
        )
        batch.create_foreign_key(
            "fk_consent_child_tenant",
            "children",
            ["organization_id", "child_id"],
            ["organization_id", "child_id"],
        )

    with op.batch_alter_table("assessments") as batch:
        batch.create_foreign_key(
            "fk_assessments_child_tenant",
            "children",
            ["organization_id", "child_id"],
            ["organization_id", "child_id"],
        )
        batch.create_foreign_key(
            "fk_assessments_clinician_membership_tenant",
            "organization_memberships",
            ["organization_id", "assigned_clinician_id"],
            ["organization_id", "user_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("assessments") as batch:
        batch.drop_constraint("fk_assessments_clinician_membership_tenant", type_="foreignkey")
        batch.drop_constraint("fk_assessments_child_tenant", type_="foreignkey")

    with op.batch_alter_table("consent_records") as batch:
        batch.drop_constraint(
            "uq_consent_organization_child_purpose_version", type_="unique"
        )
        batch.drop_constraint("fk_consent_child_tenant", type_="foreignkey")

    with op.batch_alter_table("care_team_assignments") as batch:
        batch.drop_constraint("fk_care_team_membership_tenant", type_="foreignkey")
        batch.drop_constraint("fk_care_team_child_tenant", type_="foreignkey")

    with op.batch_alter_table("children") as batch:
        batch.drop_constraint("uq_children_organization_child", type_="unique")

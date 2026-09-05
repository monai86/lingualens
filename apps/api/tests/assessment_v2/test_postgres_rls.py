from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from app.assessment_v2.db.migrations_runner import upgrade_assessment_database
from app.assessment_v2.db.repositories import AssessmentRepository
from app.assessment_v2.db.session import assessment_session_for, get_assessment_engine
from app.assessment_v2.domain.models import AccessScope
from app.core.security import CurrentUser


pytestmark = pytest.mark.assessment_postgres
_ROLE = "lingualens_assessment_rls_test"
_ROLE_PASSWORD = "assessment-rls-test-only"


def _test_url() -> str:
    value = os.getenv("LINGUALENS_ASSESSMENT_TEST_DATABASE_URL")
    if not value:
        pytest.skip("LINGUALENS_ASSESSMENT_TEST_DATABASE_URL is not configured")
    return value


def _limited_url(owner_url: URL) -> str:
    return owner_url.set(username=_ROLE, password=_ROLE_PASSWORD).render_as_string(hide_password=False)


@pytest.fixture(scope="module")
def rls_database() -> Iterator[tuple[str, str, str, str]]:
    owner_url = make_url(_test_url())
    if owner_url.get_backend_name() != "postgresql":
        pytest.skip("assessment PostgreSQL RLS tests require a PostgreSQL URL")

    previous_database_url = os.environ.get("LINGUALENS_ASSESSMENT_DATABASE_URL")
    os.environ["LINGUALENS_ASSESSMENT_DATABASE_URL"] = owner_url.render_as_string(hide_password=False)
    from app.core.config import get_settings
    from app.assessment_v2.db.session import get_assessment_session_factory

    get_settings.cache_clear()
    upgrade_assessment_database()
    owner_engine = create_engine(owner_url)
    alpha_child = f"child_alpha_{uuid4().hex[:12]}"
    beta_child = f"child_beta_{uuid4().hex[:12]}"
    limited_user = f"rls_user_{uuid4().hex[:12]}"

    with owner_engine.begin() as connection:
        if connection.scalar(text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": _ROLE}):
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE usename = :role AND pid <> pg_backend_pid()"
                ),
                {"role": _ROLE},
            )
            connection.execute(text(f"DROP OWNED BY {_ROLE}"))
            connection.execute(text(f"DROP ROLE {_ROLE}"))
        connection.execute(
            text(
                f"CREATE ROLE {_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{_ROLE_PASSWORD}'"
            )
        )
        connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {_ROLE}"))
        connection.execute(
            text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {_ROLE}"
            )
        )
        connection.execute(
            text(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {_ROLE}")
        )
        connection.execute(
            text(
                "INSERT INTO organizations "
                "(organization_id, display_label, active, created_at, updated_at) "
                "VALUES (:id, :label, true, :now, :now)"
            ),
            [
                {"id": "org_alpha", "label": "Synthetic Alpha", "now": datetime.now(timezone.utc)},
                {"id": "org_beta", "label": "Synthetic Beta", "now": datetime.now(timezone.utc)},
            ],
        )
        connection.execute(
            text(
                "INSERT INTO user_profiles "
                "(user_id, display_label, created_at, updated_at) "
                "VALUES (:id, :label, :now, :now)"
            ),
            {
                "id": limited_user,
                "label": "Synthetic RLS User",
                "now": datetime.now(timezone.utc),
            },
        )
        connection.execute(
            text(
                "INSERT INTO organization_memberships "
                "(membership_id, organization_id, user_id, role, active, created_at, updated_at) "
                "VALUES (:membership_id, 'org_alpha', :user_id, 'org_admin', true, :now, :now)"
            ),
            {"membership_id": uuid4().hex, "user_id": limited_user, "now": datetime.now(timezone.utc)},
        )
        for child_id, organization_id in ((alpha_child, "org_alpha"), (beta_child, "org_beta")):
            connection.execute(
                text(
                    "INSERT INTO children "
                    "(child_id, organization_id, display_code, birth_month, birth_year, "
                    "language_context, version, created_at, updated_at) "
                    "VALUES (:child_id, :organization_id, :display_code, 6, 2021, "
                    "'{\"additional\":[],\"primary\":\"th\"}', 1, :now, :now)"
                ),
                {
                    "child_id": child_id,
                    "organization_id": organization_id,
                    "display_code": f"LL-{child_id[-6:]}",
                    "now": datetime.now(timezone.utc),
                },
            )

    try:
        limited_url = _limited_url(owner_url)
        yield str(owner_url), limited_url, alpha_child, beta_child
    finally:
        with owner_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM children WHERE child_id IN (:alpha, :beta)"),
                {"alpha": alpha_child, "beta": beta_child},
            )
            connection.execute(
                text("DELETE FROM organization_memberships WHERE user_id = :user_id"),
                {"user_id": limited_user},
            )
            connection.execute(text("DELETE FROM user_profiles WHERE user_id = :user_id"), {"user_id": limited_user})
            connection.execute(
                text("DELETE FROM organizations WHERE organization_id IN ('org_alpha', 'org_beta')")
            )
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE usename = :role AND pid <> pg_backend_pid()"
                ),
                {"role": _ROLE},
            )
            connection.execute(text(f"DROP OWNED BY {_ROLE}"))
            connection.execute(text(f"DROP ROLE IF EXISTS {_ROLE}"))
        owner_engine.dispose()
        get_assessment_session_factory.cache_clear()
        get_assessment_engine.cache_clear()
        get_settings.cache_clear()
        if previous_database_url is None:
            os.environ.pop("LINGUALENS_ASSESSMENT_DATABASE_URL", None)
        else:
            os.environ["LINGUALENS_ASSESSMENT_DATABASE_URL"] = previous_database_url


def _limited_engine(limited_url: str):
    return create_engine(limited_url, pool_size=1, max_overflow=0)


def test_rls_filters_tenant_rows_and_rejects_cross_tenant_writes(
    rls_database: tuple[str, str, str, str],
) -> None:
    _, limited_url, alpha_child, beta_child = rls_database
    engine = _limited_engine(limited_url)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(
                    text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
                    {"organization_id": "org_alpha"},
                )
                visible = set(connection.scalars(text("SELECT child_id FROM children")).all())
                assert visible == {alpha_child}

        with engine.begin() as connection:
            with pytest.raises(Exception):
                connection.execute(
                    text(
                        "INSERT INTO children "
                        "(child_id, organization_id, display_code, birth_month, birth_year, "
                        "language_context, version, created_at, updated_at) "
                        "VALUES (:child_id, :organization_id, 'LL-BLOCKED', 6, 2021, "
                        "'{\"additional\":[],\"primary\":\"th\"}', 1, :now, :now)"
                    ),
                    {
                        "child_id": f"blocked_{uuid4().hex}",
                        "organization_id": "org_beta",
                        "now": datetime.now(timezone.utc),
                    },
                )
    finally:
        engine.dispose()


def test_rls_without_context_is_fail_closed(rls_database: tuple[str, str, str, str]) -> None:
    _, limited_url, _, _ = rls_database
    engine = _limited_engine(limited_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM children")) == 0
        with engine.begin() as connection:
            with pytest.raises(Exception):
                connection.execute(
                    text(
                        "INSERT INTO children "
                        "(child_id, organization_id, display_code, birth_month, birth_year, "
                        "language_context, version, created_at, updated_at) "
                        "VALUES (:child_id, 'org_alpha', 'LL-NO-CONTEXT', 6, 2021, "
                        "'{\"additional\":[],\"primary\":\"th\"}', 1, :now, :now)"
                    ),
                    {"child_id": f"blocked_{uuid4().hex}", "now": datetime.now(timezone.utc)},
                )
    finally:
        engine.dispose()


def test_repository_sets_local_context_and_pool_does_not_retain_it(
    rls_database: tuple[str, str, str, str],
) -> None:
    _, limited_url, alpha_child, _ = rls_database
    user = CurrentUser(
        user_id="rls-user-placeholder",
        role="org_admin",
        organization_id="org_alpha",
        display_name="Synthetic RLS User",
    )
    # The fixture's membership is looked up by its generated user ID. Discovering
    # it through a scoped query keeps the assertion independent of that ID.
    engine = _limited_engine(limited_url)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(
                    text("SELECT set_config('app.current_organization_id', 'org_alpha', true)")
                )
                user.user_id = connection.scalar(
                    text("SELECT user_id FROM organization_memberships WHERE organization_id = 'org_alpha'")
                )
        user = CurrentUser(
            user_id=user.user_id,
            role=user.role,
            organization_id=user.organization_id,
            display_name=user.display_name,
        )
        with assessment_session_for(user, limited_url) as session:
            repository = AssessmentRepository(session)
            found = repository.get_child(
                AccessScope(user_id=user.user_id, organization_id="org_alpha", role="org_admin"),
                alpha_child,
            )
            assert found is not None

        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM children")) == 0
    finally:
        engine.dispose()

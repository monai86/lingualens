# Legacy Clinical Workflow Compatibility Surface

> [!WARNING]
> **LEGACY SURFACE / NOT FOR NEW PRODUCT ENDPOINTS**
> Per `AGENTS.md` and `docs/PROJECT_SOURCE_OF_TRUTH.md`:
> - `apps/api/app/repositories/` is the canonical production persistence layer for LinguaLens.
> - `src/clinical_workflow/` is retained solely for backward compatibility with legacy research tests and pilot scripts (`src/therapist_backend/`).
> - Do **NOT** add new clinical entities, business logic, or endpoints here.

## Canonical Architecture Mapping

| Legacy Research Component (`src/clinical_workflow/`) | Canonical Production Component (`apps/api/app/repositories/`) |
|-----------------------------------------------------|---------------------------------------------------------------|
| `repository_interface.ClinicalRepository`           | `apps.api.app.repositories.base.ClinicalRepository`           |
| `mock_repository.MockClinicalRepository`            | `apps.api.app.repositories.mock_repository.MemoryClinicalRepository` / `JsonClinicalRepository` |
| `postgres_supabase_repository.PostgresSupabaseRepository` | `apps.api.app.repositories.sqlalchemy_repository.SqlAlchemyClinicalRepository` |

## Guidance for Developers
1. When building new features or APIs, import models and repositories from `apps/api/app/`.
2. Existing tests referencing `src.clinical_workflow` remain supported to ensure baseline research reproducibility.

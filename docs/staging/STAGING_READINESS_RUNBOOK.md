# LinguaLens Staging Verification & Operational Readiness Runbook

**Document Version:** 2.0 (Assessment V2 Staging Gate S1)  
**Date:** 2026-09-12  
**Authority Boundary:** Research Prototype. Controlled Staging Verification Only. No Production Promotion Authorized.  
**Mandatory Safety Rule:** Local mocks or test fixtures **must never** be cited as evidence of managed Supabase staging. External staging execution requires explicit owner environment authority and live credentials.

---

## 1. Executive Status & Execution Gate

| Verification Target | Authority & Credentials Status | Execution Status | Evidence / Blocking Factor |
|---|---|---|---|
| **Local Disposable DB & Native PostgreSQL RLS** | Local developer authority; local PostgreSQL `localhost:5432` | **VERIFIED (PASSED)** | `scripts/check_assessment_v2_native.py` exit 0; 11/11 tests pass with forced tenant RLS on all 24 tables. |
| **External Managed Staging (Supabase Auth / JWKS)** | External project ref: `cbhwxklvcpgizeqriqxi` (unauthorized/tokens expired) | **EXECUTION PENDING** | Awaiting active non-mock operator tokens and staging project authority. |
| **Two-Tenant Staging Isolation (`org_a` vs `org_b`)** | Requires active provisioning of dual organizations on managed Supabase | **EXECUTION PENDING** | Blocked on live custom-claims provisioning (`app.current_organization_id`). |
| **Managed Private Storage & URL Expiry** | Requires Supabase S3-compatible private bucket with signed URL policies | **EXECUTION PENDING** | Blocked on bucket provisioning and lifecycle policy confirmation. |
| **Worker Recovery & Lease Integrity** | Local DB-backed worker leases verified; managed Render background worker pending | **LOCAL VERIFIED / MANAGED PENDING** | Local worker lease recovery verified in `test_postgres_processing_leases.py`. |

> [!IMPORTANT]
> In accordance with project instructions and AGENTS rules, external staging tests are executed **strictly when exact environment authority and credentials are provided**. Antigravity does not attempt unauthorized network calls or fabricate live staging receipts with local mocks.

---

## 2. Local Reproducible Evidence Foundation (Verified)

The following verification suite proves that all SQL models, migrations, and Row-Level Security policies are structurally sound and fail-closed:

```bash
# 1. Migration Upgrade & Downgrade Cycle (0001 -> 0012 -> 0001)
PYTHONPATH=apps/api:src python3 scripts/check_assessment_v2_migrations.py

# 2. Native PostgreSQL RLS & Lease Recovery Verification (Fresh disposable DB)
PYTHONPATH=apps/api:src python3 scripts/check_assessment_v2_native.py
```

### Verified Local Results:
- **Alembic Head:** `0012_clinical_review_reports` (28 chars $\le 32$).
- **Forced Row-Level Security (RLS):** All 24 tenant-scoped tables enforce `FORCE ROW LEVEL SECURITY`.
- **Cross-Tenant Blocking:** Queries without `app.current_organization_id` return 0 rows (fail-closed). Direct cross-tenant writes raise PostgreSQL exceptions.
- **Worker Leases:** Stale worker lease recovery and bounded retry limits verified without data loss.

---

## 3. External Staging Execution Protocol (When Authorized)

When external staging credentials are provisioned, the operator must execute the following sequential protocol without deviation.

### Phase A: Staging Environment Shell Preparation

1. Generate a dated working environment file from the template:
   ```bash
   bash scripts/create_staging_verification_env.sh
   ```
2. Populate the working copy (`docs/release_artifacts/staging_env/<dated-run>.env`) with live staging values:
   - `STAGING_API_BASE_URL`: e.g. `https://lingualens-api-staging.onrender.com/api/v1`
   - `STAGING_SUPABASE_PROJECT_REF`: e.g. `cbhwxklvcpgizeqriqxi`
   - `TOKEN_THERAPIST_A_ASSIGNED`: Real RS256/EdDSA JWT issued by Supabase Auth with custom claims (`org_id=org_a`, `role=therapist`, `care_team=[case_a_1]`).
   - `TOKEN_THERAPIST_A_UNASSIGNED`: Real JWT for therapist in `org_a` without `case_a_1` assignment.
   - `TOKEN_THERAPIST_B_ASSIGNED`: Real JWT for therapist in `org_b` assigned to `case_b_1`.
   - `TOKEN_SUPERVISOR_A`: Real JWT for clinical supervisor in `org_a`.
   - `TOKEN_ORG_ADMIN_A`: Real JWT for organization administrator in `org_a`.
   - `TOKEN_PLATFORM_OPERATOR_A`: Real JWT for platform operator (break-glass only).
3. Validate the working environment file:
   ```bash
   bash scripts/validate_staging_verification_env.sh docs/release_artifacts/staging_env/<dated-run>.env
   ```

---

### Phase B: Verification Matrix & Security Gates

#### 1. Real JWT / JWKS Claim Lifecycle & Role Boundary
- **Objective:** Verify that the API validates tokens directly against Supabase JWKS URL (`https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`) with zero mock fallbacks.
- **Command:**
  ```bash
  curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN_THERAPIST_A_ASSIGNED" \
    "$STAGING_API_BASE_URL/auth/session/verify"
  ```
- **Expectation:** `HTTP 200` with decoded claims matching tenant context. An expired token or invalid signature must return `HTTP 401 unauthorized`.

#### 2. Two-Tenant Row-Level Security Isolation (`org_a` vs `org_b`)
- **Objective:** Prove that `therapist_a_assigned` cannot read or modify any resource belonging to `org_b`.
- **Command:**
  ```bash
  # Attempt cross-tenant assessment access
  curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer $TOKEN_THERAPIST_A_ASSIGNED" \
    "$STAGING_API_BASE_URL/api/v2/assessments/$ORG_B_CASE_ID"
  ```
- **Expectation:** Must return `HTTP 404 not_found` or `HTTP 403 forbidden`. No metadata, status, or timestamps from `org_b` may leak into error payloads.

#### 3. Same-Organization Care-Team Assignment Enforcement
- **Objective:** Prove that unassigned therapists within `org_a` cannot access clinical assessment data.
- **Command:**
  ```bash
  curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer $TOKEN_THERAPIST_A_UNASSIGNED" \
    "$STAGING_API_BASE_URL/api/v2/assessments/$ORG_A_CASE_ID/transcript-segment-set"
  ```
- **Expectation:** Must return `HTTP 403 forbidden` (`error_code="forbidden"`).

#### 4. Consent Revocation Race & Fail-Closed Behavior
- **Objective:** Prove that revoking consent immediately denies access to recordings, transcripts, and reports even for the assigned therapist.
- **Command:**
  ```bash
  # 1. Withdraw consent
  curl -X POST -H "Authorization: Bearer $TOKEN_SUPERVISOR_A" \
    "$STAGING_API_BASE_URL/api/v2/children/$CHILD_A_ID/consents/withdraw"
  
  # 2. Immediately probe transcript segment set
  curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer $TOKEN_THERAPIST_A_ASSIGNED" \
    "$STAGING_API_BASE_URL/api/v2/assessments/$ORG_A_CASE_ID/transcript-segment-set"
  ```
- **Expectation:** Must return `HTTP 409 consent_revoked`.

#### 5. Private Storage & Signed URL Expiry
- **Objective:** Verify that audio files and signed PDF exports are stored in private buckets accessible only via short-lived signed URLs.
- **Checks:**
  - Direct unauthenticated bucket access (`https://<project-ref>.supabase.co/storage/v1/object/public/assessment-audio/...`) must return `HTTP 400` or `HTTP 404` (public access disabled).
  - Signed URL expiration window is capped at $\le 900$ seconds (15 minutes).
  - Attempting to access an expired URL must return `HTTP 403` or `HTTP 400 SignatureDoesNotMatch`.

#### 6. Asynchronous Worker Recovery & Lease Integrity
- **Objective:** Prove that if a worker pod terminates during evidence extraction, the database lease recovers safely.
- **Procedure:**
  1. Enqueue evidence run: `POST /api/v2/assessments/{id}/evidence-runs`.
  2. Simulate worker termination (`SIGKILL` on background worker process).
  3. Verify that `processing_runs.available_at` expires and a secondary worker picks up the job without duplicate execution or record corruption.

#### 7. Managed Backup & Point-in-Time Restore
- **Objective:** Validate disaster recovery runbook (`docs/BACKUP_RESTORE_RUNBOOK.md`).
- **Procedure:**
  1. Trigger managed snapshot/backup via Supabase Management API or PostgreSQL dump.
  2. Restore to an isolated recovery database.
  3. Execute `python3 scripts/check_assessment_v2_migrations.py` against the restored target to verify schema completeness.

#### 8. Redacted Telemetry & Audit Evidence Collection
- **Objective:** Ensure no Protected Health Information (PHI) or secrets appear in staging logs.
- **Verification Rule:** Inspect `audit_events` and API server logs. Verify that:
  - Real child names, surnames, and Thai national IDs are absent (only synthetic `LL-XXXXXX` display codes).
  - Raw audio byte payloads, base64 data, and Supabase JWT tokens are replaced with redaction markers.
  - Transcript utterance text is excluded from structured log fields.

---

## 4. Staging Evidence Packet Template

When staging verification is completed with real credentials, compile the outputs using `scripts/run_staging_review_bundle.sh` into `docs/release_artifacts/staging_packet/` with the following signed header:

```markdown
# Staging Tenant-Safety & Runtime Verification Packet
- Run Date/Time: <UTC timestamp>
- Git Commit: <exact SHA>
- Deployed API URL: https://lingualens-api-staging.onrender.com/api/v1
- Supabase Project Ref: cbhwxklvcpgizeqriqxi
- Verifier Mode: jwks_url
- Operator: <authorized human name>
- Verification Result: PASS / FAIL
```

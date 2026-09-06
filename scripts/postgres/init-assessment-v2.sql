-- Local Compose bootstrap only. Production credentials must come from managed secrets.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lingualens_assessment_app') THEN
        CREATE ROLE lingualens_assessment_app
            LOGIN
            NOSUPERUSER
            NOBYPASSRLS
            PASSWORD 'local-assessment-only';
    END IF;
END
$$;

-- Create the fresh assessment database beside, never instead of, therapist_app_v2.
CREATE DATABASE lingualens_assessment_v2 OWNER lingualens_assessment_app;

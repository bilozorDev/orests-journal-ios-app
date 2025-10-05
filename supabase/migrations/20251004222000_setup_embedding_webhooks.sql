-- Enable pg_net extension for HTTP requests
CREATE EXTENSION IF NOT EXISTS pg_net
WITH SCHEMA extensions;

-- Function to get Supabase project URL from environment
CREATE OR REPLACE FUNCTION get_project_url()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    url TEXT;
BEGIN
    -- Get the project URL from Vault or use default for local development
    SELECT decrypted_secret INTO url
    FROM vault.decrypted_secrets
    WHERE name = 'project_url';

    -- Fallback for local development
    IF url IS NULL THEN
        url := 'http://host.docker.internal:54321';
    END IF;

    RETURN url;
END;
$$;

-- Function to trigger embedding generation via Edge Function webhook
CREATE OR REPLACE FUNCTION trigger_embedding_generation()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    project_url TEXT;
    request_id BIGINT;
BEGIN
    -- Get project URL
    project_url := get_project_url();

    -- Call the Edge Function via pg_net
    SELECT INTO request_id net.http_post(
        url := project_url || '/functions/v1/generate-health-embedding',
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key', true)
        ),
        body := jsonb_build_object(
            'type', TG_OP,
            'table', TG_TABLE_NAME,
            'schema', TG_TABLE_SCHEMA,
            'record', to_jsonb(NEW),
            'old_record', CASE WHEN TG_OP = 'UPDATE' THEN to_jsonb(OLD) ELSE NULL END
        ),
        timeout_milliseconds := 5000
    );

    RETURN NEW;
END;
$$;

-- Create triggers for pet_health_categories
DROP TRIGGER IF EXISTS generate_category_embedding_on_insert ON pet_health_categories;
CREATE TRIGGER generate_category_embedding_on_insert
    AFTER INSERT ON pet_health_categories
    FOR EACH ROW
    EXECUTE FUNCTION trigger_embedding_generation();

DROP TRIGGER IF EXISTS generate_category_embedding_on_update ON pet_health_categories;
CREATE TRIGGER generate_category_embedding_on_update
    AFTER UPDATE OF name ON pet_health_categories
    FOR EACH ROW
    WHEN (OLD.name IS DISTINCT FROM NEW.name)
    EXECUTE FUNCTION trigger_embedding_generation();

-- Create triggers for pet_health_events
DROP TRIGGER IF EXISTS generate_event_embedding_on_insert ON pet_health_events;
CREATE TRIGGER generate_event_embedding_on_insert
    AFTER INSERT ON pet_health_events
    FOR EACH ROW
    EXECUTE FUNCTION trigger_embedding_generation();

DROP TRIGGER IF EXISTS generate_event_embedding_on_update ON pet_health_events;
CREATE TRIGGER generate_event_embedding_on_update
    AFTER UPDATE OF notes, category_id ON pet_health_events
    FOR EACH ROW
    WHEN (OLD.notes IS DISTINCT FROM NEW.notes OR OLD.category_id IS DISTINCT FROM NEW.category_id)
    EXECUTE FUNCTION trigger_embedding_generation();

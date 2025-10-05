-- Backfill embeddings for existing health categories and events
-- This migration triggers the embedding generation webhook for all existing records

-- Trigger embedding generation for all existing categories
-- We do this by doing a no-op update that changes the updated_at timestamp
DO $$
DECLARE
    category_record RECORD;
BEGIN
    FOR category_record IN
        SELECT id FROM pet_health_categories WHERE embedding IS NULL
    LOOP
        -- Update to trigger the webhook (this will call the Edge Function)
        -- We're updating the name to itself to trigger the update trigger
        UPDATE pet_health_categories
        SET name = name
        WHERE id = category_record.id;

        -- Small delay to avoid overwhelming the Edge Function
        PERFORM pg_sleep(0.1);
    END LOOP;
END $$;

-- Trigger embedding generation for all existing events
DO $$
DECLARE
    event_record RECORD;
BEGIN
    FOR event_record IN
        SELECT id FROM pet_health_events WHERE embedding IS NULL
    LOOP
        -- Update to trigger the webhook
        -- We update occurred_at to itself (doesn't trigger our specific update trigger)
        -- So instead we'll set notes to itself or to empty string and back
        UPDATE pet_health_events
        SET notes = notes
        WHERE id = event_record.id;

        -- Small delay to avoid overwhelming the Edge Function
        PERFORM pg_sleep(0.1);
    END LOOP;
END $$;

-- Function to combine category name and event notes for embedding input
CREATE OR REPLACE FUNCTION health_event_embedding_input(event pet_health_events)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    category_name TEXT;
BEGIN
    -- Get the category name for this event
    SELECT name INTO category_name
    FROM pet_health_categories
    WHERE id = event.category_id;

    -- Combine category name with notes (if any)
    IF event.notes IS NOT NULL AND event.notes != '' THEN
        RETURN category_name || '. ' || event.notes;
    ELSE
        RETURN category_name;
    END IF;
END;
$$;

-- Function to search health events using semantic search
CREATE OR REPLACE FUNCTION search_health_events(
    query_embedding vector(384),
    pet_id_filter UUID DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    event_id UUID,
    category_id UUID,
    category_name TEXT,
    occurred_at TIMESTAMPTZ,
    notes TEXT,
    pet_id UUID,
    pet_name TEXT,
    created_by_id UUID,
    created_by_email TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER -- Run with elevated privileges to access auth.users
AS $$
BEGIN
    RETURN QUERY
    WITH event_matches AS (
        -- Search events by their embeddings
        SELECT
            e.id AS event_id,
            e.category_id,
            c.name AS category_name,
            e.occurred_at,
            e.notes,
            c.pet_id,
            e.created_by,
            -- Calculate similarity (convert inner product to positive similarity score)
            -- Inner product for normalized vectors ranges from -1 to 1, we convert to 0 to 1
            (1 + (e.embedding <#> query_embedding)) / 2 AS similarity
        FROM pet_health_events e
        JOIN pet_health_categories c ON e.category_id = c.id
        WHERE
            e.embedding IS NOT NULL
            AND (pet_id_filter IS NULL OR c.pet_id = pet_id_filter)
            -- Filter by similarity threshold
            AND (1 + (e.embedding <#> query_embedding)) / 2 > match_threshold
            -- RLS will automatically filter to user's family's pets

        UNION ALL

        -- Search categories by their embeddings
        SELECT
            e.id AS event_id,
            e.category_id,
            c.name AS category_name,
            e.occurred_at,
            e.notes,
            c.pet_id,
            e.created_by,
            -- Calculate similarity for category embeddings
            (1 + (c.embedding <#> query_embedding)) / 2 AS similarity
        FROM pet_health_categories c
        JOIN pet_health_events e ON e.category_id = c.id
        WHERE
            c.embedding IS NOT NULL
            AND (pet_id_filter IS NULL OR c.pet_id = pet_id_filter)
            -- Filter by similarity threshold
            AND (1 + (c.embedding <#> query_embedding)) / 2 > match_threshold
            -- RLS will automatically filter to user's family's pets
    ),
    -- Deduplicate and take best similarity for each event
    best_matches AS (
        SELECT DISTINCT ON (event_id)
            event_id,
            category_id,
            category_name,
            occurred_at,
            notes,
            pet_id,
            created_by,
            similarity
        FROM event_matches
        ORDER BY event_id, similarity DESC
    )
    SELECT
        bm.event_id,
        bm.category_id,
        bm.category_name,
        bm.occurred_at,
        bm.notes,
        bm.pet_id,
        p.name AS pet_name,
        bm.created_by AS created_by_id,
        COALESCE(au.email, 'Unknown') AS created_by_email,
        bm.similarity
    FROM best_matches bm
    JOIN pets p ON bm.pet_id = p.id
    LEFT JOIN auth.users au ON bm.created_by = au.id
    ORDER BY bm.similarity DESC
    LIMIT match_count;
END;
$$;

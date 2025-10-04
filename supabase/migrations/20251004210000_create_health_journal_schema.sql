-- Create pet_health_categories table
CREATE TABLE pet_health_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    CONSTRAINT unique_category_per_pet UNIQUE (pet_id, name_normalized)
);

-- Create pet_health_events table
CREATE TABLE pet_health_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES pet_health_categories(id) ON DELETE CASCADE,
    occurred_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Create indexes for pet_health_categories
CREATE INDEX idx_pet_health_categories_pet_id ON pet_health_categories(pet_id);
CREATE INDEX idx_pet_health_categories_name_normalized ON pet_health_categories(pet_id, name_normalized);
CREATE INDEX idx_pet_health_categories_created_at ON pet_health_categories(created_at DESC);

-- Create indexes for pet_health_events
CREATE INDEX idx_pet_health_events_category_id ON pet_health_events(category_id);
CREATE INDEX idx_pet_health_events_occurred_at ON pet_health_events(occurred_at DESC);
CREATE INDEX idx_pet_health_events_created_by ON pet_health_events(created_by);

-- Enable Row Level Security
ALTER TABLE pet_health_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE pet_health_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies for pet_health_categories
CREATE POLICY "Users can view categories for their family's pets"
    ON pet_health_categories FOR SELECT
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can create categories"
    ON pet_health_categories FOR INSERT
    WITH CHECK (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
        AND created_by = auth.uid()
    );

CREATE POLICY "Family members can update categories"
    ON pet_health_categories FOR UPDATE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can delete categories"
    ON pet_health_categories FOR DELETE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

-- RLS Policies for pet_health_events
CREATE POLICY "Users can view events for their family's pets"
    ON pet_health_events FOR SELECT
    USING (
        category_id IN (
            SELECT id FROM pet_health_categories
            WHERE pet_id IN (
                SELECT id FROM pets
                WHERE family_id IN (
                    SELECT family_id FROM family_members
                    WHERE user_id = auth.uid()
                )
            )
        )
    );

CREATE POLICY "Family members can create events"
    ON pet_health_events FOR INSERT
    WITH CHECK (
        category_id IN (
            SELECT id FROM pet_health_categories
            WHERE pet_id IN (
                SELECT id FROM pets
                WHERE family_id IN (
                    SELECT family_id FROM family_members
                    WHERE user_id = auth.uid()
                )
            )
        )
        AND created_by = auth.uid()
    );

CREATE POLICY "Family members can update events"
    ON pet_health_events FOR UPDATE
    USING (
        category_id IN (
            SELECT id FROM pet_health_categories
            WHERE pet_id IN (
                SELECT id FROM pets
                WHERE family_id IN (
                    SELECT family_id FROM family_members
                    WHERE user_id = auth.uid()
                )
            )
        )
    );

CREATE POLICY "Family members can delete events"
    ON pet_health_events FOR DELETE
    USING (
        category_id IN (
            SELECT id FROM pet_health_categories
            WHERE pet_id IN (
                SELECT id FROM pets
                WHERE family_id IN (
                    SELECT family_id FROM family_members
                    WHERE user_id = auth.uid()
                )
            )
        )
    );

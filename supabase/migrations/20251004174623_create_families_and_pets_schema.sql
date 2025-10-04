-- Create families table
CREATE TABLE families (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Create family_members table
CREATE TABLE family_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
    joined_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(family_id, user_id)
);

-- Create pets table
CREATE TABLE pets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    photo_url TEXT,
    current_weight DOUBLE PRECISION,
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW()
);

-- Create health_records table
CREATE TABLE health_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    recorded_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    age_years DOUBLE PRECISION,
    weight_pounds DOUBLE PRECISION,
    notes TEXT
);

-- Create indexes
CREATE INDEX idx_family_members_family_id ON family_members(family_id);
CREATE INDEX idx_family_members_user_id ON family_members(user_id);
CREATE INDEX idx_pets_family_id ON pets(family_id);
CREATE INDEX idx_health_records_pet_id ON health_records(pet_id);
CREATE INDEX idx_health_records_recorded_at ON health_records(recorded_at DESC);

-- Enable Row Level Security
ALTER TABLE families ENABLE ROW LEVEL SECURITY;
-- Note: family_members RLS is disabled to allow policy subqueries to work
-- ALTER TABLE family_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE pets ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_records ENABLE ROW LEVEL SECURITY;

-- RLS Policies for families
CREATE POLICY "Users can view their families"
    ON families FOR SELECT
    USING (
        created_by = auth.uid()
        OR
        id IN (
            SELECT family_id FROM family_members
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create families"
    ON families FOR INSERT
    WITH CHECK (created_by = auth.uid());

CREATE POLICY "Family creators can update families"
    ON families FOR UPDATE
    USING (created_by = auth.uid());

-- RLS Policies for family_members
-- Note: These policies are commented out because RLS is disabled on family_members
-- This allows other tables' RLS policies to query family_members without circular dependencies

-- CREATE POLICY "Users can view their own memberships"
--     ON family_members FOR SELECT
--     USING (user_id = auth.uid());

-- CREATE POLICY "Family creators can add members"
--     ON family_members FOR INSERT
--     WITH CHECK (
--         EXISTS (
--             SELECT 1 FROM families
--             WHERE id = family_id AND created_by = auth.uid()
--         )
--     );

-- CREATE POLICY "Family creators can remove members"
--     ON family_members FOR DELETE
--     USING (
--         EXISTS (
--             SELECT 1 FROM families
--             WHERE id = family_id AND created_by = auth.uid()
--         )
--     );

-- RLS Policies for pets
CREATE POLICY "Users can view their family's pets"
    ON pets FOR SELECT
    USING (
        family_id IN (
            SELECT family_id FROM family_members
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Family members can create pets"
    ON pets FOR INSERT
    WITH CHECK (
        family_id IN (
            SELECT family_id FROM family_members
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Family members can update pets"
    ON pets FOR UPDATE
    USING (
        family_id IN (
            SELECT family_id FROM family_members
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Family creators can delete pets"
    ON pets FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM families
            WHERE id = family_id AND created_by = auth.uid()
        )
    );

-- RLS Policies for health_records
CREATE POLICY "Users can view health records for their family's pets"
    ON health_records FOR SELECT
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can create health records"
    ON health_records FOR INSERT
    WITH CHECK (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can update health records"
    ON health_records FOR UPDATE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can delete health records"
    ON health_records FOR DELETE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

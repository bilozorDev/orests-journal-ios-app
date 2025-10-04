-- Create pet_feedings table
CREATE TABLE pet_feedings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    food_id UUID NOT NULL REFERENCES pet_foods(id) ON DELETE CASCADE,
    fed_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    fed_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    amount DOUBLE PRECISION NOT NULL,
    amount_unit TEXT NOT NULL DEFAULT 'g' CHECK (amount_unit IN ('g', 'oz', 'kg', 'lb')),
    calories DOUBLE PRECISION NOT NULL,
    notes TEXT,
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW()
);

-- Create pet_calorie_goals table
CREATE TABLE pet_calorie_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    daily_calories DOUBLE PRECISION NOT NULL,
    effective_from TIMESTAMP(0) WITH TIME ZONE NOT NULL DEFAULT NOW(),
    effective_until TIMESTAMP(0) WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    CONSTRAINT check_date_range CHECK (effective_until IS NULL OR effective_until >= effective_from)
);

-- Create indexes for pet_feedings
CREATE INDEX idx_pet_feedings_pet_id ON pet_feedings(pet_id);
CREATE INDEX idx_pet_feedings_fed_at ON pet_feedings(fed_at DESC);
CREATE INDEX idx_pet_feedings_fed_by ON pet_feedings(fed_by);

-- Create indexes for pet_calorie_goals
CREATE INDEX idx_pet_calorie_goals_pet_id ON pet_calorie_goals(pet_id);
CREATE INDEX idx_pet_calorie_goals_effective ON pet_calorie_goals(pet_id, effective_from, effective_until);

-- Enable Row Level Security
ALTER TABLE pet_feedings ENABLE ROW LEVEL SECURITY;
ALTER TABLE pet_calorie_goals ENABLE ROW LEVEL SECURITY;

-- RLS Policies for pet_feedings
CREATE POLICY "Users can view feedings for their family's pets"
    ON pet_feedings FOR SELECT
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can create feedings"
    ON pet_feedings FOR INSERT
    WITH CHECK (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
        AND fed_by = auth.uid()
    );

CREATE POLICY "Family members can update feedings"
    ON pet_feedings FOR UPDATE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can delete feedings"
    ON pet_feedings FOR DELETE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

-- RLS Policies for pet_calorie_goals
CREATE POLICY "Users can view calorie goals for their family's pets"
    ON pet_calorie_goals FOR SELECT
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can create calorie goals"
    ON pet_calorie_goals FOR INSERT
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

CREATE POLICY "Family members can update calorie goals"
    ON pet_calorie_goals FOR UPDATE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can delete calorie goals"
    ON pet_calorie_goals FOR DELETE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

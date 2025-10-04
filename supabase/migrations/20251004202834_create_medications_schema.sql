-- Create pet_medications table
CREATE TABLE pet_medications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    medication_type TEXT NOT NULL CHECK (medication_type IN ('drops', 'pill', 'inhaler', 'shot', 'liquid', 'tablet', 'capsule', 'topical')),
    start_date TIMESTAMP(0) WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP(0) WITH TIME ZONE,
    times_per_day INTEGER NOT NULL CHECK (times_per_day > 0),
    notes TEXT,
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    CONSTRAINT check_medication_date_range CHECK (end_date IS NULL OR end_date >= start_date)
);

-- Create pet_medication_doses table
CREATE TABLE pet_medication_doses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    medication_id UUID NOT NULL REFERENCES pet_medications(id) ON DELETE CASCADE,
    given_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    given_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    notes TEXT,
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for pet_medications
CREATE INDEX idx_pet_medications_pet_id ON pet_medications(pet_id);
CREATE INDEX idx_pet_medications_dates ON pet_medications(pet_id, start_date, end_date);
CREATE INDEX idx_pet_medications_created_at ON pet_medications(created_at DESC);

-- Create indexes for pet_medication_doses
CREATE INDEX idx_pet_medication_doses_medication_id ON pet_medication_doses(medication_id);
CREATE INDEX idx_pet_medication_doses_given_at ON pet_medication_doses(given_at DESC);
CREATE INDEX idx_pet_medication_doses_given_by ON pet_medication_doses(given_by);

-- Enable Row Level Security
ALTER TABLE pet_medications ENABLE ROW LEVEL SECURITY;
ALTER TABLE pet_medication_doses ENABLE ROW LEVEL SECURITY;

-- RLS Policies for pet_medications
CREATE POLICY "Users can view medications for their family's pets"
    ON pet_medications FOR SELECT
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can create medications"
    ON pet_medications FOR INSERT
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

CREATE POLICY "Family members can update medications"
    ON pet_medications FOR UPDATE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Family members can delete medications"
    ON pet_medications FOR DELETE
    USING (
        pet_id IN (
            SELECT id FROM pets
            WHERE family_id IN (
                SELECT family_id FROM family_members
                WHERE user_id = auth.uid()
            )
        )
    );

-- RLS Policies for pet_medication_doses
CREATE POLICY "Users can view doses for their family's pet medications"
    ON pet_medication_doses FOR SELECT
    USING (
        medication_id IN (
            SELECT id FROM pet_medications
            WHERE pet_id IN (
                SELECT id FROM pets
                WHERE family_id IN (
                    SELECT family_id FROM family_members
                    WHERE user_id = auth.uid()
                )
            )
        )
    );

CREATE POLICY "Family members can create doses"
    ON pet_medication_doses FOR INSERT
    WITH CHECK (
        medication_id IN (
            SELECT id FROM pet_medications
            WHERE pet_id IN (
                SELECT id FROM pets
                WHERE family_id IN (
                    SELECT family_id FROM family_members
                    WHERE user_id = auth.uid()
                )
            )
        )
        AND given_by = auth.uid()
    );

CREATE POLICY "Family members can update doses"
    ON pet_medication_doses FOR UPDATE
    USING (
        medication_id IN (
            SELECT id FROM pet_medications
            WHERE pet_id IN (
                SELECT id FROM pets
                WHERE family_id IN (
                    SELECT family_id FROM family_members
                    WHERE user_id = auth.uid()
                )
            )
        )
    );

CREATE POLICY "Family members can delete doses"
    ON pet_medication_doses FOR DELETE
    USING (
        medication_id IN (
            SELECT id FROM pet_medications
            WHERE pet_id IN (
                SELECT id FROM pets
                WHERE family_id IN (
                    SELECT family_id FROM family_members
                    WHERE user_id = auth.uid()
                )
            )
        )
    );

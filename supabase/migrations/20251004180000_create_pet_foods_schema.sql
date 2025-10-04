-- Create pet_foods table
CREATE TABLE pet_foods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('dry', 'wet', 'snack')),
    calories_per_container DOUBLE PRECISION NOT NULL,
    container_size_grams DOUBLE PRECISION NOT NULL,
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX idx_pet_foods_family_id ON pet_foods(family_id);
CREATE INDEX idx_pet_foods_created_at ON pet_foods(created_at DESC);

-- Enable Row Level Security
ALTER TABLE pet_foods ENABLE ROW LEVEL SECURITY;

-- RLS Policies for pet_foods
CREATE POLICY "Users can view their family's foods"
    ON pet_foods FOR SELECT
    USING (
        family_id IN (
            SELECT family_id FROM family_members
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Family members can create foods"
    ON pet_foods FOR INSERT
    WITH CHECK (
        family_id IN (
            SELECT family_id FROM family_members
            WHERE user_id = auth.uid()
        )
        AND created_by = auth.uid()
    );

CREATE POLICY "Family members can update foods"
    ON pet_foods FOR UPDATE
    USING (
        family_id IN (
            SELECT family_id FROM family_members
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Family creators can delete foods"
    ON pet_foods FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM families
            WHERE id = family_id AND created_by = auth.uid()
        )
    );

-- Create storage bucket for food images
INSERT INTO storage.buckets (id, name, public)
VALUES ('food-images', 'food-images', true)
ON CONFLICT (id) DO NOTHING;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Public can view food images" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can upload food images" ON storage.objects;
DROP POLICY IF EXISTS "Users can update their own food images" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete their own food images" ON storage.objects;

-- Policy: Anyone can view food images (public bucket)
CREATE POLICY "Public can view food images"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'food-images');

-- Policy: Authenticated users can upload food images
CREATE POLICY "Authenticated users can upload food images"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'food-images' AND
        auth.role() = 'authenticated'
    );

-- Policy: Users can update their own uploaded food images
CREATE POLICY "Users can update their own food images"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'food-images' AND
        auth.uid() = owner::uuid
    );

-- Policy: Users can delete their own uploaded food images
CREATE POLICY "Users can delete their own food images"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'food-images' AND
        auth.uid() = owner::uuid
    );
